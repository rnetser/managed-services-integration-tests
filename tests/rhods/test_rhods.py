import logging

import pytest
from ocm_python_client.model.add_on_installation_parameter import (
    AddOnInstallationParameter,
)


LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def installed_rhods(cluster):
    addon_installation_dict = {
        "id": "managed-odh",
        "addon": {"id": "managed-odh"},
        "parameters": [
            AddOnInstallationParameter(
                {"id": "notification-email", "name": "sss@xxx.com"}
            )
        ],
    }
    return cluster.install_addon(addon_installation_dict=addon_installation_dict)


def test_rhods(installed_rhods):
    LOGGER.info("Test installing RHODS")
    # import ipdb
    #
    # ipdb.set_trace()
