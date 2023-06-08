import os
import re
import shutil

import boto3
import pytest
import rosa.cli
import shortuuid
from clouds.aws.aws_utils import verify_aws_credentials
from ocm_python_wrapper.cluster import Cluster
from ocm_python_wrapper.exceptions import MissingResourceError
from ocp_resources.utils import TimeoutExpiredError, TimeoutSampler
from ocp_utilities.operators import install_operator, uninstall_operator
from packaging import version
from pytest_testconfig import py_config
from python_terraform import IsNotFlagged, Terraform, TerraformCommandError
from simple_logger.logger import get_logger


LOGGER = get_logger(name=__name__)


pytestmark = pytest.mark.hypershift_install


class RegionNotFoundError(Exception):
    pass


def create_vpcs(terraform):
    LOGGER.info("Create VPCs")
    try:
        terraform.plan(dir_or_plan="rosa.plan")
        terraform.apply(capture_output=False, skip_plan=True, raise_on_error=True)
    except TerraformCommandError as ex:
        LOGGER.error(f"Failed to apply Terraform plan, {ex}")
        # Clean up already created resources from the plan
        destroy_vpcs(terraform=terraform)
        raise


def destroy_vpcs(terraform):
    try:
        LOGGER.info("Destroy VPCs")
        terraform.destroy(
            force=IsNotFlagged,
            auto_approve=True,
            capture_output=False,
            raise_on_error=True,
        )
    except TerraformCommandError as ex:
        LOGGER.error(f"Failed to destroy VPCs, {ex}")
        raise


def create_hypershift_cluster(
    cluster_parameters,
    ocp_target_version,
    cluster_subnets,
    openshift_channel_group,
    aws_compute_machine_type,
    oidc_config_id,
    rosa_allowed_commands,
):
    rosa_create_cluster_cmd = (
        f"create cluster --cluster-name {cluster_parameters['cluster_name']} "
        f"--subnet-ids {cluster_subnets} --sts --hosted-cp --machine-cidr 10.0.0.0/16 "
        f"--compute-machine-type {aws_compute_machine_type} --replicas {py_config['rosa_number_of_nodes']} "
        f"--tags dns:external --region {cluster_parameters['aws_region']} --channel-group {openshift_channel_group} "
        f"--version {ocp_target_version} --oidc-config-id {oidc_config_id}"
    )
    rosa.cli.execute(
        command=rosa_create_cluster_cmd, allowed_commands=rosa_allowed_commands
    )


@pytest.fixture(scope="session")
def exported_aws_credentials():
    verify_aws_credentials()


@pytest.fixture(scope="session")
def rosa_login(rosa_allowed_commands):
    home_dir = py_config.get("home_dir")
    if home_dir:
        os.environ["HOME"] = home_dir
    api_server = py_config["api_server"]
    env_str = "--env=staging" if api_server == "stage" else ""
    rosa.cli.execute(command=f"login {env_str}", allowed_commands=rosa_allowed_commands)


@pytest.fixture(scope="session")
def rosa_hypershift_regions(rosa_regions):
    hypershift_regions = [
        region["id"] for region in rosa_regions if region["supports_hypershift"] is True
    ]
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
        raise ValueError(
            f"{pyconfig_aws_region} is not supported, supported regions: {rosa_hypershift_regions}"
        )
    # If a region was not passed, use a hypershift-enabled region with the lowest number of used VPCs
    region, vpcs = None, None
    for _region in rosa_hypershift_regions:
        num_vpcs = len(
            boto3.client(service_name="ec2", region_name=_region).describe_vpcs()[
                "Vpcs"
            ]
        )
        if vpcs is None or num_vpcs < vpcs:
            region = _region
            vpcs = num_vpcs
    return region


@pytest.fixture(scope="class")
def az_ids(aws_region):
    # az_id example: us-east-2 -> ["use2-az1", "use2-az2"]
    az_id_prefix = "".join(re.match(r"(.*)-(\w).*-(\d)", aws_region).groups())
    return [f"{az_id_prefix}-az1", f"{az_id_prefix}-az2"]


@pytest.fixture(scope="class")
def cluster_parameters(aws_region, az_ids):
    params = {
        "aws_region": aws_region,
        "az_ids": az_ids,
        "cluster_name": f"msi-{shortuuid.random(11)}".lower(),
    }
    LOGGER.info(f"Cluster parameters: {params}")
    return params


