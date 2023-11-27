import pytest


pytestmark = [pytest.mark.acm_observability, pytest.mark.usefixtures("multi_cluster_observability")]


class TestACMObservability:
    def test_all_clusters_metrics_reported(self, observability_reported_clusters, acm_clusters):
        observability_missing_report_clusters = [
            cluster for cluster in acm_clusters if cluster not in observability_reported_clusters
        ]
        assert not observability_missing_report_clusters, (
            "Not all ACM clusters "
            f"are reported via observability: {observability_missing_report_clusters}, "
            f"clusters expected: {acm_clusters}"
        )

    def test_acm_clusters_etcd_metrics_exist_and_valid(self, clusters_etcd_metrics, observability_reported_clusters):
        failed_acm_clusters = {}

        for cluster_name in observability_reported_clusters:
            # Checking given cluster's last etcd db size metric updated via observability
            latest_etcd_db_size = clusters_etcd_metrics[cluster_name][-1]
            if not (isinstance(latest_etcd_db_size, float) and latest_etcd_db_size > 0):
                failed_acm_clusters[cluster_name] = latest_etcd_db_size

        assert (
            not failed_acm_clusters
        ), f"The following ACM clusters etcd db size metric is invalid: {failed_acm_clusters}"
