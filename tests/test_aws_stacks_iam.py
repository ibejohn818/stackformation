import pytest
from stackformation.aws.stacks import iam
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

    t = iam_stack.build_template()
