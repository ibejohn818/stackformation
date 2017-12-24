import stackformation
from stackformation.deploy import (
        DeployStacks
)
from stackformation.aws import (eip)
from stackformation.aws.ec2 import EC2Stack
from stackformation.aws.elb import ELBStack
from stackformation.aws.vpc import VPCStack
from stackformation.aws.s3 import S3Stack
from stackformation.aws.iam import IAMStack
import stackformation.aws.s3 as s3
from stackformation.aws import iam

def common_stacks(infra):

    vpc = infra.add_stack(VPCStack(num_azs=3))

    iam_stack = infra.add_stack(iam.IAMStack())

    web_profile = iam.EC2AdminProfile("WebAdmin")

    iam_stack.add_role(web_profile)

    s3_stack = infra.add_stack(s3.S3Stack("test"))

    test_bucket = s3_stack.add_bucket(s3.S3Bucket("jchtest"))

    web_profile.add_policy(iam.S3FullBucketAccess(test_bucket))

    eip_stack = infra.add_stack(eip.EIPStack())

def prod_stacks():

    prod_infra = infra.create_sub_infra("prod")

    common_stacks(prod_infra)

    vpc = prod_infra.find_stack(VPCStack)

    vpc.base_cidr = "10.10"

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

    vpc = dev_infra.find_stack(VPCStack)

    vpc.base_cidr = "10.50"

    return dev_infra


session = stackformation.BotoSession(region_name='us-east-2')

infra = stackformation.Infra("Jch", session)

prod_infra = prod_stacks()
dev_infra =  dev_stacks()


stacks = infra.list_stacks()

for stack in stacks:
    print("STACK: {}".format(stack.get_stack_name()))
    print("DEPS: ")
    deps = infra.get_dependent_stacks(stack)
    for s in  deps:
        print(" -{} ({})".format(s.get_stack_name(), s.__class__))
    print("------------------")


cf = session.client("cloudformation")


