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
from simple_logger.logger import get_logger

from utilities.pytest_utils import exit_pytest_execution


LOGGER = get_logger(name=__name__)


def cluster_sanity(
    nodes,
    pods,
    junitxml_property=None,
    exit_pytest=True,
):
    """
    Args:
        nodes (list): list of Node resources
        pods (list): list of Pod resources
        junitxml_property (pytest plugin): record_testsuite_property
        exit_pytest (bool): Exit pytest execution on failure if True else raise relevant exception

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
        if exit_pytest:
            exit_pytest_execution(
                filename=exceptions_filename,
                message=ex.args[0],
                junitxml_property=junitxml_property,
            )

        raise ex


def get_ocm_client(token):
    api_host = py_config["ocm_api_server"]
    LOGGER.info(f"Running against {api_host}")
    ocm_client = OCMPythonClient(
        token=token.strip(),
        endpoint="https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token",
        api_host=api_host,
        discard_unknown_keys=True,
    )
    return ocm_client.client
