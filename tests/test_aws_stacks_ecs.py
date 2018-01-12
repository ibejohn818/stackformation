import pytest
from stackformation.aws.stacks import ecs, vpc
from stackformation import Infra


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


def test_ecs_stack(test_infra):

    infra = test_infra['infra']
    vpc_stack = test_infra['vpc_stack']
    test_infra = test_infra['test_infra']

    ecs_stack = test_infra.add_stack(ecs.ECSStack("test"))

    cluster = ecs_stack.add_cluster('test')

    t = ecs_stack.build_template()

    t_dict = t.resources['testECSCluster'].to_dict()

    assert t_dict['Properties']['ClusterName'] == 'test'
    assert t_dict['Type'] == 'AWS::ECS::Cluster'
    assert cluster.output_cluster()  == 'TestTestTestECStestECSCluster'
    assert cluster.output_cluster_arn()  == 'TestTestTestECStestECSClusterArn'

