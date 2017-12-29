import pytest
import stackformation
from stackformation.aws import user_data
from stackformation.aws.stacks import (ec2)
from stackformation import utils


@pytest.fixture
def test_infra():

    infra = stackformation.Infra("test")
    test_infra = infra.create_sub_infra("test")
    ec2_stack = test_infra.add_stack(ec2.EC2Stack('test'))
    env = utils.jinja_env(test_infra.context, True)

    return {
            'infra': infra,
            'test_infra': test_infra,
            'ec2_stack': ec2_stack,
            'env': env
            }
