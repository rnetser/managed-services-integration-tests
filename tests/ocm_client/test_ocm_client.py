import logging

import pytest
from ocm_python_client import ApiException
from ocp_resources.utils import TimeoutExpiredError, TimeoutSampler


LOGGER = logging.getLogger(__name__)


class TestOCMPythonClient:
    @pytest.mark.smoke
    def test_ocm_client(self, ocm_client_scope_class):
        versions = ocm_client_scope_class.api_clusters_mgmt_v1_versions_get()
        assert versions, "Failed to get versions"

    def test_cluster_instance(self, cluster):
        assert cluster.instance, f"Cannot fetch cluster {cluster.name} instance"

    def test_cluster_credentials(self, cluster):
        assert cluster.credentials, f"Fail to get cluster {cluster.name} credentials"

    def test_get_cluster_kubeconfig(self, cluster):
        assert cluster.kubeconfig, "Failed to get cluster kubeconfig"

    def test_client_timeout(self, cluster):
        samples = TimeoutSampler(
            wait_timeout=360,
            sleep=10,
            func=lambda: cluster.kubeconfig,
        )
        try:
            for sample in samples:
                if sample:
                    continue
        except TimeoutExpiredError:
            LOGGER.info("API client did not raise timeout exception.")
        except ApiException as ex:
            LOGGER.error(f"API client raised exception on {ex}")
            raise
