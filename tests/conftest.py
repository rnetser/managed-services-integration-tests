import json
import logging
import os
import shlex

import pytest
from ocm_python_wrapper.cluster import Cluster
from ocp_resources.node import Node
from ocp_utilities.infra import get_client
from ocp_utilities.utils import run_command

from utilities.infra import get_ocm_client


LOGGER = logging.getLogger(__name__)


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
def rosa_regions():
    # A region (any region) is required for ROSA commands
    cmd_succeeded, cmd_out, cmd_err = run_command(
        command=shlex.split("rosa list regions -ojson --region us-west-2")
    )
    if cmd_succeeded:
        return json.loads(cmd_out)
    LOGGER.error(f"Failed to get ROSA regions, error: {cmd_err}")
    raise RosaCommandError
