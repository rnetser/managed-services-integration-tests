# Sanity tests to work with https://github.com/redhat-developer/app-services-sdk-python APIs

import logging

import pytest
import rhoas_connector_mgmt_sdk
import rhoas_kafka_instance_sdk
import rhoas_service_accounts_mgmt_sdk
import rhoas_service_registry_mgmt_sdk
import rhoas_smart_events_mgmt_sdk
from rhoas_smart_events_mgmt_sdk.model.managed_resource_status import (
    ManagedResourceStatus,
)


LOGGER = logging.getLogger(__name__)
DEFAULT_PAGE_INDEX = "1"
DEFAULT_NUM_ITEMS = "50"
DEFAULT_ORDER_BY_STR = "name asc"


@pytest.mark.smoke
@pytest.mark.skip_data_collector
def test_list_kafka_instances(kafka_mgmt_api_instance):
    try:
        assert kafka_mgmt_api_instance.get_kafkas(
            page=DEFAULT_PAGE_INDEX,
            size=DEFAULT_NUM_ITEMS,
            order_by=DEFAULT_ORDER_BY_STR,
            search="cloud_provider = aws",
        ), "Failed to get a list of kafka instances"
    except rhoas_kafka_instance_sdk.ApiException:
        LOGGER.error("Api exception when trying to get a list of kafka instances.")
        raise


@pytest.mark.skip_data_collector
def test_list_connector_mgmt_connectors(connector_mgmt_connectors_api_instance):
    try:
        assert connector_mgmt_connectors_api_instance.list_connectors(
            page=DEFAULT_PAGE_INDEX,
            size=DEFAULT_NUM_ITEMS,
            order_by=DEFAULT_ORDER_BY_STR,
            search="name = aws-sqs-source and channel = stable",
        ), "Failed to get a list of connectors"
    except rhoas_connector_mgmt_sdk.ApiException:
        LOGGER.error("Api exception when trying to get connector cluster.")
        raise


@pytest.mark.skip_data_collector
def test_smart_events_mgmt_bridges_api_get_bridges(
    smart_events_mgmt_bridge_api_instance,
):
    try:
        assert smart_events_mgmt_bridge_api_instance.bridges_api_get_bridges(
            page=0,
            size=50,
            status=[
                ManagedResourceStatus("accepted"),
            ],
        ), "Failed to get a list of smart events bridges"
    except rhoas_smart_events_mgmt_sdk.ApiException:
        LOGGER.error("Api exception when trying to get a list of bridges.")
        raise


@pytest.mark.skip_data_collector
def test_service_accounts_get_service_accounts(service_accounts_api_instance):
    try:
        service_accounts_api_instance.get_service_accounts(first=0, max=20)
    except rhoas_service_accounts_mgmt_sdk.ApiException:
        LOGGER.error("Api exception when trying to get a list of service accounts.")
        raise


@pytest.mark.skip_data_collector
def test_service_registry_mgmt_get_registries(
    service_registry_mgmt_registries_api_instance,
):
    try:
        assert service_registry_mgmt_registries_api_instance.get_registries(
            page=1, size=25, search="status = AVAILABLE"
        ), "Failed to get a list of registries"
    except rhoas_service_registry_mgmt_sdk.ApiException:
        LOGGER.error("Api exception when trying to get a list registries.")
        raise
