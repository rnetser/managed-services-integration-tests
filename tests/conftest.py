import os

import pytest
from ocm_python_wrapper.cluster import Cluster
from ocp_resources.node import Node
from ocp_resources.resource import get_client
from pytest_testconfig import py_config

from utilities.infra import get_ocm_client
from utilities.vault_utils import get_vault_config


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
    assert request.session.config.getoption(
        name="--cluster-name"
    ), "Cluster name is missing from cmdline"


@pytest.fixture(scope="session")
def cluster(ocm_client_scope_session, cluster_name):
    return Cluster(client=ocm_client_scope_session, name=cluster_name)


@pytest.fixture(scope="session")
def ocm_client_scope_session(ocm_token):
    return get_ocm_client(token=ocm_token)


@pytest.fixture(scope="class")
def ocm_client_scope_class(ocm_token):
    return get_ocm_client(token=ocm_token)


@pytest.fixture(scope="session")
def ocm_token():
    token = os.getenv("OCM_TOKEN")
    if token:
        return token
    ocm_token_key = (
        "ocm_api_token"
        if py_config["api_server"] == "production"
        else "ocm_stage_api_token"
    )
    return get_vault_config(path="rh-interop-qe-ms-account")["data"]["data"][
        ocm_token_key
    ]
