from stackformation import (BaseStack, SoloStack)
from troposphere import ec2
from troposphere import (
        FindInMap, GetAtt, Join,
        Parameter, Output, Ref,
        Select, Tags, Template,
        GetAZs, Export
)



class EipStack(BaseStack, SoloStack):

    def __init__(self, stack_name):

        super(EipStack, self).__init__("EIP", 0)

        self.stack_name = stack_name

        self.ips = []

    def add_ip(self, name):

        self.ips.append(name)

    def build_ip(self, ip, template):

        eip = template.add_resource(ec2.EIP(
            "{}EIP".format(ip)
        ))

        template.add_output([
            Output(
                "{}AllocationId".format(ip),
                Value=GetAtt(eip, "AllocationId"),
                Description="{} Elastic IP".format(ip)
            ),
            Output(
                "{}EIP".format(ip),
                Value=Ref(eip),
                Description="{} Elastic IP".format(ip)
            ),
        ])

    def build_template(self):

        t = self._init_template()

        for ip in self.ips:
            self.build_ip(ip, t)

        return t

    def output_eip(self, name):
        return "{}{}EIP".format(self.get_stack_name(),name)

    def output_allocation_id(self, name):
        return "{}{}AllocationId".format(self.get_stack_name(), name)
