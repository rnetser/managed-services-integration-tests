import os

import pytest
import rosa.cli
from ocm_python_wrapper.cluster import Cluster
from ocp_resources.node import Node
from ocp_utilities.infra import get_client
from simple_logger.logger import get_logger

from utilities.infra import get_ocm_client


LOGGER = get_logger(name=__name__)


class RosaCommandError(Exception):
    pass


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


@pytest.fixture(scope="session")
def ocp_target_version(request):
    cmdline_option = "--ocp-target-version"
    ocp_target_version = request.config.getoption(cmdline_option)
    assert ocp_target_version, f"{cmdline_option} cmdline option not provided"
    return ocp_target_version


@pytest.fixture(scope="session")
def rosa_regions(rosa_allowed_commands):
    # A region (any region) is required for ROSA commands
    return rosa.cli.execute(
        command="list regions --region us-west-2",
        allowed_commands=rosa_allowed_commands,
    )["out"]


@pytest.fixture(scope="session")
def rosa_allowed_commands():
    # Get ROSA allowed commands to save execution time
    return rosa.cli.parse_help()
