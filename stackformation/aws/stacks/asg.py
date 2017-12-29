from stackformation.aws.stacks import BaseStack
from stackformation.aws import Ami
from troposphere import ec2
from troposphere import autoscaling
from troposphere.policies import UpdatePolicy, AutoScalingRollingUpdate
from troposphere import (
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Template, Base64,
    GetAZs, Export, Tags
)


class ASGStack(BaseStack):

    def __init__(self, name, vpc, iam_profile):

        super(ASGStack, self).__init__("ASG", 400)

        self.stack_name = name
        self.vpc_stack = vpc
        self.iam_profile = iam_profile
        self.elb_stacks = []
        self.private_subnet = False
        self.security_groups = []
        self.pause_time = 'PT5M'
        self.update_policy_instance_count = 2
        self.ami = None,
        self.keyname = None

    def set_ami(self, ami):
        if isinstance(ami, (Ami)):
            self.ami = ami.get_ami()
        else:
            self.ami = ami

    def add_elb(self, elb_stack):
        self.elb_stacks.append(elb_stack)

    def add_security_group(self, sg):
        self.security_groups.append(sg)

    def add_user_data(self, ud):
        self.add_template_component(ud)

    def build_template(self):

        t = self._init_template()

        min_inst = t.add_parameter(Parameter(
            'Input{}ASGMinInstances'.format(self.stack_name),
            Type='String',
            Default='2',
            Description='{} Minimum # of instances'.format(self.stack_name)
        ))

        max_inst = t.add_parameter(Parameter(
            'Input{}ASGMaxInstances'.format(self.stack_name),
            Type='String',
            Default='10',
            Description='{} Minimum # of instances'.format(self.stack_name)
        ))

        des_inst = t.add_parameter(Parameter(
            'Input{}ASGDesiredInstances'.format(self.stack_name),
            Type='String',
            Default='2',
            Description='{} Minimum # of instances'.format(self.stack_name)
        ))

        inst_type = t.add_parameter(Parameter(
            'Input{}ASGInstanceType'.format(self.stack_name),
            Type='String',
            Default='t2.micro',
            Description='{} Instance Type'.format(self.stack_name)
        ))

        inst_tag_name = t.add_parameter(Parameter(
            'Input{}ASGTagName'.format(self.stack_name),
            Type='String',
            Default='{} ASG'.format(self.name),
            Description='{} Instance Type'.format(self.stack_name)
        ))

        #termination policies
        term_policies = t.add_parameter(Parameter(
            'Input{}ASGTerminationPolicies'.format(self.stack_name),
            Type='String',
            Default='Default',
            Description='{} Instance Type'.format(self.stack_name)
        ))

        # root file size
        root_device_size = t.add_parameter(Parameter(
            "Input{}ASGRootDeviceSize".format(self.stack_name),
            Type="String",
            Default="20",
            Description="{} Root Device File Size".format(self.stack_name)
        ))

        # root device name
        root_device_name = t.add_parameter(Parameter(
            "Input{}ASGRootDeviceName".format(self.stack_name),
            Type="String",
            Default="/dev/xvda",
            Description="{} Root Device Name".format(self.stack_name)
        ))

        # root device type
        root_device_type = t.add_parameter(Parameter(
            "Input{}ASGRootDeviceType".format(self.stack_name),
            Type="String",
            Default="gp2",
            Description="{} Root Device Type".format(self.stack_name)
        ))



        # instance profile
        instance_profile_param = t.add_parameter(Parameter(
            self.iam_profile.output_instance_profile(),
            Type='String'
        ))

        min_in_service = Ref(des_inst)

        # sec groups
        sec_groups = [
                Ref(t.add_parameter(Parameter(
                    sg.output_security_group(),
                    Type='String'
                )))
                for sg in self.security_groups
            ]

        user_data_refs = [
                Ref(t.add_parameter(Parameter(
                    '{}UserData{}'.format(self.name, i),
                    Type='String',
                    Default=' ',
                    Description='{} UserData #{}'.format(self.name, i)
                )))
                for i in range(0, 4)
                ]


        # subnet list
        if self.private_subnet:
            sn_list = [i for i in self.vpc_stack.output_private_subnets()]
        else:
            sn_list = [i for i in self.vpc_stack.output_public_subnets()]

        sn_list = [
                    Ref(t.add_parameter(Parameter(
                        i,
                        Type='String'
                    )))
                    for i  in sn_list
                ]

        lconfig = t.add_resource(autoscaling.LaunchConfiguration(
            '{}LaunchConfiguration'.format(self.name),
            AssociatePublicIpAddress=True,
            IamInstanceProfile=Ref(instance_profile_param),
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
            InstanceType=Ref(inst_type),
            SecurityGroups=sec_groups,
            ImageId=self.ami,
            UserData=Base64(Join('', [
                "#!/bin/bash\n",
                "exec > >(tee /var/log/user-data.log|logger ",
                "-t user-data -s 2>/dev/console) 2>&1\n",
                ] + user_data_refs + [
                "\n", 
                "#yum update -y aws-cfn-bootstrap",
                "\n",
                "curl -L https://gist.github.com/ibejohn818",
                "/aa2bcd6743a59f62e1baa098d6365a61/raw/",
                "/ubuntu-init.sh",
                " -o /tmp/ubuntu-init.sh && chmod +x /tmp/ubuntu-init.sh",
                "\n",
                "/tmp/ubuntu-init.sh",
                "\n",
                #] + wait_cmd + [
                "cfn-signal -e 0",
                "    --resource {}AutoScalingGroup".format(self.stack_name),
                "    --stack ", Ref("AWS::StackName"),
                "    --region ", Ref("AWS::Region"), "\n",
                ]
            ))
            ))

        if self.keyname:
            lconfig.KeyName = self.keyname

        asg = t.add_resource(autoscaling.AutoScalingGroup(
            '{}AutoScalingGroup'.format(self.stack_name),
            LaunchConfigurationName=Ref(lconfig),
            MinSize=Ref(min_inst),
            MaxSize=Ref(max_inst),
            VPCZoneIdentifier=sn_list,
            HealthCheckType='EC2',
            TerminationPolicies=[Ref(term_policies)],
            UpdatePolicy=UpdatePolicy(
                AutoScalingRollingUpdate=AutoScalingRollingUpdate(
                    PauseTime=self.pause_time,
                    MinInstancesInService=min_in_service,
                    MaxBatchSize=str(self.update_policy_instance_count),
                    WaitOnResourceSignals=True
                )
            )
           ))


        return t
