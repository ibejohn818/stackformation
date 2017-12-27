import pytest

from stackformation.aws import (vpc)
from stackformation import Infra


@pytest.fixture
def prod_infra():

    infra = Infra("test")

    prod_infra = infra.create_sub_infra("prod")

    return (infra, prod_infra)

def test_vpc(prod_infra):

    infra = prod_infra[0]
    prod_infra = prod_infra[1]

    vpc_stack = prod_infra.add_stack(vpc.VPCStack(num_azs=3))

    assert isinstance(vpc_stack, vpc.VPCStack)

    t = vpc_stack.build_template()

    assert len(vpc_stack.output_azs()) == 3
    assert len(vpc_stack.output_private_subnets()) == 3
    assert len(vpc_stack.output_public_subnets()) == 3
    assert vpc_stack.output_vpc() == "ProdTestVpcVpcId"
    assert vpc_stack.output_public_routetable() == "ProdTestVpcPublicRouteTable"
    assert vpc_stack.output_private_routetable() == "ProdTestVpcPrivateRouteTable"
    assert vpc_stack.output_default_acl_table() == "ProdTestVpcDefaultAclTable"

def test_base_sec_group(prod_infra):

    infra = prod_infra[0]
    prod_infra = prod_infra[1]

    vpc_stack = prod_infra.add_stack(vpc.VPCStack(num_azs=3))

    base_sg = vpc_stack.add_security_group(vpc.SecurityGroup('base'))

    with pytest.raises(Exception) as e:
        vpc_stack.build_template()
    assert "Must implement" in str(e)


def test_ssh_sec_group(prod_infra):

    infra = prod_infra[0]
    prod_infra = prod_infra[1]

    vpc_stack = prod_infra.add_stack(vpc.VPCStack(num_azs=3))

    ssh_sg = vpc_stack.add_security_group(vpc.SSHSecurityGroup("SSH"))

    t = vpc_stack.build_template()

    assert isinstance(ssh_sg, vpc.SSHSecurityGroup)

    sg_dict = t.resources['SSHSecurityGroup'].to_dict()

    assert sg_dict['Properties']['SecurityGroupIngress'][0]['ToPort'] == 22
    assert sg_dict['Properties']['SecurityGroupIngress'][0]['FromPort'] == 22
    assert sg_dict['Properties']['SecurityGroupIngress'][0]['CidrIp'] == '0.0.0.0/0'

    ssh_sg2 = vpc_stack.add_security_group(vpc.SSHSecurityGroup("SSH2"))
    ssh_sg2.allow_cidr('1.2.3.4/5')

    t = vpc_stack.build_template()

    sg_dict = t.resources['SSH2SecurityGroup'].to_dict()

    assert sg_dict['Properties']['SecurityGroupIngress'][0]['ToPort'] == 22
    assert sg_dict['Properties']['SecurityGroupIngress'][0]['FromPort'] == 22
    assert sg_dict['Properties']['SecurityGroupIngress'][0]['CidrIp'] == '1.2.3.4/5'

    assert ssh_sg.output_security_group() == "ProdTestVpcSSHSecurityGroup"


def test_web_sec_group(prod_infra):

    infra = prod_infra[0]
    prod_infra = prod_infra[1]

    vpc_stack = prod_infra.add_stack(vpc.VPCStack(num_azs=3))

    web_sg = vpc_stack.add_security_group(vpc.WebSecurityGroup("Web"))

    t = vpc_stack.build_template()

    sg = t.resources['WebSecurityGroup'].to_dict()

    assert sg['Properties']['SecurityGroupIngress'][0]['ToPort'] == 80
    assert sg['Properties']['SecurityGroupIngress'][0]['FromPort'] == 80
