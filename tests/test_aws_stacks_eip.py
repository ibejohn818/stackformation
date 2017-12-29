import pytest
import stackformation
from stackformation.aws.stacks import eip




@pytest.fixture
def test_infra():

    infra = stackformation.Infra('test')
    test_infra = infra.create_sub_infra('test')


    return {
            'infra': infra,
            'test_infra': test_infra
        }

def test_eip_stack(test_infra):

    eip_stack = test_infra['test_infra'].add_stack(eip.EIPStack('test'))

    web_ip = eip_stack.add_ip('Web')

    assert isinstance(web_ip, (eip.EIP))

    find_ip = eip_stack.find_ip('Web')

    assert find_ip.name == 'Web'

    none_ip = eip_stack.find_ip('none')

    assert none_ip is None

    t = eip_stack.build_template()
