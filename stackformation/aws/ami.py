from stackformation import StackComponent
import stackformation
import json
import os


CWD = os.path.realpath(os.path.dirname(__file__))
print(stackformation.__file__)

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
    'aws': {
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

        return amis_query['Images'][0]['ImageId']



class Ami(BaseAmi):
    pass
