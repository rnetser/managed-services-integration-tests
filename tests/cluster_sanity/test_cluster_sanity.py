import pytest

from utilities.infra import cluster_sanity


@pytest.mark.smoke
def test_cluster_sanity(nodes, junitxml_plugin):
    cluster_sanity(
        nodes=nodes,
        junitxml_property=junitxml_plugin,
    )
