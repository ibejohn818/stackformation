from stackformation.aws.stacks import (StackComponent)
import stackformation
import json
import os
import subprocess
import yaml
from stackformation.aws import PackerImage

CWD = os.path.realpath(os.path.dirname(stackformation.__file__)).strip('/')

AMI_INFO={
    'ubuntu': {
        'username': 'ubuntu',
        'ami_filters': [
            {
                'Name': 'name',
                'Values': ['ubuntu*16*']
            },
        ]
    },
    'awslinux': {
        'username': 'ec2-user',
        'ami_filters': [
            {
                'Name': 'name',
                'Values': ['amzn-ami*x86_64-gp2']
            },
            {
                'Name': 'description',
                'Values': ["*Linux*"]
            },
        ]
    }
}

class BaseAmi(StackComponent):

    def __init__(self, name, os_type='aws'):

        super(BaseAmi, self).__init__(name)
        self.boto_session = None
        self.os_type = os_type





class Ami(PackerImage):

    def __init__(self, name, os_type='awslinux'):

        super(Ami, self).__init__(name)
        self.os_type = os_type
        self.base_ami_info = None

    def get_base_ami(self):
        """
        Get the latest AWS Linux AMI based on
        the creation date

        Args:
            botoKwargs (dict): the boto3 client kwargs

        Returns:
            amiid (str): The AWS Linux AmiID
        """

        filters = [
                {
                    'Name': 'architecture',
                    'Values': ["x86_64"]
                },
                {
                    'Name': 'root-device-type',
                    'Values': ["ebs"]
                },
                {
                    'Name': 'virtualization-type',
                    'Values': ["hvm"]
                },
                {
                    'Name': 'state',
                    'Values': ['available']
                },
                {
                    'Name': 'ena-support',
                    'Values': ['true']
                },
                {
                    'Name': 'image-type',
                    'Values': ['machine']
                },
                {
                    'Name': 'is-public',
                    'Values': ['true']
                },
            ]

        filters.extend(AMI_INFO[self.os_type]['ami_filters'])

        amis_query = self.boto_session.client("ec2").describe_images(Filters=filters)

        # sort by CreationDate
        amis_query['Images'].sort(
            key=lambda item: item['CreationDate'],
            reverse=True)

        ami = amis_query['Images'][0]

        self.base_ami_info = ami

        return ami['ImageId']

    def get_ami(self):
        return self.get_base_ami()


    def get_vpc_id(self):

        ec2 = self.boto_session.client('ec2')

        f = [
                {'Name': 'is-default', 'Values': ['true']}
            ]

        vpc = ec2.describe_vpcs(Filters=f)

        return vpc['Vpcs'][0]['VpcId']

    def generate(self):

        self.region = self.boto_session.get_conf('region_name')

        aws_builder = {
                'type':'amazon-ebs',
                'source_ami': self.get_base_ami(),
                'instance_type':'t2.medium',
                'communicator': 'ssh',
                'ssh_pty': 'true',
                'ssh_username': self.get_ssh_user(),
                'ami_name':"AMI {}".format(self.name),
                'region':self.region,
                'vpc_id': self.get_vpc_id()

        }

        shell = {
                'type': 'shell',
                'inline': ['echo "HELLLP"']
                }

        self.add_builder(aws_builder)
        self.add_provisioner(shell)
        self.save_packer_file()
        return super(Ami, self).generate()














