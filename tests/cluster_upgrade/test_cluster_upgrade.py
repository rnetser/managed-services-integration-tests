import pytest
from simple_logger.logger import get_logger

from tests.cluster_upgrade.utils import (
    get_clusterversion,
    wait_for_cluster_version_state_and_version,
)


LOGGER = get_logger(name=__name__)


@pytest.mark.upgrade
def test_cluster_upgrade(
    pytestconfig,
    cluster,
    target_version_in_available_upgrades,
    verified_no_existing_upgrade_policies,
    ocp_target_version,
    updated_upgrade_policies,
    upgradable_cloud_credentials_operator,
):
    LOGGER.info(
        f"Test cluster {cluster.name} upgrade from {cluster.instance.version.raw_id} to"
        f" {ocp_target_version}"
    )
    wait_for_cluster_version_state_and_version(
        cluster_version=get_clusterversion(dyn_client=cluster.ocp_client),
        target_ocp_version=ocp_target_version,
        collect_data=pytestconfig.getoption("--data-collector"),
    )
    cluster.wait_for_ocm_cluster_version(ocp_target_version=ocp_target_version)
