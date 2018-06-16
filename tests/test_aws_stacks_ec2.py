import pytest

from stackformation.aws.stacks import (vpc, ec2, iam, eip, ebs)
from stackformation.aws import user_data
from stackformation import Infra
from stackformation import utils


@pytest.fixture
def infra():

    infra = Infra("test")

    prod_infra = infra.create_sub_infra("prod")

    iam_stack = prod_infra.add_stack(iam.IAMStack("roles"))

    web_profile = iam_stack.add_role(iam.EC2AdminProfile("test"))

    vpc_stack = prod_infra.add_stack(vpc.VPCStack())

    eip_stack = prod_infra.add_stack(eip.EIPStack("test"))

    ebs_stack = prod_infra.add_stack(ebs.EBSStack("test", vpc_stack))

    return (infra, prod_infra, iam_stack, web_profile, vpc_stack, eip_stack, ebs_stack)


def test_ec2_stack(infra):

    ebs_stack   = infra[6]
    eip_stack   = infra[5]
    vpc_stack   = infra[4]
    web_profile = infra[3]
    iam_stack   = infra[2]
    prod_infra  = infra[1]
    infra       = infra[0]


    ec2_stack = prod_infra.add_stack(ec2.EC2Stack("Web", vpc_stack, web_profile))

    web_vol = ebs_stack.add_volume(ebs.EBSVolume("Web", 100))

    ec2_stack.add_volume(web_vol)

    ssh_sg = vpc_stack.add_security_group(vpc.SSHSecurityGroup("SSH"))

    ec2_stack.add_security_group(ssh_sg)

    ec2_stack.keypair("testkey")

    ec2_stack.ami = "ami-id"

    t = ec2_stack.build_template()

    inst = t.resources['WebEC2Instance'].to_dict()

    assert ec2_stack.output_instance() == "ProdTestWebEC2WebEC2Instance"

    assert inst['Properties']['KeyName'] == 'testkey'

    assert inst['Properties']['NetworkInterfaces'][0]['SubnetId'] == {'Ref': 'ProdTestVPCPublicSubnet0'}

    assert inst['Properties']['NetworkInterfaces'][0]['GroupSet'][0] == {'Ref': 'ProdTestVPCSSHSecurityGroup'}

    ec2_stack.private_subnet = True

    t = ec2_stack.build_template()

    inst = t.resources['WebEC2Instance'].to_dict()

    assert inst['Properties']['NetworkInterfaces'][0]['SubnetId'] == {'Ref': 'ProdTestVPCPrivateSubnet1'}

    web_eip = eip_stack.add_ip("WebEip")

    ec2_stack.add_user_data(user_data.EIPInfo(web_eip))

    env = utils.jinja_env(prod_infra.context, True)

    res = ec2_stack.render_template_components(env[0], prod_infra.context)

    assert env[1][0] == 'ProdTestTestEIPWebEipEIP'
    assert env[1][1] == 'ProdTestTestEIPWebEipAllocationId'

    params = ec2_stack.get_parameters()
    ec2_stack.before_deploy(prod_infra.context, params)

    assert prod_infra.get_var("WebUserData0") == res['WebUserData'][0]
