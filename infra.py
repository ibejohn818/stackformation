import stackformation
from stackformation.deploy import (
        DeployStacks
)
from stackformation.aws.elb import ELBStack
from stackformation.aws import ( iam, vpc, ec2, user_data,
                                    ebs, s3, eip
                                )


def common_stacks(infra):

    vpc_stack = infra.add_stack(vpc.VPCStack(num_azs=3))

    ssh_sg = vpc_stack.add_security_group(vpc.SSHSecurityGroup())

    web_sg = vpc_stack.add_security_group(vpc.WebSecurityGroup())

    iam_stack = infra.add_stack(iam.IAMStack())

    web_profile = iam.EC2AdminProfile("WebAdmin")

    iam_stack.add_role(web_profile)

    s3_stack = infra.add_stack(s3.S3Stack("test"))

    test_bucket = s3_stack.add_bucket(s3.S3Bucket("jchtest"))

    web_profile.add_policy(iam.S3FullBucketAccess(test_bucket))

    eip_stack = infra.add_stack(eip.EIPStack())

def prod_stacks():

    prod_infra = infra.create_sub_infra("prod")

    prod_infra.add_vars({
        'InputWebEC2TagName': "WebServer",
        'InputWebEC2InstanceType': "t2.medium",
        'InputWebEC2RootDeviceSize': "50",
        'InputWebEBSDeviceName': "/dev/xvdb",
        'InputNFSEBSDeviceName': "/dev/xvdc",
    })
    common_stacks(prod_infra)

    vpc_stack = prod_infra.find_stack(vpc.VPCStack)

    vpc_stack.base_cidr = "10.10"

    web_sg = vpc_stack.find_security_group(vpc.WebSecurityGroup)
    ssh_sg = vpc_stack.find_security_group(vpc.SSHSecurityGroup)

    eip_stack = prod_infra.find_stack(eip.EIPStack)

    web_ip = eip_stack.add_ip("WebServer")

    ebs_stack = prod_infra.add_stack(ebs.EBSStack("Vols", vpc_stack))

    web_vol = ebs_stack.add_volume(ebs.EBSVolume('Web', 100))
    nfs_vol = ebs_stack.add_volume(ebs.EBSVolume('NFS', 350))

    iam_stack = prod_infra.find_stack(iam.IAMStack)

    web_profile = iam_stack.find_role(iam.EC2AdminProfile)

    ec2_stack = prod_infra.add_stack(ec2.EC2Stack("Web", vpc_stack, web_profile))

    ec2_stack.add_security_group(web_sg)
    ec2_stack.add_security_group(ssh_sg)

    ec2_stack.add_volume(nfs_vol)
    ec2_stack.add_volume(web_vol)

    ec2_stack.keypair("jch")
    ec2_stack.add_user_data(user_data.WriteEIP(web_ip))
    ec2_stack.add_user_data(user_data.MountEBS(nfs_vol, "/mnt/nfs"))
    ec2_stack.add_user_data(user_data.MountEBS(web_vol, "/mnt/web"))

    return prod_infra

def dev_stacks():

    dev_infra = infra.create_sub_infra("dev")

    dev_infra.add_vars({
        'InputWebEC2TagName': "WebServer",
    })

    common_stacks(dev_infra)

    vpc_stack = dev_infra.find_stack(vpc.VPCStack)

    vpc_stack.base_cidr = "10.50"

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
    for k, s in  deps.items():
        print(" -{} ({})".format(s.get_stack_name(), s.__class__))
    print("------------------")


cf = session.client("cloudformation")


