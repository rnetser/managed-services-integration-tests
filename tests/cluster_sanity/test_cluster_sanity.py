import pytest
from pytest_testconfig import py_config

from utilities.infra import cluster_sanity


@pytest.mark.smoke
def test_cluster_sanity(nodes, junitxml_plugin):
    cluster_sanity(
        nodes=nodes,
        cluster_storage_classes=py_config.get("storage_classes"),
        junitxml_property=junitxml_plugin,
    )
