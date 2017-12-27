import pytest

from stackformation.aws import (vpc, ec2, iam)
from stackformation import Infra


@pytest.fixture
def infra():

    infra = Infra("test")

    prod_infra = infra.create_sub_infra("prod")

    iam_stack = prod_infra.add_stack(iam.IAMStack("roles"))

    web_profile = iam_stack.add_role(iam.EC2AdminProfile("test"))

    vpc_stack = prod_infra.add_stack(vpc.VPCStack())

    return (infra, prod_infra, iam_stack, web_profile, vpc_stack)


def test_ec2_stack(infra):

    vpc_stack   = infra[4]
    web_profile = infra[3]
    iam_stack   = infra[2]
    prod_infra  = infra[1]
    infra       = infra[0]


    ec2_stack = prod_infra.add_stack(ec2.EC2Stack("Web", vpc_stack, web_profile))

    ssh_sg = vpc_stack.add_security_group(vpc.SSHSecurityGroup("SSH"))

    ec2_stack.add_security_group(ssh_sg)

    ec2_stack.keypair("testkey")

    t = ec2_stack.build_template()

    inst = t.resources['WebEC2Instance'].to_dict()

    assert ec2_stack.output_instance() == "ProdTestWebEC2WebEC2Instance"

    assert inst['Properties']['KeyName'] == 'testkey'

    assert inst['Properties']['NetworkInterfaces'][0]['SubnetId'] == {'Ref': 'ProdTestVPCPublicSubnet1'}

    assert inst['Properties']['NetworkInterfaces'][0]['GroupSet'][0] == {'Ref': 'ProdTestVPCSSHSecurityGroup'}

    ec2_stack.private_subnet = True

    t = ec2_stack.build_template()

    inst = t.resources['WebEC2Instance'].to_dict()

    assert inst['Properties']['NetworkInterfaces'][0]['SubnetId'] == {'Ref': 'ProdTestVPCPrivateSubnet1'}
