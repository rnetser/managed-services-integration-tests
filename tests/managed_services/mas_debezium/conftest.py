import logging

import pytest
import rhoas_kafka_instance_sdk
from constants import KAFKA_NAME, TEST_RECORD, TEST_TOPIC
from consumer_pod import ConsumerPod
from ocp_resources.namespace import Namespace
from ocp_resources.pod import Pod
from ocp_resources.utils import TimeoutExpiredError, TimeoutSampler
from ocp_utilities.infra import cluster_resource
from rhoas_kafka_instance_sdk.api import acls_api, records_api, topics_api
from rhoas_kafka_instance_sdk.model.acl_binding import AclBinding
from rhoas_kafka_instance_sdk.model.acl_operation import AclOperation
from rhoas_kafka_instance_sdk.model.acl_pattern_type import AclPatternType
from rhoas_kafka_instance_sdk.model.acl_permission_type import AclPermissionType
from rhoas_kafka_instance_sdk.model.acl_resource_type import AclResourceType
from rhoas_kafka_instance_sdk.model.config_entry import ConfigEntry
from rhoas_kafka_instance_sdk.model.new_topic_input import NewTopicInput
from rhoas_kafka_instance_sdk.model.record import Record
from rhoas_kafka_instance_sdk.model.topic_settings import TopicSettings
from rhoas_kafka_mgmt_sdk.model.kafka_request_payload import KafkaRequestPayload
from rhoas_service_accounts_mgmt_sdk.model.service_account_create_request_data import (
    ServiceAccountCreateRequestData,
)


LOGGER = logging.getLogger(__name__)
WAIT_STATUS_TIMEOUT = 120


@pytest.fixture(scope="class")
def kafka_instance(kafka_mgmt_api_instance):
    _async = True
    kafka_request_payload = KafkaRequestPayload(
        cloud_provider="aws",
        name=KAFKA_NAME,
        region="us-east-1",
        plan="standard.x1",
        reauthentication_enabled=True,
    )
    kafka_create_api = kafka_mgmt_api_instance.create_kafka(
        _async=_async, kafka_request_payload=kafka_request_payload
    )
    assert (
        kafka_create_api.status == "accepted"
    ), f"Failed to create a kafka instance. API response:\n{kafka_create_api}"

    yield kafka_create_api

    kafka_mgmt_api_instance.delete_kafka_by_id(
        async_req=True, _async=_async, id=kafka_create_api.id
    )


@pytest.fixture(scope="class")
def kafka_instance_ready(kafka_mgmt_api_instance, kafka_instance):
    try:
        kafka_samples = TimeoutSampler(
            wait_timeout=360,
            sleep=10,
            func=lambda: kafka_mgmt_api_instance.get_kafka_by_id(id=kafka_instance.id),
        )
        for kafka_sample in kafka_samples:
            if kafka_sample.status == "ready":
                LOGGER.info(f"Kafka instance is ready:\n{kafka_sample}")
                yield kafka_sample
                break

    except TimeoutExpiredError:
        LOGGER.error(
            "Timeout expired. Kafka creation status: "
            f"{kafka_mgmt_api_instance.get_kafka_by_id(id=kafka_instance.id).status}"
        )
        raise


@pytest.fixture(scope="class")
def kafka_instance_client(kafka_instance_ready, access_token):
    # https://github.com/redhat-developer/app-services-sdk-python/tree/main/sdks/kafka_instance_sdk
    configuration = rhoas_kafka_instance_sdk.Configuration(
        host=kafka_instance_ready.admin_api_server_url, access_token=access_token
    )

    with rhoas_kafka_instance_sdk.ApiClient(
        configuration=configuration
    ) as kafka_api_client:
        yield kafka_api_client


