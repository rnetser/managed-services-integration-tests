import logging

import pytest
import rhoas_kafka_instance_sdk
from constants import CLOUD_PROVIDER, KAFKA_TOPICS_LIST
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
from rhoas_kafka_mgmt_sdk.exceptions import ApiException
from rhoas_kafka_mgmt_sdk.model.kafka_request_payload import KafkaRequestPayload
from rhoas_service_accounts_mgmt_sdk.model.service_account_create_request_data import (
    ServiceAccountCreateRequestData,
)


LOGGER = logging.getLogger(__name__)
WAIT_STATUS_TIMEOUT = 120


class NoAvailableRegionsError(Exception):
    pass


@pytest.fixture(scope="class")
def kafka_instance_region(kafka_mgmt_api_instance, rosa_regions):
    LOGGER.info(
        f"Searching for available kafka cloud region under {CLOUD_PROVIDER} cloud provider"
    )
    for region_dict in rosa_regions:
        try:
            kafka_mgmt_api_instance.get_instance_types_by_cloud_provider_and_region(
                cloud_provider=CLOUD_PROVIDER, cloud_region=region_dict["id"]
            )
            return region_dict["id"]
        except ApiException:
            continue

    raise NoAvailableRegionsError


@pytest.fixture(scope="class")
def kafka_instance(kafka_mgmt_api_instance, kafka_instance_region):
    kafka_name = "msi-kafka"
    LOGGER.info(f"Creating {kafka_name} kafka instance")
    _async = True
    kafka_request_payload = KafkaRequestPayload(
        cloud_provider=CLOUD_PROVIDER,
        name=kafka_name,
        region=kafka_instance_region,
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

    LOGGER.info(f"Waiting for {kafka_name} kafka instance to be deleted")
    kafka_mgmt_api_instance.delete_kafka_by_id(
        async_req=True, _async=_async, id=kafka_create_api.id
    )
    kafka_list_samples = TimeoutSampler(
        wait_timeout=WAIT_STATUS_TIMEOUT,
        sleep=10,
        func=kafka_mgmt_api_instance.get_kafkas,
        search=f"name = {kafka_name}",
    )
    kafka_list_sample = None
    try:
        for kafka_list_sample in kafka_list_samples:
            if kafka_list_sample.size == 0:
                return
    except TimeoutExpiredError:
        LOGGER.error(
            f"Timeout expired for deleting {kafka_name} kafka instance:\n"
            f"{kafka_list_sample}"
        )
        raise


@pytest.fixture(scope="class")
def kafka_instance_ready(kafka_mgmt_api_instance, kafka_instance):
    LOGGER.info(f"Waiting for {kafka_instance.name} kafka instance to be ready")
    kafka_samples = TimeoutSampler(
        wait_timeout=450,
        sleep=10,
        func=kafka_mgmt_api_instance.get_kafka_by_id,
        id=kafka_instance.id,
    )
    kafka_sample = None
    try:
        for kafka_sample in kafka_samples:
            if kafka_sample.status == "ready":
                return kafka_sample
    except TimeoutExpiredError:
        LOGGER.error("Timeout expired. Current kafka snapshot:\n" f"{kafka_sample}")
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
def kafka_instance_sa(
    kafka_instance_client, kafka_instance, service_accounts_api_instance
):
    kafka_sa_name = f"{kafka_instance.name}-sa"
    LOGGER.info(
        f"Creating {kafka_sa_name} service-account for {kafka_instance.name} kafka instance"
    )
    service_account_create_request_data = ServiceAccountCreateRequestData(
        name=kafka_sa_name,
        description=f"{kafka_instance.name} instance service-account",
    )
    kafka_sa = service_accounts_api_instance.create_service_account(
        service_account_create_request_data=service_account_create_request_data
    )
    assert (
        kafka_sa.id
    ), f"Failed to create service-account for kafka. API response:\n{kafka_sa}"

    yield kafka_sa

    LOGGER.info(f"Waiting for {kafka_sa_name} service-account to be deleted")
    service_accounts_api_instance.delete_service_account(id=kafka_sa.id, async_req=True)
    sa_list_samples = TimeoutSampler(
        wait_timeout=WAIT_STATUS_TIMEOUT,
        sleep=10,
        func=service_accounts_api_instance.get_service_accounts,
        client_id=[kafka_sa.id],
    )
    # if a service-account with given id does not exist, an empty list will be returned
    sa_list_sample = "N/A"
    try:
        for sa_list_sample in sa_list_samples:
            if not sa_list_sample:
                return
    except TimeoutExpiredError:
        LOGGER.error(
            f"Timeout expired for deleting {kafka_sa_name} kafka service account:\n"
            f"{sa_list_sample}"
        )
        raise


@pytest.fixture(scope="class")
def kafka_sa_acl_binding(kafka_instance_client, kafka_instance, kafka_instance_sa):
    LOGGER.info(
        f"Binding acls for {kafka_instance_sa.name} service-account with {kafka_instance.name} kafka instance"
    )
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
def kafka_topics(kafka_instance_client, kafka_instance):
    LOGGER.info(f"Creating kafka topics for {kafka_instance.name} kafka instance")

    created_topics = []
    kafka_topics_api_instance = topics_api.TopicsApi(api_client=kafka_instance_client)
    for topic_name in KAFKA_TOPICS_LIST:
        new_topic_input = NewTopicInput(
            name=topic_name,
            settings=TopicSettings(
                num_partitions=1,
                config=[
                    ConfigEntry(
                        key="cleanup.policy",
                        value="delete",
                    ),
                ],
            ),
        )
        created_topics.append(
            kafka_topics_api_instance.create_topic(new_topic_input=new_topic_input)
        )

    return created_topics


@pytest.fixture(scope="class")
def first_kafka_topic_name(kafka_topics):
    return kafka_topics[0].name


@pytest.fixture(scope="class")
def kafka_record(kafka_instance_client, first_kafka_topic_name):
    test_record = "This is a topic test record"
    LOGGER.info(
        f"Producing test record '{test_record}' to {first_kafka_topic_name} kafka topic"
    )
    records_api_client = records_api.RecordsApi(api_client=kafka_instance_client)
    records_api_client.produce_record(
        topic_name=first_kafka_topic_name, record=Record(value=test_record)
    )
    return test_record


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
    admin_client,
    kafka_instance_ready,
    kafka_instance_sa,
    debezium_namespace,
    first_kafka_topic_name,
):
    with cluster_resource(ConsumerPod)(
        client=admin_client,
        name="kafka-consumer-pod",
        namespace=debezium_namespace.name,
        consumer_image="edenhill/kcat:1.7.1",
        kafka_bootstrap_url=kafka_instance_ready.bootstrap_server_host,
        kafka_sa_client_id=kafka_instance_sa.id,
        kafka_sa_client_secret=kafka_instance_sa.secret,
        kafka_test_topic=first_kafka_topic_name,
    ) as consumer_pod:
        consumer_pod.wait_for_status(
            status=Pod.Status.RUNNING, timeout=WAIT_STATUS_TIMEOUT
        )
        yield consumer_pod
