import logging
from datetime import datetime, timedelta

from dateutil.tz import tzutc
from ocp_resources.cluster_version import ClusterVersion
from ocp_resources.utils import TimeoutExpiredError, TimeoutSampler


LOGGER = logging.getLogger(__name__)
UPGRADE_SCHEDULE_DELTA = 10 * 60
TIMEOUT_180MIN = 180 * 60


def cluster_upgrade_policy_dict(target_version):
    upgrade_next_run_time = get_upgrade_next_run_time()
    return {
        "kind": "UpgradePolicy",
        "schedule_type": "manual",
        "upgrade_type": "OSD",
        "version": target_version,
        "next_run": upgrade_next_run_time,
    }


def get_upgrade_next_run_time():
    # Expected patter example: 2006-01-02T15:04:05+07:00 with timezone
    now = datetime.now(tzutc())
    upgrade_next_run_time = now + timedelta(seconds=UPGRADE_SCHEDULE_DELTA)
    LOGGER.info(f"Set upgrade time to {upgrade_next_run_time}")

    return upgrade_next_run_time


def wait_for_cluster_version_state_and_version(cluster_version, target_ocp_version):
    def _cluster_version_state_and_version(_cluster_version, _target_ocp_version):
        cluster_version_status_history = _cluster_version.instance.status.history[0]
        LOGGER.info(f"clusterversion status.histroy: {cluster_version_status_history}")
        return (
            cluster_version_status_history.state == _cluster_version.Status.COMPLETED
            and cluster_version_status_history.version == target_ocp_version
        )

    try:
        for sample in TimeoutSampler(
            wait_timeout=TIMEOUT_180MIN + UPGRADE_SCHEDULE_DELTA,
            sleep=10,
            func=_cluster_version_state_and_version,
            _cluster_version=cluster_version,
            _target_ocp_version=target_ocp_version,
        ):
            if sample:
                return

    except TimeoutExpiredError:
        LOGGER.error(
            "Timeout reached while upgrading OCP."
            "clusterversion conditions: {cluster_version.instance.status.conditions}"
        )
        # TODO: Call collect_resources_for_test from new repo
        # collect_resources_for_test(resources_to_collect=[ClusterOperator])
        raise


def get_clusterversion(dyn_client):
    for cluster_version in ClusterVersion.get(dyn_client=dyn_client):
        return cluster_version
