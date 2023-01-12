import pytest
from ocp_resources.pod import Pod

from utilities.infra import cluster_sanity


@pytest.fixture(scope="session")
def pods(admin_client):
    return list(Pod.get(dyn_client=admin_client))


@pytest.mark.smoke
def test_cluster_sanity(nodes, pods, junitxml_plugin):
    cluster_sanity(
        nodes=nodes,
        pods=pods,
        junitxml_property=junitxml_plugin,
    )
