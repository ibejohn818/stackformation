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


def test_elb_stack(test_infra):

    infra = test_infra['infra']
    vpc_stack = test_infra['vpc_stack']
    test_infra = test_infra['test_infra']

    test_infra.add_vars({
        'InputtestHealthURI': '/testme'
    })

    sf_sg = vpc_stack.add_security_group(vpc.SelfReferenceSecurityGroup())

    elb_stack = test_infra.add_stack(elb.ELBStack('test', vpc_stack))

    elb_stack.add_security_group(sf_sg)

    t = elb_stack.build_template()

    tdict = t.resources['testELB'].to_dict()



def test_is_public(test_infra):

    infra = test_infra['infra']
    vpc_stack = test_infra['vpc_stack']
    test_infra = test_infra['test_infra']

    lb = test_infra.add_stack(elb.ELBStack('test', vpc_stack))

    assert lb.get_scheme() == "internet-facing"

    lb.is_public = False

    assert lb.get_scheme() == "internal"


