import logging

import pytest
from ocp_resources.node import Node
from ocp_resources.resource import get_client


LOGGER = logging.getLogger(__name__)
BASIC_LOGGER = logging.getLogger("basic")


# Test-related fixtures
@pytest.fixture(scope="session", autouse=True)
def admin_client():
    """
    Get DynamicClient
    """
    return get_client()


@pytest.fixture(scope="session")
def nodes(admin_client):
    yield list(Node.get(dyn_client=admin_client))
