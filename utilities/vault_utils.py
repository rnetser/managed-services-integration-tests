import logging
import os

import requests
import urllib3
from hvac import Client as hvacClient
from urllib3.exceptions import InsecureRequestWarning


urllib3.disable_warnings(InsecureRequestWarning)

LOGGER = logging.getLogger(__name__)
MPS_QE = "mps-qe"


def get_vault_config(path):
    try:
        hashi_vault_env_var_name = "ANSIBLE_HASHI_VAULT_SECRET_ID"
        secret_id = os.getenv(hashi_vault_env_var_name)
        assert secret_id, f"{hashi_vault_env_var_name} environment variable is not set."
        base_path = f"apps/data/{MPS_QE}/managed-services/{path}"

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
