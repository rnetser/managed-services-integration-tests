import logging
import os

import pytest
import requests
import urllib3
from hvac import Client as hvacClient
from ocm_python_wrapper.cluster import Cluster
from ocp_resources.node import Node
from ocp_resources.resource import get_client
from pytest_testconfig import py_config

from utilities.constants import MPS_QE
from utilities.infra import get_ocm_client


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LOGGER = logging.getLogger(__name__)
BASIC_LOGGER = logging.getLogger("basic")


def get_vault_config():
    try:
        hashi_vault_env_var_name = "ANSIBLE_HASHI_VAULT_SECRET_ID"
        secret_id = os.getenv(hashi_vault_env_var_name)
        assert secret_id, f"{hashi_vault_env_var_name} environment variable is not set."
        base_path = f"apps/data/{MPS_QE}/managed-services/rh-interop-qe-ms-account"

        vault_client = hvacClient(
            url="https://vault.corp.redhat.com:8200", verify=False
        )
        vault_client.auth.approle.login(
            role_id=MPS_QE,
            secret_id=secret_id,
        )

        return vault_client.read(path=base_path)
    except requests.exceptions.ConnectionError:
        LOGGER.error("Failed to connect to vault.")
        raise


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
    return get_vault_config()["data"]["data"][ocm_token_key]
