import os

import pytest
import requests
from ocp_resources.managed_cluster import ManagedCluster
from ocp_resources.multi_cluster_observability import MultiClusterObservability
from ocp_resources.route import Route
from pytest_testconfig import config as py_config
from simple_logger.logger import get_logger


LOGGER = get_logger(name=__name__)


@pytest.fixture(scope="session")
def kubeadmin_token():
    kubeadmin_token_env_var_name = "KUBEADMIN_TOKEN"
    token = os.getenv(kubeadmin_token_env_var_name, py_config.get("kubeadmin_token", ""))

    assert token, (
        "kubeadmin token is not set; either set as an environment variable"
        f" {kubeadmin_token_env_var_name} or via pytest command line using"
        " --tc:kubeadmin_token=<kubeadmin token>"
    )

    return token


@pytest.fixture(scope="session")
def multi_cluster_observability(admin_client_scope_session):
    observability = MultiClusterObservability(
        client=admin_client_scope_session,
        name="observability",
    )
    assert observability.exists, f"{observability.name} MultiClusterObservability does not exist"
    observability.wait_for_condition(
        condition=observability.Condition.READY,
        status=observability.Condition.Status.TRUE,
        timeout=5,
    )

    return observability


@pytest.fixture(scope="session")
def rbac_proxy_route_url(admin_client_scope_session, multi_cluster_observability):
    rbac_proxy_route = Route(
        client=admin_client_scope_session,
        name="rbac-query-proxy",
        namespace="open-cluster-management-observability",
    )
    assert rbac_proxy_route.exists, f"{rbac_proxy_route.name} Route does not exist"

    return rbac_proxy_route.instance.spec.host


@pytest.fixture(scope="session")
def etcd_metrics_query(rbac_proxy_route_url, kubeadmin_token):
    query_name = "etcd_debugging_mvcc_db_total_size_in_bytes"
    query_result = requests.get(
        url=f"https://{rbac_proxy_route_url}/api/v1/query?query={query_name}",
        headers={
            "Authorization": f"Bearer {kubeadmin_token}",
        },
        verify=False,  # TODO: add certificate to verify query
    )

    assert query_result.ok, (
        f"Query request at {rbac_proxy_route_url} for '{query_name}' metric failed with"
        f" status {query_result.status_code}: {query_result.reason}"
    )
    return query_result.json()["data"]["result"]


@pytest.fixture(scope="session")
def clusters_etcd_metrics(etcd_metrics_query):
    clusters_etcd_metrics = {}

    for metric_result in etcd_metrics_query:
        clusters_etcd_metrics.setdefault(metric_result["metric"]["cluster"], []).append(metric_result["value"][0])

    assert clusters_etcd_metrics, "No clusters metrics found"

    return clusters_etcd_metrics


@pytest.fixture(scope="session")
def observability_reported_clusters(clusters_etcd_metrics):
    _observability_reported_clusters = [cluster_name for cluster_name in clusters_etcd_metrics]
    LOGGER.info(f"Observability reported clusters: {_observability_reported_clusters}")

    return _observability_reported_clusters


@pytest.fixture(scope="session")
def acm_clusters(admin_client_scope_session):
    _acm_clusters = [cluster.name for cluster in ManagedCluster.get(dyn_client=admin_client_scope_session)]

    assert _acm_clusters, "No ACM clusters found"
    LOGGER.info(f"ACM clusters: {_acm_clusters}")

    return _acm_clusters
