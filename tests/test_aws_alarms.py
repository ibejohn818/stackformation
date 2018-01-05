import pytest
from stackformation import Infra
from stackformation.aws.stacks import ( alarms, iam, vpc, eip,
                                        ebs, sns, ec2 )



@pytest.fixture
def infra():

    infra = Infra("test")

    prod_infra = infra.create_sub_infra("prod")

    iam_stack = prod_infra.add_stack(iam.IAMStack("roles"))

    web_profile = iam_stack.add_role(iam.EC2AdminProfile("test"))

    vpc_stack = prod_infra.add_stack(vpc.VPCStack())

    eip_stack = prod_infra.add_stack(eip.EIPStack("test"))

    ebs_stack = prod_infra.add_stack(ebs.EBSStack("test", vpc_stack))

    sns_stack = prod_infra.add_stack(sns.SNSTopicStack('test'))

    return {
            'infra': infra,
            'prod_infra': prod_infra,
            'iam_stack': iam_stack,
            'web_profile': web_profile,
            'vpc_stack' : vpc_stack,
            'eip_stack': eip_stack,
            'ebs_stack': ebs_stack,
            'sns_stack': sns_stack
            }

def test_ec2_high_cpu(infra):

    ec2_pro = infra['iam_stack'].add_role(iam.EC2Profile('test'))

    ec2_stack = infra['prod_infra'].add_stack(ec2.EC2Stack('test', infra['vpc_stack'], ec2_pro))

    alarm = infra['prod_infra'].add_stack(alarms.AlarmStack('test'))

    alarm.add_alarm(alarms.EC2HighCpuAlarm(ec2_stack))


    t = alarm.build_template()


def test_ec2_instance_fail(infra):

    ec2_pro = infra['iam_stack'].add_role(iam.EC2Profile('test'))

    ec2_stack = infra['prod_infra'].add_stack(ec2.EC2Stack('test', infra['vpc_stack'], ec2_pro))

    alarm = infra['prod_infra'].add_stack(alarms.AlarmStack('test'))

    alarm.add_alarm(alarms.EC2InstanceFailAlarm(ec2_stack))

    t = alarm.build_template()
