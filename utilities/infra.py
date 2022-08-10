import logging

from ocp_resources.storage_class import StorageClass

from ocp_utilities.exceptions import ClusterSanityError
from ocp_utilities.infra import validate_nodes_ready, validate_nodes_schedulable
from ocp_utilities.pytest_utils import exit_pytest_execution


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
            raise ClusterSanityError(
                err_str=f"Cluster is missing storage class. Expected {_cluster_storage_classes}\n,"
                f"missing sc {missing_storage_classes}\n"
            )

    exceptions_filename = "cluster_sanity_failure.txt"
    try:
        LOGGER.info("Running cluster sanity")
        if cluster_storage_classes:
            _storage_sanity_check(_cluster_storage_classes=cluster_storage_classes)

        # validate that all the nodes are ready and schedulable
        LOGGER.info("Check nodes sanity.")
        validate_nodes_ready(nodes=nodes)
        validate_nodes_schedulable(nodes=nodes)

    except ClusterSanityError as ex:
        exit_pytest_execution(
            filename=exceptions_filename,
            message=ex.err_str,
            junitxml_property=junitxml_property,
        )
