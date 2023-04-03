import logging
import os
import re
import shlex
import shutil

import boto3
import pytest
import shortuuid
from clouds.aws.aws_utils import verify_aws_credentials
from ocm_python_wrapper.cluster import Cluster
from ocm_python_wrapper.exceptions import ClusterInstallError, MissingResourceError
from ocp_resources.utils import TimeoutExpiredError, TimeoutSampler
from ocp_utilities.operators import install_operator, uninstall_operator
from ocp_utilities.utils import run_command
from pytest_testconfig import py_config
from python_terraform import IsNotFlagged, Terraform, TerraformCommandError


LOGGER = logging.getLogger(__name__)
OPERATOR_NAME = "servicemeshoperator"


pytestmark = pytest.mark.hypershift_install


class RosaLoginError(Exception):
    pass


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
):
    rosa_create_cluster_cmd = (
        f"rosa create cluster --cluster-name {cluster_parameters['cluster_name']} "
        f"--subnet-ids {cluster_subnets} --sts --mode auto --hosted-cp --machine-cidr 10.0.0.0/16 "
        f"--compute-machine-type {aws_compute_machine_type} --replicas {py_config['rosa_number_of_nodes']} "
        f"--tags dns:external --region {cluster_parameters['aws_region']} --channel-group {openshift_channel_group} "
        f"--version {ocp_target_version} -y"
    )
    # ROSA output warnings results with command errors, using verify_stderr to ignore fail exit status in these cases.
    cmd_succeeded, cmd_out, cmd_err = run_command(
        command=shlex.split(rosa_create_cluster_cmd), verify_stderr=False
    )

    # ROSA output may contain WARNINGS which can be ignored; failing only if there are errors.
    if "ERR" in cmd_err:
        LOGGER.error(
            f"Failed to install cluster: \noutput: {cmd_out}\nerror: {cmd_err}"
        )
        raise ClusterInstallError


@pytest.fixture(scope="session")
def exported_aws_credentials():
    verify_aws_credentials()


@pytest.fixture(scope="session")
def rosa_login():
    api_server = py_config["api_server"]
    env_str = "--env=staging" if api_server == "stage" else ""
    cmd_succeeded, _, cmd_err = run_command(
        command=shlex.split(f"rosa login {env_str}")
    )
    if not cmd_succeeded:
        LOGGER.error(f"Failed to login to ROSA in {api_server} with error: {cmd_err}")
        raise RosaLoginError


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


@pytest.mark.usefixtures("exported_aws_credentials", "rosa_login", "vpcs")
class TestHypershiftCluster:
    @pytest.mark.dependency(name="test_hypershift_cluster_installation")
    def test_hypershift_cluster_installation(
        self,
        cluster_parameters,
        ocp_target_version,
        cluster_subnets,
    ):
        create_hypershift_cluster(
            cluster_parameters=cluster_parameters,
            ocp_target_version=ocp_target_version,
            cluster_subnets=cluster_subnets,
            openshift_channel_group=py_config["openshift_channel_group"],
            aws_compute_machine_type=py_config["aws_compute_machine_type"],
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
            name=OPERATOR_NAME,
            channel="stable",
            source="redhat-operators",
        )

    @pytest.mark.dependency(depends=["test_install_operator"])
    def test_uninstall_operator(self, cluster_scope_class):
        uninstall_operator(
            admin_client=cluster_scope_class.ocp_client, name=OPERATOR_NAME
        )

    @pytest.mark.dependency(depends=["test_hypershift_cluster_installation"])
    def test_hypershift_cluster_uninstall(self, cluster_scope_class):
        cluster_scope_class.delete()
