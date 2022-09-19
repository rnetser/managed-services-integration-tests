import logging
import os

import pytest
import urllib3
from hvac import Client as hvacClient
from ocm_python_wrapper.cluster import Cluster
from ocp_resources.node import Node
from ocp_resources.resource import get_client

from utilities.constants import MPS_QE
from utilities.infra import get_ocm_client


LOGGER = logging.getLogger(__name__)
BASIC_LOGGER = logging.getLogger("basic")


@pytest.fixture(scope="session")
def admin_client():
    """
    Get DynamicClient
    """
    return get_client()


@pytest.fixture(scope="session")
def nodes(admin_client):
    yield list(Node.get(dyn_client=admin_client))


@pytest.fixture(scope="session")
def cluster_name(request):
    cluster_name = request.session.config.getoption(name="--cluster-name")
    assert cluster_name, "Cluster name is missing from cmdline"
    return cluster_name


@pytest.fixture(scope="session")
def cluster(ocm_client_scope_session, cluster_name):
    return Cluster(client=ocm_client_scope_session, name=cluster_name)


@pytest.fixture(scope="session")
def vault_config():
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    base_path = f"apps/data/{MPS_QE}/managed-services/rh-interop-qe-ms-account"

    vault_client = hvacClient(url="https://vault.corp.redhat.com:8200", verify=False)
    vault_client.auth.approle.login(
        role_id=MPS_QE,
        secret_id=os.environ["ANSIBLE_HASHI_VAULT_SECRET_ID"],
    )

    return vault_client.read(path=base_path)


@pytest.fixture(scope="session")
def ocm_client_scope_session(vault_config):
    return get_ocm_client(vault_config=vault_config)


@pytest.fixture(scope="class")
def ocm_client_scope_class(vault_config):
    return get_ocm_client(vault_config=vault_config)
