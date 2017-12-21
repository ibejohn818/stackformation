from stackformation.base import BaseStack
from troposphere import ec2
from troposphere import (
        FindInMap, GetAtt, Join,
        Parameter, Output, Ref,
        Select, Tags, Template,
        GetAZs, Export
)



class EipStack(BaseStack):

    def __init__(self, stack_name):

        super(EipStack, self).__init__("EIP", 1)

        self.stack_name = stack_name

        self.ips = {}

    def add_ip(self, name):

        self.ips.update({name:
            self.template.add_resource(ec2.EIP(
                "{}EIP".format(name)
            ))
        })

        self.template.add_output([
            Output(
                "{}AllocationId".format(name),
                Value=GetAtt(self.ips[name], "AllocationId"),
                Description="{} Elastic IP".format(name)
            ),
            Output(
                "{}EIP".format(name),
                Value=Ref(self.ips[name]),
                Description="{} Elastic IP".format(name)
            ),
        ])

        return self.ips[name]

    def build_template(self):
        return self.template


    def output_eip(self, name):
        return "{}{}EIP".format(self.get_stack_name(),name)

    def output_allocation_id(self, name):
        return "{}{}AllocationId".format(self.get_stack_name(), name)
