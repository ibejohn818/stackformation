import pytest
from stackformation.aws.stacks import iam, s3
from stackformation import (Infra)



@pytest.fixture
def test_infra():

    infra = Infra('test')
    test_infra = infra.create_sub_infra('test')

    return {
            'infra': infra,
            'test_infra': test_infra
            }

def test_iam_base(test_infra):

    infra = test_infra['infra']
    test_infra = test_infra['test_infra']

    iam_stack = test_infra.add_stack(iam.IAMStack('test'))

    base = iam.IAMBase('test')

    with pytest.raises(Exception) as e:
        base._build_template(iam_stack._init_template())

    assert "_build_template" in str(e)


def test_iam_user(test_infra):

    infra = test_infra['infra']
    test_infra = test_infra['test_infra']

    iam_stack = test_infra.add_stack(iam.IAMStack('test'))

    user = iam_stack.add_user(iam.IAMUser('test'))

    user.set_login_name("test")

    # test key methods
    user.disable_key()
    assert user._generate_key is False
    user.enable_key()
    assert user._generate_key is True

    # Test console login methods
    user.allow_console_login()
    assert user._allow_console is True
    user.disable_console_login()
    assert user._allow_console is False
    user.allow_console_login()

    assert user.output_user() == 'TestTestTestIAMtestIAMUser'
    assert user.output_access_key() == 'TestTestTestIAMtestIAMAccessKey'
    assert user.output_secret_key() == 'TestTestTestIAMtestIAMSecretKey'


    t = iam_stack.build_template()

    user_dict = t.resources['test'].to_dict()

    assert user_dict['Type'] == 'AWS::IAM::User'


def test_s3_fullaccess(test_infra):

    infra = test_infra['infra']
    test_infra = test_infra['test_infra']

    iam_stack = test_infra.add_stack(iam.IAMStack('test'))
    s3_stack = test_infra.add_stack(s3.S3Stack('test'))

    bucket = s3_stack.add_bucket(s3.S3Bucket('test'))

    user = iam_stack.add_user(iam.IAMUser('test'))

    user.add_policy(iam.S3FullBucketAccess(bucket))

    with pytest.raises(TypeError) as e:
        iam.S3FullBucketAccess({})
    assert "Object" in str(e)
