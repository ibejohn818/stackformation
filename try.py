import stackformation.base
import stackformation.aws.vpc
from stackformation.base import (
        DeployStacks
)
from stackformation.aws.eip import EipStack

session = stackformation.base.BotoSession(region_name='us-west-2')

infra = stackformation.base.Infra("Jch", session)

prod_infra = infra.create_sub_infra("prod")

vpc = prod_infra.add_stack(stackformation.aws.vpc.VpcStack())
eip = prod_infra.add_stack(EipStack("IPS"))

eip.add_ip("JchCom")
eip.add_ip("AdminJchCom")
eip.add_ip("JenkinJchCom")


print(infra)
print(prod_infra.__dict__)
print(vpc.get_stack_name())


DeployStacks.deploy_stacks(infra)


s3 = session.client('s3')

print(s3)
print(s3.list_buckets())

