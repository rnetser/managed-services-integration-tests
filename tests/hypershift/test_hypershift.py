import logging
import os
import random
import shlex

import pytest
from ocm_python_wrapper.cluster import Cluster
from ocp_utilities.utils import run_command
from python_terraform import IsNotFlagged, Terraform, TerraformCommandError


LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def cluster_parameters():
    params = {
        "aws_region": "us-west-2",
        "cluster_name": f"msi-{random.randint(1000000000, 9999999999) }",
    }
    LOGGER.info(f"Cluster parameters: {params}")
    return params


@pytest.fixture(scope="module")
def terraform(cluster_parameters):
    tf = Terraform(working_dir=os.path.dirname(__file__), variables=cluster_parameters)
    tf.init()
    return tf


@pytest.fixture(scope="module")
def created_vpcs(terraform, ocp_target_version):
    LOGGER.info("Create VPCs")
    try:
        terraform.plan(dir_or_plan="rosa.plan")
        terraform.apply(capture_output=False, skip_plan=True, raise_on_error=True)
        return terraform
    except TerraformCommandError as ex:
        LOGGER.error(f"Failed to apply Terraform plan, {ex}")
        raise


@pytest.fixture(scope="module")
def cluster_subnets(created_vpcs, terraform):
    """Returns cluster subnets tuple (public subnet, private subnet)"""
    terraform_output = terraform.output()
    try:
        private_subnet = terraform_output["cluster-private-subnet"]["value"]
        public_subnet = terraform_output["cluster-public-subnet"]["value"]
        LOGGER.info(
            f"Cluster public subnet: {public_subnet}, private subnet: {private_subnet}"
        )
        return public_subnet, private_subnet
    except KeyError:
        LOGGER.error(
            f"Failed to get cluster subnets, terraform output: {terraform_output}"
        )
        raise


def delete_vpcs(terraform):
    LOGGER.info("Delete VPCs")
    terraform.destroy(force=IsNotFlagged, auto_approve=True, capture_output=False)
    terraform_output = terraform.output()
    assert not terraform_output, f"VPCs are not deleted, {terraform_output}"


def create_hypershift_cluster(cluster_parameters, ocp_target_version, cluster_subnets):
    rosa_create_cluster_cmd = (
        f"rosa create cluster --cluster-name {cluster_parameters['cluster_name']} "
        f"--subnet-ids {','.join(cluster_subnets)} --sts --mode auto "
        "--machine-cidr 10.0.0.0/16 --compute-machine-type m5.xlarge --hosted-cp "
        f"--tags dns:external --region {cluster_parameters['aws_region']} --channel-group candidate "
        f"--version {ocp_target_version} -y"
    )
    cmd_succeeded, cmd_out, cmd_err = run_command(
        command=shlex.split(rosa_create_cluster_cmd)
    )
    # import ipdb
    #
    # ipdb.set_trace()


@pytest.fixture(scope="module")
def hypershift_cluster(ocm_client_scope_session, cluster_parameters):
    return Cluster(
        client=ocm_client_scope_session, name=cluster_parameters["cluster_name"]
    )


def test_hypershift_cluster_installation(
    cluster_parameters,
    ocp_target_version,
    cluster_subnets,
):
    create_hypershift_cluster(
        cluster_parameters=cluster_parameters,
        ocp_target_version=ocp_target_version,
        cluster_subnets=cluster_subnets,
    )


def test_hypershift_cluster_ready(hypershift_cluster):
    hypershift_cluster.wait_for_cluster_ready()


def test_hypershift_cluster_uninstall(hypershift_cluster, terraform):
    hypershift_cluster.delete()
    delete_vpcs(terraform=terraform)
