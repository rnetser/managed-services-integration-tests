import pytest
import rhoas_connector_mgmt_sdk
import rhoas_kafka_mgmt_sdk
import rhoas_kafka_mgmt_sdk.api.default_api
import rhoas_service_accounts_mgmt_sdk
import rhoas_service_registry_mgmt_sdk
import rhoas_smart_events_mgmt_sdk
from auth.rhoas_auth import get_access_token
from ocm_python_wrapper.ocm_client import OCMPythonClient
from pytest_testconfig import py_config
from rhoas_connector_mgmt_sdk.api import connectors_api
from rhoas_service_accounts_mgmt_sdk.api import service_accounts_api
from rhoas_service_registry_mgmt_sdk.api import registries_api
from rhoas_smart_events_mgmt_sdk.api import bridges_api


@pytest.fixture(scope="session")
def ocm_base_api_url():
    return OCMPythonClient.get_base_api_uri(api_host=py_config["ocm_api_server"])


@pytest.fixture(scope="session")
def access_token(ocm_token):
    return get_access_token(offline_token=ocm_token)["access_token"]


# Management SDKs - support managing services
# Each API consists of a REST API client and an API instance.
# The API instance is used to interact with a specific API within the SDK.
# For example: `kafka_mgmt_sdk` SDK has `DefaultApi` and `SecurityApi`


@pytest.fixture(scope="session")
def kafka_mgmt_client(ocm_base_api_url, access_token):
    # https://github.com/redhat-developer/app-services-sdk-python/tree/main/sdks/kafka_mgmt_sdk
    configuration = rhoas_kafka_mgmt_sdk.Configuration(
        host=ocm_base_api_url,
        access_token=access_token,
    )
    with rhoas_kafka_mgmt_sdk.ApiClient(configuration=configuration) as api_client:
        yield api_client


@pytest.fixture(scope="session")
def kafka_mgmt_api_instance(kafka_mgmt_client):
    return rhoas_kafka_mgmt_sdk.api.default_api.DefaultApi(api_client=kafka_mgmt_client)


@pytest.fixture(scope="session")
def connector_mgmt_client(ocm_base_api_url, access_token):
    # https://github.com/redhat-developer/app-services-sdk-python/tree/main/sdks/connector_mgmt_sdk
    configuration = rhoas_connector_mgmt_sdk.Configuration(
        host=ocm_base_api_url,
        access_token=access_token,
        discard_unknown_keys=True,
    )
    with rhoas_connector_mgmt_sdk.ApiClient(configuration=configuration) as api_client:
        yield api_client


@pytest.fixture(scope="session")
def connector_mgmt_connectors_api_instance(connector_mgmt_client):
    return connectors_api.ConnectorsApi(api_client=connector_mgmt_client)


@pytest.fixture(scope="session")
def smart_events_mgmt_client(ocm_base_api_url, access_token):
    # https://github.com/redhat-developer/app-services-sdk-python/tree/main/sdks/smart_events_mgmt_sdk
    configuration = rhoas_smart_events_mgmt_sdk.Configuration(
        host=ocm_base_api_url,
        access_token=access_token,
    )
    with rhoas_smart_events_mgmt_sdk.ApiClient(configuration=configuration) as api_client:
        yield api_client


@pytest.fixture(scope="session")
def smart_events_mgmt_bridge_api_instance(smart_events_mgmt_client):
    return bridges_api.BridgesApi(api_client=smart_events_mgmt_client)


@pytest.fixture(scope="session")
def service_accounts_mgmt_client(access_token):
    # https://github.com/redhat-developer/app-services-sdk-python/tree/main/sdks/service_accounts_mgmt_sdk
    configuration = rhoas_service_accounts_mgmt_sdk.Configuration(
        host="https://sso.redhat.com/auth/realms/redhat-external",
        access_token=access_token,
    )
    with rhoas_service_accounts_mgmt_sdk.ApiClient(configuration=configuration) as api_client:
        yield api_client


@pytest.fixture(scope="session")
def service_accounts_api_instance(service_accounts_mgmt_client):
    return service_accounts_api.ServiceAccountsApi(api_client=service_accounts_mgmt_client)


@pytest.fixture(scope="session")
def service_registry_mgmt_client(ocm_base_api_url, access_token):
    # https://github.com/redhat-developer/app-services-sdk-python/tree/main/sdks/registry_mgmt_sdk
    configuration = rhoas_service_registry_mgmt_sdk.Configuration(
        host=ocm_base_api_url,
        access_token=access_token,
        discard_unknown_keys=True,
    )
    with rhoas_service_registry_mgmt_sdk.ApiClient(configuration=configuration) as api_client:
        yield api_client


@pytest.fixture(scope="session")
def service_registry_mgmt_registries_api_instance(service_registry_mgmt_client):
    return registries_api.RegistriesApi(api_client=service_registry_mgmt_client)