@pytest.fixture(scope="class")
def terraform_workdir(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("terraform_working_dir")
    LOGGER.info(f"Terraform work dir: {tmp_dir}")
    yield tmp_dir


@pytest.fixture(scope="class")
def copied_terraform_vpcs_config_file(terraform_workdir):
    shutil.copy(
        f"{os.path.dirname(__file__)}/manifests/setup-vpc.tf", terraform_workdir
    )


@pytest.fixture(scope="class")
def terraform(terraform_workdir, copied_terraform_vpcs_config_file, cluster_parameters):
    tf = Terraform(working_dir=terraform_workdir, variables=cluster_parameters)
    tf.init()
    return tf


@pytest.fixture(scope="class")
def vpcs(terraform):
    create_vpcs(terraform=terraform)
    yield
    destroy_vpcs(terraform=terraform)


@pytest.fixture(scope="class")
def cluster_subnets(vpcs, terraform):
    """Returns cluster subnets str (public subnet, private subnet). Order is required by ROSA CLI"""
    terraform_output = terraform.output()
    try:
        private_subnet = terraform_output["cluster-private-subnet"]["value"]
        public_subnet = terraform_output["cluster-public-subnet"]["value"]
        LOGGER.info(
            f"Cluster public subnet: {public_subnet}, private subnet: {private_subnet}"
        )
        return f'"{public_subnet},{private_subnet}"'
    except KeyError:
        LOGGER.error(
            f"Failed to get cluster subnets, terraform output: {terraform_output}"
        )
        raise


@pytest.fixture(scope="class")
def cluster_scope_class(ocm_client_scope_session, cluster_parameters):
    cluster_name = cluster_parameters["cluster_name"]
    try:
        for sample in TimeoutSampler(
            wait_timeout=120,
            sleep=5,
            func=Cluster,
            client=ocm_client_scope_session,
            name=cluster_name,
            exceptions_dict={MissingResourceError: []},
        ):
            if sample:
                return sample
    except TimeoutExpiredError:
        LOGGER.error(f"Cluster {cluster_name} not found.")
        raise


@pytest.fixture(scope="class")
def oidc_config_id(cluster_parameters, aws_region, rosa_allowed_commands):
    oidc_prefix = cluster_parameters["cluster_name"]
    LOGGER.info("Create oidc-config")
    rosa.cli.execute(
        command=f"create oidc-config --managed=false --prefix {oidc_prefix} --region {aws_region}",
        allowed_commands=rosa_allowed_commands,
    )
    res = rosa.cli.execute(
        command=f"list oidc-config --region {aws_region}",
        allowed_commands=rosa_allowed_commands,
    )["out"]
    _oidc_config_id = [
        oidc_config["id"]
        for oidc_config in res
        if oidc_prefix in oidc_config["secret_arn"]
    ][0]
    yield _oidc_config_id
    LOGGER.info("Delete oidc-config")
    rosa.cli.execute(
        command=f"delete oidc-config --oidc-config-id {_oidc_config_id} --region {aws_region}",
        allowed_commands=rosa_allowed_commands,
    )


@pytest.fixture(scope="session")
def hypershift_target_version(ocp_target_version, rosa_allowed_commands):
    """Return ocp_target_version if semantic version else return ROSA latest version based on ocp_target_version"""
    # Z-stream or explicit RC
    if len(version.parse(ocp_target_version).release) == 3:
        return ocp_target_version

    rosa_versions = rosa.cli.execute(
        command=f"list versions --channel-group {py_config['openshift_channel_group']}",
        allowed_commands=rosa_allowed_commands,
    )["out"]
    # Excluding "ec" releases
    target_version = max(
        [
            version.parse(ver["raw_id"])
            for ver in rosa_versions
            if ver["raw_id"].startswith(ocp_target_version)
            and "ec" not in ver["raw_id"]
        ]
    ).public
    # version removes the 'rc' hyphen and period from the version, example: '4.13.0rc7' -> '4.13.0-rc.7'
    return target_version.replace("rc", "-rc.")


@pytest.mark.usefixtures("exported_aws_credentials", "rosa_login", "vpcs")
class TestHypershiftCluster:
    OPERATOR_NAME = "servicemeshoperator"

    @pytest.mark.dependency(name="test_hypershift_cluster_installation")
    def test_hypershift_cluster_installation(
        self,
        cluster_parameters,
        hypershift_target_version,
        cluster_subnets,
        oidc_config_id,
        rosa_allowed_commands,
    ):
        LOGGER.info(
            f"Test hypershift cluster install using {hypershift_target_version} OCP version"
        )
        create_hypershift_cluster(
            cluster_parameters=cluster_parameters,
            ocp_target_version=hypershift_target_version,
            cluster_subnets=cluster_subnets,
            openshift_channel_group=py_config["openshift_channel_group"],
            aws_compute_machine_type=py_config["aws_compute_machine_type"],
            oidc_config_id=oidc_config_id,
            rosa_allowed_commands=rosa_allowed_commands,
        )

    @pytest.mark.dependency(
        name="test_hypershift_cluster_ready",
        depends=["test_hypershift_cluster_installation"],
    )
    def test_hypershift_cluster_ready(self, cluster_scope_class):
        cluster_scope_class.wait_for_cluster_ready()

    @pytest.mark.dependency(
        name="test_install_operator", depends=["test_hypershift_cluster_ready"]
    )
    def test_install_operator(self, cluster_scope_class):
        install_operator(
            admin_client=cluster_scope_class.ocp_client,
            name=TestHypershiftCluster.OPERATOR_NAME,
            channel="stable",
            source="redhat-operators",
        )

    @pytest.mark.dependency(depends=["test_install_operator"])
    def test_uninstall_operator(self, cluster_scope_class):
        uninstall_operator(
            admin_client=cluster_scope_class.ocp_client,
            name=TestHypershiftCluster.OPERATOR_NAME,
        )

    @pytest.mark.dependency(depends=["test_hypershift_cluster_installation"])
    def test_hypershift_cluster_uninstall(self, cluster_scope_class):
        cluster_scope_class.delete()
