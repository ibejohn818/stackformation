import pytest
from stackformation.aws.stacks import (ebs, vpc)
import stackformation

@pytest.fixture
def test_infra():

    infra = stackformation.Infra('test')

    test_infra = infra.create_sub_infra('test')

    vpc_stack = test_infra.add_stack(vpc.VPCStack())

    return (infra, test_infra, vpc_stack)



def test_ebs_stack(test_infra):

    infra = test_infra[0]
    vpc_stack = test_infra[2]
    test_infra = test_infra[1]

    ebs_stack = test_infra.add_stack(ebs.EBSStack('vols', vpc_stack))

    test_vol = ebs_stack.add_volume(ebs.EBSVolume('testvol', 100))

    find_vol = ebs_stack.find_volume('testvol')
    none_vol = ebs_stack.find_volume('no_vol')

    assert find_vol.name == 'testvol'
    assert none_vol is None

    t = ebs_stack.build_template()
