import boto3
import openshift_cli_installer.cli
import pytest
import shortuuid
from click.testing import CliRunner
from ocm_python_wrapper.cluster import Cluster
from ocp_utilities.operators import install_operator, uninstall_operator
from pytest_testconfig import py_config
from simple_logger.logger import get_logger


LOGGER = get_logger(name=__name__)


pytestmark = pytest.mark.hypershift_install


class RegionNotFoundError(Exception):
    pass


@pytest.fixture(scope="session")
def rosa_hypershift_regions(rosa_regions):
    hypershift_regions = [region["id"] for region in rosa_regions if region["supports_hypershift"] is True]
    if not hypershift_regions:
        LOGGER.error("No Hypershift-supported regions found")
        raise RegionNotFoundError
    LOGGER.info(f"ROSA Hypershift-supported regions: {hypershift_regions}")
    return hypershift_regions


@pytest.fixture(scope="session")
def aws_region(rosa_hypershift_regions):
    pyconfig_aws_region = py_config.get("aws_region")
    if pyconfig_aws_region:
        if pyconfig_aws_region in rosa_hypershift_regions:
            return pyconfig_aws_region
        raise ValueError(f"{pyconfig_aws_region} is not supported, supported regions:" f" {rosa_hypershift_regions}")
    # If a region was not passed, use a hypershift-enabled region with the lowest number of used VPCs
    region, vpcs = None, None
    for _region in rosa_hypershift_regions:
        num_vpcs = len(boto3.client(service_name="ec2", region_name=_region).describe_vpcs()["Vpcs"])
        if vpcs is None or num_vpcs < vpcs:
            region = _region
            vpcs = num_vpcs
    return region


@pytest.fixture(scope="class")
def cluster_name_scope_class():
    return f"msi-{shortuuid.random(11)}".lower()


@pytest.fixture(scope="class")
def cluster_cmd(
    ocm_token,
    ocm_client_scope_session,
    aws_region,
    ocp_target_version,
    cluster_name_scope_class,
):
    return (
        "--clusters-install-data-directory /tmp/clusters-data "
        f"--ocm-token={ocm_token} "
        f"--cluster 'name={cluster_name_scope_class};"
        "platform=hypershift;"
        f"region={aws_region};"
        f"version={ocp_target_version};"
        f"compute-machine-type={py_config['aws_compute_machine_type']};"
        f"replicas={py_config['rosa_number_of_nodes']};"
        f"channel-group={py_config['openshift_channel_group']};"
        "expiration-time=4h;"
        "timeout=1h' "
        f"--ocm-env={py_config['ocm_api_server']} "
        "--s3-bucket-name=openshift-cli-installer "
        "--s3-bucket-path=msi-tests"
    )


@pytest.fixture(scope="class")
def create_cluster_cmd(cluster_cmd):
    return f"--action create {cluster_cmd}"


@pytest.fixture(scope="class")
def destroy_cluster_cmd(cluster_cmd):
    return f"--action destroy {cluster_cmd}"


@pytest.fixture(scope="class")
def click_runner():
    return CliRunner(mix_stderr=False)


@pytest.fixture(scope="class")
def cluster_scope_class(ocm_client_scope_session, cluster_name_scope_class):
    return Cluster(client=ocm_client_scope_session, name=cluster_name_scope_class)


class TestHypershiftCluster:
    OPERATOR_NAME = "serverless-operator"
    OPERATOR_NAMESPACE = "openshift-serverless"

    @pytest.mark.dependency(name="test_hypershift_cluster_installation")
    def test_hypershift_create_cluster(self, create_cluster_cmd, click_runner):
        result = click_runner.invoke(
            cli=openshift_cli_installer.cli.main,
            args=create_cluster_cmd,
            catch_exceptions=False,
        )
        LOGGER.info(result.stdout)

        if result.exit_code != 0:
            pytest.fail(f"Failed to create cluster on {result.stderr}")

    @pytest.mark.dependency(name="test_install_operator", depends=["test_hypershift_cluster_installation"])
    def test_install_operator(self, cluster_scope_class):
        install_operator(
            admin_client=cluster_scope_class.ocp_client,
            name=TestHypershiftCluster.OPERATOR_NAME,
            operator_namespace=TestHypershiftCluster.OPERATOR_NAMESPACE,
            channel="stable",
            source="redhat-operators",
        )

    @pytest.mark.dependency(depends=["test_install_operator"])
    def test_uninstall_operator(self, cluster_scope_class):
        uninstall_operator(
            admin_client=cluster_scope_class.ocp_client,
            name=TestHypershiftCluster.OPERATOR_NAME,
            operator_namespace=TestHypershiftCluster.OPERATOR_NAMESPACE,
        )

    @pytest.mark.dependency(depends=["test_hypershift_cluster_installation"])
    def test_hypershift_destroy_cluster(self, destroy_cluster_cmd, click_runner):
        result = click_runner.invoke(
            cli=openshift_cli_installer.cli.main,
            args=destroy_cluster_cmd,
            catch_exceptions=False,
        )
        LOGGER.info(result.stdout)

        if result.exit_code != 0:
            pytest.fail(f"Failed to destroy cluster. error: {result.stderr}")
