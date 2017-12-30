import pytest
from stackformation.aws.stacks import elb, vpc
from stackformation import Infra
from stackformation import utils


@pytest.fixture
def test_infra():

    infra = Infra('test')
    test_infra = infra.create_sub_infra('test')
    vpc_stack = test_infra.add_stack(vpc.VPCStack())

    return {
            'infra': infra,
            'test_infra': test_infra,
            'vpc_stack': vpc_stack
            }

def test_elb(test_infra):

    infra = test_infra['infra']
    vpc_stack = test_infra['vpc_stack']
    test_infra = test_infra['test_infra']

    elb_stack = test_infra.add_stack(elb.ELBStack('test', vpc_stack))

    t = elb_stack.build_template()

