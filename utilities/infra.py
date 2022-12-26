import logging

from ocm_python_wrapper.ocm_client import OCMPythonClient
from ocp_utilities.exceptions import NodeNotReadyError, NodeUnschedulableError
from ocp_utilities.infra import assert_nodes_ready, assert_nodes_schedulable
from pytest_testconfig import py_config

from utilities.pytest_utils import exit_pytest_execution


LOGGER = logging.getLogger(__name__)


def cluster_sanity(
    nodes,
    junitxml_property,
):
    """
    Args:
        nodes (list): list of Node resources

    Raises:
        NodeNotReadyError or NodeUnschedulableError if node check failed
    """

    exceptions_filename = "cluster_sanity_failure.txt"
    try:
        LOGGER.info("Running cluster sanity")
        # validate that all the nodes are ready and schedulable
        LOGGER.info("Check nodes sanity.")
        assert_nodes_ready(nodes=nodes)
        assert_nodes_schedulable(nodes=nodes)

    except (NodeNotReadyError, NodeUnschedulableError) as ex:
        exit_pytest_execution(
            filename=exceptions_filename,
            message=ex.args[0],
            junitxml_property=junitxml_property,
        )


def get_ocm_client(token):
    api_host = py_config["api_server"]
    LOGGER.info(f"Running against {api_host}")
    ocm_client = OCMPythonClient(
        token=token,
        endpoint="https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token",
        api_host=api_host,
        discard_unknown_keys=True,
    )
    return ocm_client.client
