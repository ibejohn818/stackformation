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

    vpc_stack = prod_infra.add_stack(vpc.VPCStack())

    assert isinstance(vpc_stack, vpc.VPCStack)

    t = vpc_stack.build_template()
