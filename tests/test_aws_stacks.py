import pytest
from stackformation import (Infra, BotoSession)
from stackformation.aws.stacks import (BaseStack, SoloStack)
from stackformation.aws.stacks import (vpc, ec2, iam)


@pytest.fixture
def test_infra():

    session = BotoSession()
    infra = Infra('test', session)
    sub_infra = infra.create_sub_infra('sub')
    vpc_stack = sub_infra.add_stack(vpc.VPCStack())
    iam_stack = sub_infra.add_stack(iam.IAMStack('test'))

    return {
            'infra': infra,
            'sub_infra': sub_infra,
            'vpc_stack': vpc_stack,
            'iam_stack': iam_stack
            }


def test_solo_stack(test_infra):

    infra = test_infra['infra']
    sub_infra = test_infra['sub_infra']
    vpc_stack = test_infra['vpc_stack']
    iam_stack = test_infra['iam_stack']

    # ec2 role
    ec2_role = iam_stack.add_role(iam.EC2AdminProfile('test'))

    # create multiple ec2 stacks
    # doesn't extend solostack so should be ok
    ec2_one = sub_infra.add_stack(ec2.EC2Stack('one', vpc, ec2_role))
    ec2_two = sub_infra.add_stack(ec2.EC2Stack('two', vpc, ec2_role))

    # attemping to add another VPC will throw exception
    with pytest.raises(Exception) as e:
        sub_infra.add_stack(vpc.VPCStack('another'))

    assert 'Solo Stack Error' in str(e)


def test_add_input_spec(test_infra):

    infra = test_infra['infra']
    sub_infra = test_infra['sub_infra']
    vpc_stack = test_infra['vpc_stack']
    iam_stack = test_infra['iam_stack']

    vpc_stack.add_input_spec('blank1')

    assert 'blank1' in vpc_stack._input_spec
    assert vpc_stack._input_spec['blank1']['kms'] is False
    assert vpc_stack._input_spec['blank1']['default'] is None

    vpc_stack.add_input_spec('test1', kms=True, default='default1')

    assert 'test1' in vpc_stack._input_spec
    assert vpc_stack._input_spec['test1']['kms'] is True
    assert vpc_stack._input_spec['test1']['default'] == 'default1'

    with pytest.raises(Exception) as e:
        vpc_stack.add_input_spec()

    assert 'TypeError' in str(e)


def test_add_input_specs(test_infra):

    infra = test_infra['infra']
    sub_infra = test_infra['sub_infra']
    vpc_stack = test_infra['vpc_stack']
    iam_stack = test_infra['iam_stack']

    pass
