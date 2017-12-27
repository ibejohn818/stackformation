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

    t = ec2_stack.build_template()

    inst = t.resources['WebEC2Instance'].to_dict()

    assert inst['Properties']['NetworkInterfaces'][0]['SubnetId'] == {'Ref': 'ProdTestVpcPublicSubnet1'}


    ec2_stack.private_subnet = True

    t = ec2_stack.build_template()

    inst = t.resources['WebEC2Instance'].to_dict()

    assert inst['Properties']['NetworkInterfaces'][0]['SubnetId'] == {'Ref': 'ProdTestVpcPrivateSubnet1'}
