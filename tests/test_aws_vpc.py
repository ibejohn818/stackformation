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
