from stackformation import BaseStack
from troposphere import ec2
from troposphere import (
        FindInMap, GetAtt, Join,
        Parameter, Output, Ref,
        Select, Tags, Template,
        GetAZs, Export
)



class EC2Stack(BaseStack):

    def __init__(self, stack_name, vpc):

        super(EC2Stack, self).__init__("EC2", 500)

        self.stack_name = stack_name
        self.vpc = vpc
        self.private_subnet = False


    def build_template(self):

        t = self._init_template()

        if self.private_subnet:
            subnet = self.vpc.subnets['private'][0]
        else:
            subnet = self.vpc.subnets['public'][0]

        tag_name = t.add_parameter(Parameter(
                        self.infra.find_input_name(
                            "Input{}EC2TagName".format(self.stack_name)
                        ),
                        Type="String",
                        Description="Tag name for {} EC2 Stack".format(self.stack_name)
                    ))

        instance_type = t.add_parameter(Parameter(
                        self.infra.find_input_name(
                            "Input{}EC2InstanceType".format(self.stack_name)
                        ),
                        Type="String",
                        Description="Instance Type for {} EC2 Stack".format(self.stack_name),
                        Default="t2.micro"
                    ))
        # ec2 = t.add_resource(ec2.Instance(
                # '{}EC2Instance'.format(stack_name),
                # SubnetId=Ref(subnet),
                # Tags=Tags(
                    # Name=Ref(tag_name)
                # ),
                # AmiId=self.ami,
                # InstanceType=Ref(instance_type)

        # ))

        return t
