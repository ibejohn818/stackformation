from stackformation.aws.stacks import BaseStack
import logging
from colorama import Fore, Style, Back
from troposphere import ec2
from troposphere import (
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export, Base64
)


logger = logging.getLogger(__name__)


class EC2Stack(BaseStack):

    def __init__(self, stack_name, vpc, iam_profile):

        super(EC2Stack, self).__init__("EC2", 500)

        self.stack_name = stack_name
        self.vpc = vpc
        self.iam_profile = iam_profile
        self.private_subnet = False
        self.security_groups = []
        self.ami = 'ami-15e9c770'
        self.ami = 'ami-597d553c'
        self.use_key = None
        self.volumes = []

    def add_security_group(self, group):

        self.security_groups.append(group)

        return group

    def add_user_data(self, comp):

        self.add_template_component("UserData", comp)

    def keypair(self, key):
        self.use_key = key

    def add_volume(self, volume):
        self.volumes.append(volume)

    def before_deploy(self, context, parameters):

        ud_key = "{}UserData".format(self.stack_name)

        if not context.check_var(ud_key):
            return

        user_data = context.get_var(ud_key)

        n = 4096

        ud_list = [user_data[i:i + n] for i in range(0, len(user_data), n)]

        for k, v in enumerate(ud_list):
            varname = "{}{}".format(ud_key, k)
            context.add_vars({varname: v})

    def build_template(self):

        t = self._init_template()

        # tag Name
        tag_name = t.add_parameter(Parameter(
            "Input{}EC2TagName".format(self.stack_name),
            Type="String",
            Default='{} EC2'.format(self.stack_name),
            Description="Tag name for {} EC2 Stack".format(self.stack_name)
        ))

        # instance type
        instance_type = t.add_parameter(
            Parameter(
                "Input{}EC2InstanceType".format(
                    self.stack_name),
                Type="String",
                Description="Instance Type for {} EC2 Stack".format(
                    self.stack_name),
                Default="t2.micro"))

        # root file size
        root_device_size = t.add_parameter(Parameter(
            "Input{}EC2RootDeviceSize".format(self.stack_name),
            Type="String",
            Default="20",
            Description="{} Root Device File Size".format(self.stack_name)
        ))

        # root device name
        root_device_name = t.add_parameter(Parameter(
            "Input{}EC2RootDeviceName".format(self.stack_name),
            Type="String",
            Default="/dev/xvda",
            Description="{} Root Device Name".format(self.stack_name)
        ))

        # root device type
        root_device_type = t.add_parameter(Parameter(
            "Input{}EC2RootDeviceType".format(self.stack_name),
            Type="String",
            Default="gp2",
            Description="{} Root Device Type".format(self.stack_name)
        ))

        # instance profile
        instance_profile_param = t.add_parameter(Parameter(
            self.iam_profile.output_instance_profile(),
            Type='String'
        ))

        # user data params
        user_data = []
        for i in range(0, 4):
            user_data.append(
                Ref(t.add_parameter(Parameter(
                    '{}UserData{}'.format(self.stack_name, i),
                    Type='String',
                    Default=' ',
                    Description='{} UserData #{}'.format(self.stack_name, i)
                )))
            )

        interface = ec2.NetworkInterfaceProperty(
            Description='ENI for host',
            DeviceIndex=0,
            GroupSet=[],
            DeleteOnTermination=True,
        )

        # subnet
        if self.private_subnet:
            subnet = self.vpc.output_private_subnets()[0]
        else:
            interface.AssociatePublicIpAddress = True
            subnet = self.vpc.output_public_subnets()[0]

        subnet_param = t.add_parameter(Parameter(
            subnet,
            Type='String',
            Description='Subnet for ec2 {}'.format(self.stack_name)
        ))

        interface.SubnetId = Ref(subnet_param)

        for sg in self.security_groups:

            sg_param = t.add_parameter(Parameter(
                sg.output_security_group(),
                Type='String'
            ))

            interface.GroupSet.append(Ref(sg_param))

        volumes = []
        for volume in self.volumes:
            device_name = t.add_parameter(Parameter(
                'Input{}EBSDeviceName'.format(volume.name),
                Type='String'
            ))

            volume_id = t.add_parameter(Parameter(
                volume.output_volume(),
                Type="String"
            ))

            volumes.append(ec2.MountPoint(
                VolumeId=Ref(volume_id),
                Device=Ref(device_name)
            ))

        instance = t.add_resource(ec2.Instance(
            '{}EC2Instance'.format(self.stack_name),
            Tags=Tags(
                Name=Ref(tag_name)
            ),
            ImageId=self.ami,
            Volumes=volumes,
            InstanceType=Ref(instance_type),
            IamInstanceProfile=Ref(instance_profile_param),
            NetworkInterfaces=[interface],
            BlockDeviceMappings=[
                ec2.BlockDeviceMapping(
                    DeviceName=Ref(root_device_name),
                    Ebs=ec2.EBSBlockDevice(
                        VolumeSize=Ref(root_device_size),
                        VolumeType=Ref(root_device_type),
                        DeleteOnTermination=True
                    )
                )
            ],
            UserData=Base64(
                Join('', [
                    "#!/bin/bash\n",
                    "exec > >(tee /var/log/user-data.log|logger ",
                    "-t user-data -s 2>/dev/console) 2>&1\n",
                ] + user_data
                ))
        ))

        if self.use_key:
            instance.KeyName = self.use_key

        t.add_output([
            Output(
                '{}EC2Instance'.format(self.stack_name),
                Value=Ref(instance)
            )
        ])

        return t

    def output_instance(self):
        return "{}{}EC2Instance".format(
            self.get_stack_name(), self.stack_name)
