from stackformation.aws.stacks import BaseStack
from troposphere import ec2
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export, Base64
)


class EBSVolume(object):

    def __init__(self, name, size, az_index=0, volume_type="gp2"):

        self.name = name
        self.stack = None
        self.volume_size = size
        self.volume_type = volume_type
        self.az_index = az_index

    def _build_volume(self, template, vpc):

        t = template

        az = vpc.output_azs()[self.az_index]

        if az in t.parameters:
            az_ref = Ref(t.parameters[az])
        else:
            az_param = t.add_parameter(Parameter(
                az,
                Type='String'
            ))

            az_ref = Ref(az_param)

        ebs = t.add_resource(ec2.Volume(
            '{}EBSVolume'.format(self.name),
            Size=self.volume_size,
            VolumeType=self.volume_type,
            AvailabilityZone=az_ref,
            Tags=Tags(
                Name="{} EBS Volume".format(self.name)
            )
        ))

        t.add_output(Output(
            '{}Volume'.format(self.name),
            Value=Ref(ebs),
            Description="{} EBS Volume".format(self.name)
        ))
        return ebs

    def output_volume(self):
        return "{}{}Volume".format(self.stack.get_stack_name(),
                                   self.name)


class EBSStack(BaseStack):

    def __init__(self, name, vpc_stack):

        super(EBSStack, self).__init__("EBS", 10)

        self.stack_name = name
        self.ebs_volumes = []
        self.vpc_stack = vpc_stack

    def add_volume(self, volume):
        self.ebs_volumes.append(volume)
        volume.stack = self
        return volume

    def find_volume(self, name):

        for v in self.ebs_volumes:
            if v.name == name:
                return v

        return None

    def build_template(self):

        t = self._init_template()

        for v in self.ebs_volumes:
            v._build_volume(t, self.vpc_stack)

        return t
