import stackformation.base
import stackformation.aws.vpc
from stackformation.base import (
        DeployStacks
)
from stackformation.aws.eip import EipStack
from stackformation.aws.ec2 import EC2Stack
from stackformation.aws.elb import ELBStack

session = stackformation.base.BotoSession(region_name='us-west-2')

infra = stackformation.base.Infra("Jch", session)

prod_infra = infra.create_sub_infra("prod")

svpc = infra.add_stack(stackformation.aws.vpc.VpcStack(num_azs=3))
vpc = prod_infra.add_stack(stackformation.aws.vpc.VpcStack(num_azs=3))
elb = prod_infra.add_stack(ELBStack("Web", vpc))
elbdev = prod_infra.add_stack(ELBStack("WebDev", vpc))
eip = prod_infra.add_stack(EipStack("IPS"))
ec2 = prod_infra.add_stack(EC2Stack("Web", vpc))

eip.add_ip("JchCom")
eip.add_ip("AdminJchCom")
eip.add_ip("JenkinJchCom")




prod_infra.add_input_vars({
    'InputWebEC2TagName': "Web",
    'InputWebEC2InstanceType': "t2.small"
})

stacks = infra.get_stacks()

for stack in stacks:
    print(stack.get_stack_name())
    print(stack.get_template_params())
    print(stack.get_template_outputs())

s3 = session.client('s3')

print(s3)
print(s3.list_buckets())

