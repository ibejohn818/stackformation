from stackformation.aws.stacks import (BaseStack, SoloStack)
from troposphere import ec2
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)


class EIP(object):

    def __init__(self, name):

        self.name = name
        self.stack = None

    def _build_ip(self, t):

        eip = t.add_resource(ec2.EIP(
            "{}EIP".format(self.name)
        ))

        t.add_output([
            Output(
                "{}AllocationId".format(self.name),
                Value=GetAtt(eip, "AllocationId"),
                Description="{} Elastic IP".format(self.name)
            ),
            Output(
                "{}EIP".format(self.name),
                Value=Ref(eip),
                Description="{} Elastic IP".format(self.name)
            ),
        ])

    def output_eip(self):
        """Return EIP"""
        return "{}{}EIP".format(self.stack.get_stack_name(), self.name)

    def output_allocation_id(self):
        """Return EIP Allocation ID"""
        return "{}{}AllocationId".format(
            self.stack.get_stack_name(), self.name)


class EIPStack(BaseStack, SoloStack):

    def __init__(self, stack_name=""):

        super(EIPStack, self).__init__("EIP", 0)

        self.stack_name = stack_name

        self.ips = []

    def add_ip(self, name):

        eip = EIP(name)
        eip.stack = self
        self.ips.append(eip)
        return eip

    def find_ip(self, name):

        for ip in self.ips:
            if ip.name == name:
                return ip

        return None

    def build_template(self):

        t = self._init_template()

        for ip in self.ips:
            ip._build_ip(t)

        return t
