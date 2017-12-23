import stackformation
from stackformation import (
        DeployStacks
)
from stackformation.aws.eip import EipStack
from stackformation.aws.ec2 import EC2Stack
from stackformation.aws.elb import ELBStack
from stackformation.aws.vpc import VPCStack
from stackformation.aws.s3 import S3Stack
from stackformation.aws.iam import IAMStack
import stackformation.aws.s3 as s3
import stackformation.aws.iam as iam

def common_stacks(infra):

    vpc = infra.add_stack(VPCStack(num_azs=3))

    iam_stack = infra.add_stack(iam.IAMStack())

    web_profile = iam.EC2AdminProfile("WebAdmin")

    iam_stack.add_role(web_profile)

def prod_stacks():

    prod_infra = infra.create_sub_infra("prod")

    common_stacks(prod_infra)

    vpc = prod_infra.find_stack(VPCStack)

    vpc.base_cidr = "10.10"

    s3_stack = prod_infra.add_stack(S3Stack("JchBuckets"))

    test_bucket = s3_stack.add_bucket(s3.S3Bucket("JchTesterBucket"))
    test_bucket.public_read = True

    iam_stack = prod_infra.find_stack(iam.IAMStack)

    web_profile = iam_stack.find_role(iam.EC2AdminProfile)

    print(web_profile)

    return prod_infra

def dev_stacks():

    dev_infra = infra.create_sub_infra("dev")

    dev_infra.add_vars({
        'InputWebEC2TagName': "WebServer"
    })

    common_stacks(dev_infra)

    return dev_infra


session = stackformation.BotoSession(region_name='us-east-2')

infra = stackformation.Infra("Jch", session)

prod_infra = prod_stacks()
dev_infra =  dev_stacks()

stacks = infra.get_stacks()

deploy = DeployStacks()

deploy.deploy_stacks(infra)

# print(prod_infra.context.vars)

# for stack in stacks:
    # print(stack.get_stack_name())
    # print(stack.get_parameters())
    # print(stack.get_outputs())

s3 = session.client('s3')
cf = session.client('cloudformation')

# print(cf.describe_stacks())

# print(s3)
# print(s3.list_buckets())

