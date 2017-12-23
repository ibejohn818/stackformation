from stackformation import BaseStack

from troposphere import ec2
import troposphere.elasticloadbalancing as elb
from troposphere import (
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)


class ELBStack(BaseStack):

    def __init__(self, stack_name, vpc):

        super(ELBStack, self).__init__("ELB", 100)

        self.stack_name = stack_name
        self.is_public = True
        self.vpc = vpc

    def get_scheme(self):
        """

        """
        if self.is_public:
            return "internet-facing"
        else:
            return "internal"

    def build_template(self):
        t = self._init_template()

        lb = t.add_resource(elb.LoadBalancer(
            'ELB{}'.format(self.stack_name),
            Scheme=self.get_scheme(),
            Listeners=[
                elb.Listener(
                    LoadBalancerPort="80",
                    InstancePort='80',
                    Protocol="HTTP",
                ),
            ],
            HealthCheck=elb.HealthCheck(
                Target=Join("", ["HTTP:", '80', "/"]),
                HealthyThreshold="3",
                UnhealthyThreshold="5",
                Interval="30",
                Timeout="5",
            )
        ))


        # set the azs based on vpc outputs
        azs = self.vpc.output_azs()
        az_params = [
            t.add_parameter(
                Parameter(
                    i,
                    Type="String"
                )
            )
            for i in azs
        ]

        lb.AvailabilityZones = [Ref(i) for i in az_params]


        if not self.is_public:
            subs = self.vpc.output_private_subnets()
            sn_params = [
                t.add_parameter(
                    Parameter(
                        i,
                        Type="String"
                    )
                )
                for i in subs
            ]

            lb.Subnets = [Ref(i) for i in sn_params]
        return t
