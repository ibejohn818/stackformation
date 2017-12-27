from stackformation import BaseStack
import inflection
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
        self.public_subnets = True
        self.vpc = vpc
        self.listeners = []
        self.crosszone = True

    def get_scheme(self):
        """

        """
        if self.is_public:
            return "internet-facing"
        else:
            return "internal"

    def add_listener(self, proto, port_in, port_out, **kwargs):
        l = elb.Listener(
                Protocol=proto,
                LoadBalancerPort=port_in,
                InstancePort=port_out
            )

        if kwargs.get('ssl_id'):
            l.SSLCertificateId=kwargs.get('ssl_id')

        self.listeners.append(l)


    def build_template(self):

        t = self._init_template()

        if len(self.listeners) <= 0:
            self.add_listener("HTTP", 80, 80)


        lb = t.add_resource(elb.LoadBalancer(
            '{}ELB'.format(self.stack_name),
            Scheme=self.get_scheme(),
            Listeners=self.listeners,
            CrossZone=self.crosszone,
            HealthCheck=elb.HealthCheck(
                Target=Join("", ["HTTP:", '80', "/"]),
                HealthyThreshold="3",
                UnhealthyThreshold="5",
                Interval="30",
                Timeout="5",
            )
        ))


        if not self.public_subnets:
            subs = self.vpc.output_private_subnets()
        else:
            subs = self.vpc.output_public_subnets()

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

        t.add_output([
            Output(
                '{}ELB'.format(self.stack_name),
                Value=Ref(lb)
            )
        ])

        return t

    def output_elb(self):
        return "{}{}ELB".format(self.get_stack_name(), self.stack_name)
