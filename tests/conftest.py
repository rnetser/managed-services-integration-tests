import json
import logging
import os
import shlex

import pytest
import rhoas_kafka_instance_sdk
import rhoas_kafka_mgmt_sdk
import rhoas_kafka_mgmt_sdk.api.default_api
from auth.rhoas_auth import get_access_token
from ocm_python_wrapper.cluster import Cluster
from ocm_python_wrapper.ocm_client import OCMPythonClient
from ocp_resources.node import Node
from ocp_resources.utils import TimeoutExpiredError, TimeoutSampler
from ocp_utilities.infra import get_client
from ocp_utilities.utils import run_command
from pytest_testconfig import py_config
from rhoas_kafka_instance_sdk.api import topics_api
from rhoas_kafka_instance_sdk.model.config_entry import ConfigEntry
from rhoas_kafka_instance_sdk.model.new_topic_input import NewTopicInput
from rhoas_kafka_instance_sdk.model.topic_settings import TopicSettings
from rhoas_kafka_mgmt_sdk.model.kafka_request_payload import KafkaRequestPayload

from utilities.constants import KAFKA_TOPICS_LIST, WAIT_STATUS_TIMEOUT
from utilities.infra import get_ocm_client


LOGGER = logging.getLogger(__name__)


class RosaCommandError(Exception):
    pass


@pytest.fixture(scope="session")
def admin_client():
    """
    Get DynamicClient
    """
    return get_client()


@pytest.fixture(scope="session")
def nodes(admin_client):
    yield list(Node.get(dyn_client=admin_client))


@pytest.fixture(scope="session")
def cluster_name(request):
    cluster_name = request.session.config.getoption(name="--cluster-name")
    assert cluster_name, "Cluster name is missing from cmdline"
    return cluster_name


@pytest.fixture(scope="session")
def cluster(ocm_client_scope_session, cluster_name):
    return Cluster(client=ocm_client_scope_session, name=cluster_name)


@pytest.fixture(scope="session")
def ocm_client_scope_session(ocm_token):
    return get_ocm_client(token=ocm_token)


@pytest.fixture(scope="session")
def ocm_token():
    ocm_token_env_var_name = "OCM_TOKEN"
    token = os.getenv(ocm_token_env_var_name)
    assert token, f"{ocm_token_env_var_name} environment variable is not set."
    return token


@pytest.fixture(scope="session")
def ocp_target_version(request):
    cmdline_option = "--ocp-target-version"
    ocp_target_version = request.config.getoption(cmdline_option)
    assert ocp_target_version, f"{cmdline_option} cmdline option not provided"
    return ocp_target_version


@pytest.fixture(scope="session")
def rosa_regions():
    # A region (any region) is required for ROSA commands
    cmd_succeeded, cmd_out, cmd_err = run_command(
        command=shlex.split("rosa list regions -ojson --region us-west-2")
    )
    if cmd_succeeded:
        return json.loads(cmd_out)
    LOGGER.error(f"Failed to get ROSA regions, error: {cmd_err}")
    raise RosaCommandError


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
def kafka_instance(kafka_mgmt_api_instance, kafka_supported_region):
    kafka_name = "msi-kafka"
    LOGGER.info(f"Creating {kafka_name} kafka instance")
    _async = True
    kafka_request_payload = KafkaRequestPayload(
        cloud_provider=py_config["cloud_provider"],
        name=kafka_name,
        region=kafka_supported_region,
        plan="standard.x1",
        reauthentication_enabled=True,
    )
    requested_kafka_dict = kafka_mgmt_api_instance.create_kafka(
        _async=_async, kafka_request_payload=kafka_request_payload
    )
    assert (
        requested_kafka_dict.status == "accepted"
    ), f"Failed to create a kafka instance. API response:\n{requested_kafka_dict}"

    yield requested_kafka_dict

    LOGGER.info(f"Waiting for {requested_kafka_dict.name} kafka instance to be deleted")
    kafka_mgmt_api_instance.delete_kafka_by_id(
        async_req=True, _async=_async, id=requested_kafka_dict.id
    )
    kafka_list_samples = TimeoutSampler(
        wait_timeout=WAIT_STATUS_TIMEOUT,
        sleep=10,
        func=kafka_mgmt_api_instance.get_kafkas,
        search=f"name = {requested_kafka_dict.name}",
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


@pytest.fixture(scope="session")
def ocm_base_api_url():
    return OCMPythonClient.get_base_api_uri(api_host=py_config["api_server"])


@pytest.fixture(scope="session")
def access_token(ocm_token):
    return get_access_token(offline_token=ocm_token)["access_token"]


@pytest.fixture(scope="session")
def kafka_mgmt_client(ocm_base_api_url, access_token):
    # https://github.com/redhat-developer/app-services-sdk-python/tree/main/sdks/kafka_mgmt_sdk
    configuration = rhoas_kafka_mgmt_sdk.Configuration(
        host=ocm_base_api_url,
        access_token=access_token,
    )
    with rhoas_kafka_mgmt_sdk.ApiClient(configuration=configuration) as api_client:
        yield api_client


@pytest.fixture(scope="session")
def kafka_mgmt_api_instance(kafka_mgmt_client):
    return rhoas_kafka_mgmt_sdk.api.default_api.DefaultApi(api_client=kafka_mgmt_client)


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
