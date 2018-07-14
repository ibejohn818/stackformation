from stackformation import (Infra, BotoSession)
from stackformation.aws.stacks import (codedeploy, vpc, elb, iam)
import pytest


@pytest.fixture
def test_infra():

    infra = Infra('test')
    test_infra = infra.create_sub_infra('test')
    vpc_stack = test_infra.add_stack(vpc.VPCStack())
    iam_stack = test_infra.add_stack(iam.IAMStack())

    return {
            'infra': infra,
            'test_infra': test_infra,
            'vpc_stack': vpc_stack,
            'iam_stack': iam_stack,
            }


def test_app(test_infra):

    infra = test_infra['infra']
    vpc_stack = test_infra['vpc_stack']
    iam_stack = test_infra['iam_stack']
    test_infra = test_infra['test_infra']

    cd_role = iam_stack.add_role(iam.CodeDeployRole('test'))
    cd_stack = test_infra.add_stack(codedeploy.CodeDeployStack('test'))
