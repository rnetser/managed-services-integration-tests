import contextlib
import logging

from ocm_python_wrapper.ocm_client import OCMPythonClient
from ocp_utilities.exceptions import (
    NodeNotReadyError,
    NodesNotHealthyConditionError,
    NodeUnschedulableError,
    PodsFailedOrPendingError,
)
from ocp_utilities.infra import (
    assert_nodes_in_healthy_condition,
    assert_nodes_schedulable,
    assert_pods_failed_or_pending,
)
from pytest_testconfig import py_config
from rhoas_kafka_mgmt_sdk.exceptions import ApiException

from utilities.pytest_utils import exit_pytest_execution


LOGGER = logging.getLogger(__name__)


def cluster_sanity(
    nodes,
    pods,
    junitxml_property,
):
    """
    Args:
        nodes (list): list of Node resources
        pods (list): list of Pod resources

    Raises:
        NodeNotReadyError or NodeUnschedulableError or PodsFailedOrPendingError or
        NodesNotHealthyConditionError: if node check failed
    """

    exceptions_filename = "cluster_sanity_failure.txt"
    try:
        LOGGER.info("Running cluster sanity")
        LOGGER.info("Check nodes sanity.")
        assert_nodes_schedulable(nodes=nodes)
        assert_nodes_in_healthy_condition(nodes=nodes)
        assert_pods_failed_or_pending(pods=pods)

    except (
        NodeNotReadyError,
        NodeUnschedulableError,
        PodsFailedOrPendingError,
        NodesNotHealthyConditionError,
    ) as ex:
        exit_pytest_execution(
            filename=exceptions_filename,
            message=ex.args[0],
            junitxml_property=junitxml_property,
        )


def get_ocm_client(token):
    api_host = py_config["api_server"]
    LOGGER.info(f"Running against {api_host}")
    ocm_client = OCMPythonClient(
        token=token.strip(),
        endpoint="https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token",
        api_host=api_host,
        discard_unknown_keys=True,
    )
    return ocm_client.client


def get_kafka_supported_region(rosa_regions, kafka_mgmt_api_instance):
    cloud_provider = py_config["cloud_provider"]
    LOGGER.info(
        f"Searching for an available kafka cloud region under {cloud_provider} cloud provider"
    )
    for region_dict in rosa_regions:
        region_id = region_dict["id"]
        with contextlib.suppress(ApiException):
            kafka_mgmt_api_instance.get_instance_types_by_cloud_provider_and_region(
                cloud_provider=cloud_provider, cloud_region=region_id
            )
            return region_id