@pytest.fixture(scope="class")
def kafka_instance_sa(kafka_instance_client, service_accounts_api_instance):
    service_account_create_request_data = ServiceAccountCreateRequestData(
        name="ms-kafka-sa",
        description=f"{KAFKA_NAME} instance service-account",
    )
    kafka_sa = service_accounts_api_instance.create_service_account(
        service_account_create_request_data=service_account_create_request_data
    )
    assert (
        kafka_sa.id
    ), f"Failed to create service-account for kafka. API response:\n{kafka_sa}"

    yield kafka_sa

    service_accounts_api_instance.delete_service_account(id=kafka_sa.id, async_req=True)


@pytest.fixture(scope="class")
def kafka_sa_acl(kafka_instance_client, kafka_instance_sa):
    # Binding the service-account instance to kafka with privileges
    # via AclBinding instance
    acl_api_instance = acls_api.AclsApi(api_client=kafka_instance_client)
    for resource in ["GROUP", "TOPIC", "TRANSACTIONAL_ID"]:
        acl_binding = AclBinding(
            resource_type=AclResourceType(resource),
            resource_name="*",
            pattern_type=AclPatternType("LITERAL"),
            permission=AclPermissionType("ALLOW"),
            principal=f"User:{kafka_instance_sa.id}",
            operation=AclOperation("ALL"),
        )
        acl_api_instance.create_acl(acl_binding=acl_binding)


@pytest.fixture(scope="class")
def kafka_topics(kafka_instance_client):
    kafka_topics = [
        {
            "name": "debezium_topics",
            "topics": [
                "avro",
                "avro.inventory.addresses",
                "avro.inventory.customers",
                "avro.inventory.geom",
                "avro.inventory.orders",
                "avro.inventory.products",
                "avro.inventory.products_on_hand",
                "schema-changes.inventory",
            ],
            "cleanup_policy": "delete",
            "num_partitions": 1,
        },
        {
            "name": "mysql_topics",
            "topics": [
                "debezium-cluster-configs",
                "debezium-cluster-offsets",
                "debezium-cluster-status",
            ],
            "cleanup_policy": "compact",
            "num_partitions": 1,
        },
    ]

    kafka_topics_api_instance = topics_api.TopicsApi(api_client=kafka_instance_client)
    for topics_group in kafka_topics:
        for topic in topics_group["topics"]:
            new_topic_input = NewTopicInput(
                name=topic,
                settings=TopicSettings(
                    num_partitions=topics_group["num_partitions"],
                    config=[
                        ConfigEntry(
                            key="cleanup.policy",
                            value=topics_group["cleanup_policy"],
                        ),
                    ],
                ),
            )
            kafka_topics_api_instance.create_topic(new_topic_input=new_topic_input)

    # Produce to tested topic
    records_api_client = records_api.RecordsApi(api_client=kafka_instance_client)
    records_api_client.produce_record(
        topic_name=TEST_TOPIC, record=Record(value=TEST_RECORD)
    )


@pytest.fixture(scope="class")
def debezium_namespace(admin_client):
    with cluster_resource(Namespace)(
        client=admin_client, name="mas-debezium"
    ) as dbz_ns:
        dbz_ns.wait_for_status(
            status=Namespace.Status.ACTIVE, timeout=WAIT_STATUS_TIMEOUT
        )
        yield dbz_ns


@pytest.fixture(scope="class")
def consumer_pod(
    admin_client, kafka_instance_ready, kafka_instance_sa, debezium_namespace
):
    with cluster_resource(ConsumerPod)(
        client=admin_client,
        name="kafka-consumer-pod",
        namespace=debezium_namespace.name,
        consumer_image="edenhill/kcat:1.7.1",
        kafka_bootstrap_url=kafka_instance_ready.bootstrap_server_host,
        kafka_sa_client_id=kafka_instance_sa.id,
        kafka_sa_client_secret=kafka_instance_sa.secret,
        kafka_test_topic=TEST_TOPIC,
    ) as consumer:
        consumer.wait_for_status(status=Pod.Status.RUNNING, timeout=WAIT_STATUS_TIMEOUT)
        yield consumer
