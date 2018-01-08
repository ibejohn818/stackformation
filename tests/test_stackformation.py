from stackformation import (Infra, BotoSession, Context)
from stackformation.aws.stacks import (vpc, ec2, s3)
import mock
import pytest

@mock.patch("stackformation.boto3.session.Session")
def test_boto_session(mock_sess):

    mock_sess.return_value=True

    session = BotoSession()

    assert session.get_conf("region_name") == 'us-west-2'

    session = BotoSession(
                region_name='test-region',
                profile_name='test-profile',
                aws_secret_access_key='test-secret',
                aws_access_key_id='test-access',
                aws_session_token='test-token',
                botocore_session='test-session'
            )
    assert session.get_conf('region_name') == 'test-region'
    assert session.get_conf('profile_name') == 'test-profile'
    assert session.get_conf('aws_secret_access_key') == 'test-secret'
    assert session.get_conf('aws_access_key_id') == 'test-access'
    assert session.get_conf('aws_session_token') == 'test-token'
    assert session.get_conf('botocore_session') == 'test-session'


    with pytest.raises(Exception) as e:
        session.get_conf('nothere')
    assert 'Conf Error: nothere' in str(e)

def test_context():

    ctx = Context()

    ctx.add_vars({
        'test': 'test',
        'test1': 'test1'
    })

    assert ctx.check_var('test') is not None
    assert ctx.check_var('nothere') is None
    assert ctx.get_var('test') == 'test'
    assert ctx.get_var('nothere') is False


@mock.patch("stackformation.boto3.session.Session")
def test_infra(sess_mock):

    sess_mock.return_value = True

    session = BotoSession()

    infra = Infra('Test', session)

    vpc_stack = infra.add_stack(vpc.VPCStack())
    s3_one = infra.add_stack(s3.S3Stack('one'))
    s3_two = infra.add_stack(s3.S3Stack('two'))

    # test find stack
    vpc_find = infra.find_stack(vpc.VPCStack)

    assert isinstance(vpc_find, (vpc.VPCStack))

    assert infra.find_stack(s3.S3Stack, 'one').stack_name == 'one'
    assert infra.find_stack(s3.S3Stack, 'two').stack_name == 'two'


    # test list_stacks
    assert len(infra.list_stacks()) == 3

    # test sub
    sub = infra.create_sub_infra('sub')
    sub_sub = sub.create_sub_infra('sub')

    assert sub_sub.prefix == ['sub', 'sub']
