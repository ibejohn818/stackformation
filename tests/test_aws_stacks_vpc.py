import pytest

from stackformation.aws.stacks import (vpc, eip)
from stackformation import Infra
import troposphere


@pytest.fixture
def prod_infra():

    infra = Infra("test")

    prod_infra = infra.create_sub_infra("prod")

    return (infra, prod_infra)

def test_vpc_stack(prod_infra):

    infra = prod_infra[0]
    prod_infra = prod_infra[1]

    vpc_stack = prod_infra.add_stack(vpc.VPCStack())

    assert isinstance(vpc_stack, vpc.VPCStack)

    t = vpc_stack.build_template()

    assert len(vpc_stack.output_azs()) == 2
    assert len(vpc_stack.output_private_subnets()) == 2
    assert len(vpc_stack.output_public_subnets()) == 2
    assert vpc_stack.output_vpc() == "ProdTestVPCVpcId"
    assert vpc_stack.output_public_routetable() == "ProdTestVPCPublicRouteTable"
    assert vpc_stack.output_private_routetable() == "ProdTestVPCPrivateRouteTable"
    assert vpc_stack.output_default_acl_table() == "ProdTestVPCDefaultAclTable"

def test_base_sec_group(prod_infra):

    infra = prod_infra[0]
    prod_infra = prod_infra[1]

    vpc_stack = prod_infra.add_stack(vpc.VPCStack())
    vpc_stack.num_azs = 3

    base_sg = vpc_stack.add_security_group(vpc.SecurityGroup('base'))

    with pytest.raises(Exception) as e:
        vpc_stack.build_template()
    assert "Must implement" in str(e)


def test_find_sec_group(prod_infra):

    infra = prod_infra[0]
    prod_infra = prod_infra[1]

    vpc_stack = prod_infra.add_stack(vpc.VPCStack())
    vpc_stack.num_azs = 3

    ssh_sg = vpc_stack.add_security_group(vpc.SSHSecurityGroup("SSH"))
    web_sg = vpc_stack.add_security_group(vpc.WebSecurityGroup("Web"))

    find_ssh = vpc_stack.find_security_group(vpc.SSHSecurityGroup)
    find_web = vpc_stack.find_security_group(vpc.WebSecurityGroup)

    assert isinstance(find_ssh, vpc.SSHSecurityGroup)
    assert isinstance(find_web, vpc.WebSecurityGroup)

def test_add_sec_group(prod_infra):

    infra = prod_infra[0]
    prod_infra = prod_infra[1]

    vpc_stack = prod_infra.add_stack(vpc.VPCStack())
    vpc_stack.num_azs = 3


    with pytest.raises(Exception) as e:
        vpc_stack.add_security_group(infra)


def test_ssh_sec_group(prod_infra):

    infra = prod_infra[0]
    prod_infra = prod_infra[1]

    vpc_stack = prod_infra.add_stack(vpc.VPCStack())
    vpc_stack.num_azs = 3

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

    assert ssh_sg.output_security_group() == "ProdTestVPCSSHSecurityGroup"


def test_web_sec_group(prod_infra):

    infra = prod_infra[0]
    prod_infra = prod_infra[1]

    vpc_stack = prod_infra.add_stack(vpc.VPCStack())
    vpc_stack.num_azs = 3

    web_sg = vpc_stack.add_security_group(vpc.WebSecurityGroup("Web"))

    t = vpc_stack.build_template()

    sg = t.resources['WebSecurityGroup'].to_dict()

    assert sg['Properties']['SecurityGroupIngress'][0]['ToPort'] == 80
    assert sg['Properties']['SecurityGroupIngress'][0]['FromPort'] == 80
    assert sg['Properties']['SecurityGroupIngress'][0]['CidrIp'] == '0.0.0.0/0'
    assert sg['Properties']['SecurityGroupIngress'][1]['ToPort'] == 443
    assert sg['Properties']['SecurityGroupIngress'][1]['FromPort'] ==  443
    assert sg['Properties']['SecurityGroupIngress'][1]['CidrIp'] == '0.0.0.0/0'

    assert web_sg.output_security_group() == "ProdTestVPCWebSecurityGroup"

def test_all_ports_sec_group(prod_infra):

    infra = prod_infra[0]
    prod_infra = prod_infra[1]

    vpc_stack = prod_infra.add_stack(vpc.VPCStack())
    vpc_stack.num_azs = 3


    ap_sg = vpc_stack.add_security_group(vpc.AllPortsSecurityGroup("Test"))

    t = vpc_stack.build_template()

    sg = t.resources['TestAllPortsSecurityGroup'].to_dict()

    assert sg['Properties']['SecurityGroupIngress'][0]['ToPort'] == '-1'
    assert sg['Properties']['SecurityGroupIngress'][0]['FromPort'] == '-1'
    assert sg['Properties']['SecurityGroupIngress'][0]['CidrIp'] == '0.0.0.0/0'

def test_nat_gateway(prod_infra):

    infra = prod_infra[0]
    prod_infra = prod_infra[1]

    vpc_stack = prod_infra.add_stack(vpc.VPCStack())
    vpc_stack.num_azs = 3

    eip_stack = prod_infra.add_stack(eip.EIPStack())
    nat_eip = eip_stack.add_ip("NatEip")

    # test eip introspection
    with pytest.raises(Exception) as e:
        vpc_stack.add_nat_gateway(eip_stack)
    assert "EIP Instance" in str(e)

    # try with real EIP
    vpc_stack.add_nat_gateway(nat_eip)

    t = vpc_stack.build_template()

    res = t.resources

    assert isinstance(res['NatGateway'], (troposphere.ec2.NatGateway))
    print(res['NatGatewayRoute'].to_dict())


