import logging
import time

import pytest
import rhoas_kafka_instance_sdk
import rhoas_kafka_mgmt_sdk
import rhoas_service_accounts_mgmt_sdk
from constants import (
    KAFKA_CLOUD_PROVIDER,
    KAFKA_NAME,
    KAFKA_REGION,
    KAFKA_SA_NAME,
    KAFKA_TIMEOUT_UNITS,
    KAFKA_TOPICS,
)
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
    )  # KafkaRequestPayload | Kafka data

    try:
        # Create kafka using kafka request payload configurations
        kafka_create_api = kafka_mgmt_api_instance.create_kafka(
            _async=_async, kafka_request_payload=kafka_request_payload
        )
        assert (
            kafka_create_api.status == "accepted"
        ), "Failed to create a kafka instance."

        # wait for kafka instance to be ready
        timeout = KAFKA_TIMEOUT_UNITS
        while (
            kafka_mgmt_api_instance.get_kafka_by_id(kafka_create_api.id).status
            != "ready"
        ):
            LOGGER.info(
                f"Waiting on {KAFKA_NAME} kafka instance to be ready ({timeout * 10} sec. remaining)"
            )
            timeout -= 1
            if not timeout:
                break
            time.sleep(10)
        kafka_ready_api = kafka_mgmt_api_instance.get_kafka_by_id(
            id=kafka_create_api.id
        )
        assert (
            kafka_ready_api.status == "ready"
        ), "Kafka instance creating exceeded max. timeout limitations."

        yield kafka_ready_api

        # Kafka instance teardown
        # TODO: raises TypeError; work with Dimitri to resolve
        kafka_mgmt_api_instance.delete_kafka_by_id(id=kafka_ready_api.id, _async=_async)

    except rhoas_kafka_mgmt_sdk.ApiException as e:
        LOGGER.error(f"API Exception when calling DefaultApi: {e}")


@pytest.fixture(scope="session")
def kafka_instance_client(kafka_instance, access_token):
    # https://github.com/redhat-developer/app-services-sdk-python/tree/main/sdks/kafka_instance_sdk
    configuration = rhoas_kafka_instance_sdk.Configuration(
        host=kafka_instance.admin_api_server_url, access_token=access_token
    )

    return rhoas_kafka_instance_sdk.ApiClient(configuration=configuration)


@pytest.fixture(scope="session")
def kafka_instance_sa(kafka_instance_client, service_accounts_api_instance):
    service_account_create_request_data = ServiceAccountCreateRequestData(
        name=KAFKA_SA_NAME,
        description=f"{KAFKA_NAME} instance service-account",
    )

    try:
        # Creating the service-account using request-data
        kafka_sa_create_api = service_accounts_api_instance.create_service_account(
            service_account_create_request_data=service_account_create_request_data
        )
        assert kafka_sa_create_api, "Failed to create service-account for kafka"

        # Binding the service-account instance to kafka with all producer/consumer privileges
        # TODO: move full acl creating procedure to a utilities module
        acl_api_instance = acls_api.AclsApi(api_client=kafka_instance_client)
        acl_binding = AclBinding(
            resource_type=AclResourceType("TOPIC"),
            resource_name="*",
            pattern_type=AclPatternType("LITERAL"),
            permission=AclPermissionType("ALLOW"),
            principal=f"User:{kafka_sa_create_api.id}",
            operation=AclOperation("ALL"),
        )  # AclBinding | ACL to create.
        kafka_sa_acl = acl_api_instance.create_acl(
            acl_binding=acl_binding
        )  # TODO: bad call; check params

        LOGGER.info(f"kafka service-account:\n{kafka_sa_create_api}")
        LOGGER.info(f"kafka service-account binding:\n{kafka_sa_acl}")

        yield kafka_sa_create_api

        # Kafka service-account teardown
        acl_api_instance.delete_acls(
            principal=f"User:{kafka_sa_create_api.id}"
        )  # TODO: bad call; check params
        service_accounts_api_instance.delete_service_account(
            id=kafka_sa_create_api.id
        )  # TODO: not deleting properly.

    except rhoas_service_accounts_mgmt_sdk.ApiException as e:
        LOGGER.error(f"Exception when calling ServiceAccountsApi: {e}")


@pytest.fixture(scope="session")
def service_registry():
    return


@pytest.fixture(scope="session")
def service_registry_sa(service_registry):
    return


@pytest.fixture(scope="session")
def kafka_topics(kafka_instance_client):
    # Create an instance of the API class
    kafka_topics_api_instance = topics_api.TopicsApi(api_client=kafka_instance_client)

    # Create all specified kafka topics
    for topic_config in KAFKA_TOPICS:
        new_topic_input = NewTopicInput(
            name=topic_config["name"],
            settings=TopicSettings(
                num_partitions=topic_config["num_partitions"],
                config=[
                    ConfigEntry(
                        key="cleanup.policy",
                        value=topic_config["cleanup_policy"],
                    ),
                ],
            ),
        )  # NewTopicInput | Topic to create.

        try:
            # Creates a new topic
            kafka_topics_api_instance.create_topic(new_topic_input=new_topic_input)
        except rhoas_kafka_instance_sdk.ApiException as e:
            LOGGER.error(f"Exception when calling TopicsApi: {e}")

    return kafka_topics


@pytest.fixture(scope="session")
def mas_debezium_ns():
    return


@pytest.fixture(scope="session")
def mysql_db_pod(mas_debezium_ns):
    return


@pytest.fixture(scope="session")
def mysql_debezium_pod(mas_debezium_ns, kafka_instance_sa):
    return


@pytest.fixture(scope="session")
def avro_connector(kafka_instance_sa, service_registry_sa):
    return


@pytest.fixture(scope="session")
def deserialized_avro_records(kafka_instance_sa, service_registry_sa):
    return
