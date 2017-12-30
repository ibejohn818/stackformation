import pytest
from stackformation.aws.stacks import sns, vpc
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

def test_sns(test_infra):

    infra = test_infra['infra']
    vpc_stack = test_infra['vpc_stack']
    test_infra = test_infra['test_infra']

    sns_stack = infra.add_stack(sns.SNSTopicStack('test'))

    slack = sns_stack.add_subscription(sns.SlackSubscription('test'))

    t = sns_stack.build_template()
