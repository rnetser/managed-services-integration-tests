import os

import pytest
from ocm_python_wrapper.cluster import Cluster
from ocp_resources.node import Node
from ocp_utilities.infra import get_client

from utilities.infra import get_ocm_client


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
def ocm_client_scope_session(ocm_token):
    return get_ocm_client(token=ocm_token)


@pytest.fixture(scope="session")
def ocm_token():
    ocm_token_env_var_name = "OCM_TOKEN"
    token = os.getenv(ocm_token_env_var_name)
    assert token, f"{ocm_token_env_var_name} environment variable is not set."
    return token
