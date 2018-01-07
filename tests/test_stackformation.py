from stackformation import (Infra, BotoSession, Context)
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
