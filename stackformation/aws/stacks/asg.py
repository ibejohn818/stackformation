from stackformation.aws.stacks import BaseStack
from stackformation.aws import Ami
from troposphere import ec2
from troposphere import autoscaling
from troposphere.policies import UpdatePolicy, AutoScalingRollingUpdate
from troposphere import (  # noqa
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
        self._ami = None,
        self._keyname = None

    @property
    def keyname(self):
        return self._keyname

    @keyname.setter
    def keyname(self, keyname):
        self._keyname = keyname

    @property
    def ami(self):
        if isinstance(self._ami, (Ami)):
            return self._ami.get_ami()
        return self._ami

    @ami.setter
    def ami(self, value):
        self._ami = value

    def add_elb(self, elb_stack):
        self.elb_stacks.append(elb_stack)

    def add_security_group(self, sg):
        self.security_groups.append(sg)

    def add_user_data(self, ud):
        self.add_template_component("UserData", ud)

    def before_deploy(self, context, parameters):

        ud_key = "{}UserData".format(self.stack_name)

        if context.check_var(ud_key):

            user_data = context.get_var(ud_key)

            n = 4096

            ud_list = [user_data[i:i + n] for i in range(0, len(user_data), n)]

            for k, v in enumerate(ud_list):
                varname = "{}{}".format(ud_key, k)
                context.add_vars({varname: v})

    def output_asg(self):
        return "{}{}ASG".format(
            self.get_stack_name(),
            self.stack_name
        )

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
            Default='{}ASG'.format(self.name),
            Description='{} Instance Name Tag'.format(self.stack_name)
        ))

        # termination policies
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

        # subnet list
        if self.private_subnet:
            sn_list = [i for i in self.vpc_stack.output_private_subnets()]
            associate_public_ip = False
        else:
            sn_list = [i for i in self.vpc_stack.output_public_subnets()]
            associate_public_ip = True

        sn_list = [
            Ref(t.add_parameter(Parameter(
                i,
                Type='String'
            )))
            for i in sn_list
        ]

        elb_list = [
            Ref(t.add_parameter(Parameter(
                elb.output_elb(),
                Type='String'
            )))
            for elb in self.elb_stacks
        ]

        lconfig = t.add_resource(autoscaling.LaunchConfiguration(
            '{}LaunchConfiguration'.format(self.name),
            AssociatePublicIpAddress=associate_public_ip,
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
            ] + user_data + [
                "\n",
                "\n",
                "curl -L https://gist.github.com/ibejohn818",
                "/aa2bcd6743a59f62e1baa098d6365a61/raw",
                "/install-cfn-init.sh",
                " -o /tmp/install-cfn-init.sh && chmod +x /tmp/install-cfn-init.sh",  # noqa
                "\n",
                "/tmp/install-cfn-init.sh ",
                " {}AutoScalingGroup".format(self.stack_name),
                " ", Ref("AWS::StackName"),
                " ", Ref("AWS::Region"),
                "\n",
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
            DesiredCapacity=Ref(des_inst),
            VPCZoneIdentifier=sn_list,
            HealthCheckType='EC2',
            TerminationPolicies=[Ref(term_policies)],
            LoadBalancerNames=elb_list,
            Tags=autoscaling.Tags(Name=Ref(inst_tag_name)),
            UpdatePolicy=UpdatePolicy(
                AutoScalingRollingUpdate=AutoScalingRollingUpdate(
                    PauseTime=self.pause_time,
                    MinInstancesInService=min_in_service,
                    MaxBatchSize=str(self.update_policy_instance_count),
                    WaitOnResourceSignals=True
                )
            )
        ))

        t.add_output([
            Output(
                '{}ASG'.format(self.stack_name),
                Value=Ref(asg)
            )
        ])

        return t
