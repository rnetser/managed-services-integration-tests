import logging

import pytest
import rhoas_kafka_instance_sdk
from constants import (
    KAFKA_CLOUD_PROVIDER,
    KAFKA_NAME,
    KAFKA_REGION,
    KAFKA_SA_NAME,
    KAFKA_TIMEOUT,
    KAFKA_TOPICS,
)
from ocp_resources.utils import TimeoutSampler
from rhoas_kafka_instance_sdk.api import acls_api, topics_api
from rhoas_kafka_instance_sdk.model.acl_binding import AclBinding
from rhoas_kafka_instance_sdk.model.acl_operation import AclOperation
from rhoas_kafka_instance_sdk.model.acl_pattern_type import AclPatternType
from rhoas_kafka_instance_sdk.model.acl_permission_type import AclPermissionType
from rhoas_kafka_instance_sdk.model.acl_resource_type import AclResourceType
from rhoas_kafka_instance_sdk.model.config_entry import ConfigEntry
from rhoas_kafka_instance_sdk.model.new_topic_input import NewTopicInput
from rhoas_kafka_instance_sdk.model.topic_settings import TopicSettings
from rhoas_kafka_mgmt_sdk.model.kafka_request_payload import KafkaRequestPayload
from rhoas_service_accounts_mgmt_sdk.model.service_account_create_request_data import (
    ServiceAccountCreateRequestData,
)


LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def kafka_instance(kafka_mgmt_api_instance):
    _async = True
    kafka_request_payload = KafkaRequestPayload(
        cloud_provider=KAFKA_CLOUD_PROVIDER,
        name=KAFKA_NAME,
        region=KAFKA_REGION,
        reauthentication_enabled=True,
    )
    kafka_create_api = kafka_mgmt_api_instance.create_kafka(
        _async=_async, kafka_request_payload=kafka_request_payload
    )
    assert (
        kafka_create_api.status == "accepted"
    ), f"Failed to create a kafka instance. API response:\n{kafka_create_api}"

    kafka_status_samples = TimeoutSampler(
        wait_timeout=KAFKA_TIMEOUT,
        sleep=10,
        func=lambda: kafka_mgmt_api_instance.get_kafka_by_id(
            id=kafka_create_api.id
        ).status
        == "ready",
    )
    for sample in kafka_status_samples:
        if sample:
            break
    kafka_ready_api = kafka_mgmt_api_instance.get_kafka_by_id(id=kafka_create_api.id)
    yield kafka_ready_api

    # TODO: raises a TypeError; work with Dimitri to understand why
    kafka_mgmt_api_instance.delete_kafka_by_id(_async=_async, id=kafka_ready_api.id)


@pytest.fixture(scope="session")
def kafka_instance_client(kafka_instance, access_token):
    # https://github.com/redhat-developer/app-services-sdk-python/tree/main/sdks/kafka_instance_sdk
    configuration = rhoas_kafka_instance_sdk.Configuration(
        host=kafka_instance.admin_api_server_url, access_token=access_token
    )

    with rhoas_kafka_instance_sdk.ApiClient(configuration=configuration) as api_client:
        yield api_client


@pytest.fixture(scope="session")
def kafka_instance_sa(kafka_instance_client, service_accounts_api_instance):
    service_account_create_request_data = ServiceAccountCreateRequestData(
        name=KAFKA_SA_NAME,
        description=f"{KAFKA_NAME} instance service-account",
    )

    kafka_sa_create_api = service_accounts_api_instance.create_service_account(
        service_account_create_request_data=service_account_create_request_data
    )
    assert (
        kafka_sa_create_api.id
    ), f"Failed to create service-account for kafka. API response:\n{kafka_sa_create_api}"

    # Binding the service-account instance to kafka with all producer/consumer privileges
    # via AclBinding instance
    # TODO: move full acl creating procedure to a utilities module
    acl_api_instance = acls_api.AclsApi(api_client=kafka_instance_client)
    acl_binding = AclBinding(
        resource_type=AclResourceType("TOPIC"),
        resource_name="*",
        pattern_type=AclPatternType("LITERAL"),
        permission=AclPermissionType("ALLOW"),
        principal=f"User:{kafka_sa_create_api.id}",
        operation=AclOperation("ALL"),
    )
    acl_api_instance.create_acl(acl_binding=acl_binding)

    yield kafka_sa_create_api

    service_accounts_api_instance.delete_service_account(
        id=kafka_sa_create_api.id
    )  # TODO: not deleting properly.


@pytest.fixture(scope="session")
def kafka_topics(kafka_instance_client):
    kafka_topics_api_instance = topics_api.TopicsApi(api_client=kafka_instance_client)

    for topics_group in KAFKA_TOPICS:
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
    return kafka_topics
