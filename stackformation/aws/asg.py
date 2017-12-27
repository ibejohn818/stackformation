from stackformation import BaseStack
from troposphere import ec2
from troposphere import autoscaling
from troposphere import (
        FindInMap, GetAtt, Join,
        Parameter, Output, Ref,
        Select, Template,
        GetAZs, Export, Tags
)

class ASGStack(BaseStack):

    def __init(self, name, vpc):

        super(ASGStack, self).__init__("ASG", 400)

        self.stack_name = name
        self.vpc_stack = vpc
        self.elbs = []
        self.private_subnet = False



    def build_template(self):

        t = self._init_template()

        t.add_parameter(Parameter(
            'Input{}ASGMinInstances'.format(self.stack_name),
            Type='String',
            Description='{} Minimum # of instances'.format(self.stack_name)
        ))

        t.add_parameter(Parameter(
            'Input{}ASGMaxInstances'.format(self.stack_name),
            Type='String',
            Description='{} Minimum # of instances'.format(self.stack_name)
        ))

        t.add_parameter(Parameter(
            'Input{}ASGDesiredInstances'.format(self.stack_name),
            Type='String',
            Description='{} Minimum # of instances'.format(self.stack_name)
        ))

        t.add_parameter(Parameter(
            'Input{}InstanceType'.format(self.stack_name),
            Type='String',
            Description='{} Instance Type'.format(self.stack_name)
        ))

        # launch = t.add_resource(autoscaling.LaunchConfiguration(
            # '{}LaunchConfig'.format(self.stack_name),


        return t
