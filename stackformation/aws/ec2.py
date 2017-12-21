from stackformation.base import BaseStack




class Ec2Stack(BaseStack):

    def __init__(self, stack_name, vpc):

        super(Ec2Stack, self).__init__("EC2", 500)

        self.stack_name = stack_name
        self.vpc = vpc

    def build_template(self, infra):

        t = self.template

        return t
