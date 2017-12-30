import pytest
from stackformation.aws.stacks import logs, vpc
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

def test_logs(test_infra):

    infra = test_infra['infra']
    vpc_stack = test_infra['vpc_stack']
    test_infra = test_infra['test_infra']

    log_stack = test_infra.add_stack(logs.LogStack('test'))

    test_logs = log_stack.add_group(logs.LogGroup('test'))

    find_test = log_stack.find_group('test')

    assert find_test.name == 'test'

    find_none = log_stack.find_group('none')

    assert find_none is None

    assert test_logs.output_log_group() == 'TestTestTestLogstestLogGroup'

    t = log_stack.build_template()
