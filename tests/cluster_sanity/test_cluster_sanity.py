import pytest
from ocp_resources.node import Node
from ocp_resources.pod import Pod
from ocp_utilities.infra import get_client

from utilities.infra import cluster_sanity


@pytest.fixture()
def admin_client_scope_function(kubeconfig_file_paths):
    """
    Get DynamicClient
    """
    return get_client(config_file=kubeconfig_file_paths if kubeconfig_file_paths else None)


@pytest.fixture(scope="session")
def pods_scope_session(admin_client_scope_session):
    return list(Pod.get(dyn_client=admin_client_scope_session))


@pytest.fixture()
def pods_scope_function(admin_client_scope_function):
    return list(Pod.get(dyn_client=admin_client_scope_function))


@pytest.fixture()
def nodes_scope_function(admin_client_scope_function):
    yield list(Node.get(dyn_client=admin_client_scope_function))


@pytest.mark.smoke
def test_cluster_sanity(nodes_scope_session, pods_scope_session, junitxml_plugin):
    cluster_sanity(
        nodes=nodes_scope_session,
        pods=pods_scope_session,
        junitxml_property=junitxml_plugin,
    )


@pytest.mark.smoke_multi
def test_multi_clusters_sanity(
    nodes_scope_function,
    pods_scope_function,
):
    cluster_sanity(
        nodes=nodes_scope_function,
        pods=pods_scope_function,
        exit_pytest=False,
    )
