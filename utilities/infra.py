import logging

from ocm_python_wrapper.ocm_client import OCMPythonClient
from ocp_resources.storage_class import StorageClass
from ocp_utilities.exceptions import NodeNotReadyError, NodeUnschedulableError
from ocp_utilities.infra import assert_nodes_ready, assert_nodes_schedulable
from pytest_testconfig import py_config

from utilities.exceptions import StorageClassError
from utilities.pytest_utils import exit_pytest_execution


LOGGER = logging.getLogger(__name__)


def cluster_sanity(
    nodes,
    junitxml_property,
    cluster_storage_classes=None,
):
    """
    Args:
        nodes (list): list of Node resources
        cluster_storage_classes (list): list fo storage class names

    Raises:
        ClusterSanityError is node check and (optional) storage class check failed
    """

    def _storage_sanity_check(_cluster_storage_classes):
        LOGGER.info(f"Check storage classes sanity for {_cluster_storage_classes}.")
        missing_storage_classes = [
            sc for sc in _cluster_storage_classes if not StorageClass(name=sc).exists
        ]
        if missing_storage_classes:
            raise StorageClassError(
                f"Cluster is missing storage class. Expected {_cluster_storage_classes}\n,"
                f"missing sc {missing_storage_classes}\n"
            )

    exceptions_filename = "cluster_sanity_failure.txt"
    try:
        LOGGER.info("Running cluster sanity")
        if cluster_storage_classes:
            _storage_sanity_check(_cluster_storage_classes=cluster_storage_classes)

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
