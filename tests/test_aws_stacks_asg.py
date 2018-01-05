import pytest

from stackformation.aws.stacks import (vpc, ec2, iam,
                                        eip, ebs, asg,
                                        elb)
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

    elb_stack = prod_infra.add_stack(elb.ELBStack('test', vpc_stack))

    return {
            'infra': infra,
            'prod_infra': prod_infra,
            'iam_stack': iam_stack,
            'vpc_stack': vpc_stack,
            'eip_stack': eip_stack,
            'ebs_stack': ebs_stack,
            'elb_stack': elb_stack
            }


def test_ec2_stack(infra):

    ec2_profile = infra['iam_stack'].find_role(iam.EC2AdminProfile)
    sf_sg = infra['vpc_stack'].add_security_group(vpc.SelfReferenceSecurityGroup())

    asg_stack = infra['prod_infra'].add_stack(asg.ASGStack('test', infra['vpc_stack'], ec2_profile))
    asg_stack.add_elb(infra['elb_stack'])
    asg_stack.ami = "ami-test"

    template = asg_stack.build_template()


