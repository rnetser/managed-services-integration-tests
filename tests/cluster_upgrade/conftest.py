import ast

import pytest
from ocp_resources.cluster_operator import ClusterOperator

from tests.cluster_upgrade.utils import cluster_upgrade_policy_dict


@pytest.fixture(scope="session")
def ocp_target_version(request):
    cmdline_option = "--ocp-target-version"
    ocp_target_version = request.config.getoption(cmdline_option)
    assert ocp_target_version, f"{cmdline_option} cmdline option not provided"
    return ocp_target_version


@pytest.fixture(scope="session")
def target_version_in_available_upgrades(cluster, ocp_target_version):
    available_upgrades = cluster.instance.version.available_upgrades
    assert (
        ocp_target_version in available_upgrades
    ), f"Target version {ocp_target_version} not found in {available_upgrades}"


@pytest.fixture(scope="session")
def verified_no_existing_upgrade_policies(cluster):
    assert (
        not cluster.upgrade_policies
    ), f"Cluster {cluster.name} has existing upgrade policies {cluster.upgrade_policies}"


@pytest.fixture(scope="session")
def updated_upgrade_policies(ocm_client_scope_session, cluster, ocp_target_version):
    cluster.update_upgrade_policies(
        upgrade_policies_dict=cluster_upgrade_policy_dict(
            target_version=ocp_target_version,
        ),
        wait=True,
    )


@pytest.fixture(scope="session")
def upgradable_cloud_credentials_operator(cluster):
    cloud_credential_name = "cloud-credential"
    cloud_credentials_operator = ClusterOperator(
        client=cluster.ocp_client, name=cloud_credential_name
    )
    cloud_credentials_operator_upgradeable_condition = [
        condition
        for condition in cloud_credentials_operator.instance.status.conditions
        if condition["type"] == "Upgradeable"
    ][0]
    assert ast.literal_eval(
        cloud_credentials_operator_upgradeable_condition["status"]
    ), f"{cloud_credential_name} operator is not upgradable: {cloud_credentials_operator_upgradeable_condition}"
