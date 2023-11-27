import json
import pytest
import base64
from ocp_resources.managed_cluster import ManagedCluster
from ocp_resources.multi_cluster_observability import MultiClusterObservability
from ocp_resources.secret import Secret
from simple_logger.logger import get_logger
from ocp_utilities.monitoring import Prometheus

LOGGER = get_logger(name=__name__)


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
def rbac_query_proxy_bearer_token(admin_client_scope_session):
    hub_cluster = "local-cluster"
    hub_cluster_secret = f"{hub_cluster}-cluster-secret"

    bearer_token_secret = Secret(
        client=admin_client_scope_session,
        name=hub_cluster_secret,
        namespace=hub_cluster,
    )
    assert bearer_token_secret.exists, f"{hub_cluster_secret} Secret does not exist"

    return json.loads(base64.b64decode(bearer_token_secret.instance.data.config))["bearerToken"]


@pytest.fixture(scope="session")
def etcd_metrics_query(admin_client_scope_session, rbac_query_proxy_bearer_token):
    return Prometheus(
        client=admin_client_scope_session,
        resource_name="rbac-query-proxy",
        namespace="open-cluster-management-observability",
        bearer_token=rbac_query_proxy_bearer_token,
    ).query_sampler(query="etcd_debugging_mvcc_db_total_size_in_bytes")


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
