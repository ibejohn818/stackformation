from stackformation.aws.stacks import BaseStack
import troposphere.elasticloadbalancing as elb
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)


class ELBStack(BaseStack):

    def __init__(self, stack_name, vpc):

        super(ELBStack, self).__init__("ELB", 100)

        self.stack_name = stack_name
        self._is_public = True
        self.public_subnets = True
        self.vpc = vpc
        self.listeners = []
        self.crosszone = True
        self.security_groups = []

    @property
    def is_public(self):
        return self._is_public

    @is_public.setter
    def is_public(self, val):
        self._is_public = val
        return self._is_public

    def get_scheme(self):
        """

        """
        if self.is_public:
            return "internet-facing"
        else:
            return "internal"

    def add_security_group(self, group):
        self.security_groups.append(group)

    def add_listener(self, proto, port_in, port_out, **kwargs):
        lst = elb.Listener(
            Protocol=proto,
            LoadBalancerPort=port_in,
            InstancePort=port_out
        )

        if kwargs.get('ssl_id'):
            lst.SSLCertificateId = kwargs.get('ssl_id')

        self.listeners.append(lst)

    def build_template(self):

        t = self._init_template()

        if len(self.listeners) <= 0:
            self.add_listener("HTTP", 80, 80)

        security_groups = [
            Ref(t.add_parameter(Parameter(
                group.output_security_group(),
                Type='String'
            )))
            for group in self.security_groups
        ]

        health_check_unhealthy_threshold = t.add_parameter(
            Parameter(
                'Input{}HealthUnhealthyThreshold'.format(
                    self.stack_name),
                Type='String',
                Default='3',
                Description='{} ELB HealthCheck Unhealthy Threshold'.format(
                    self.stack_name)))

        health_check_healthy_threshold = t.add_parameter(
            Parameter(
                'Input{}HealthHealthyThreshold'.format(
                    self.stack_name),
                Type='String',
                Default='3',
                Description='{} ELB HealthCheck Healthy Threshold'.format(
                    self.stack_name)))

        health_check_interval = t.add_parameter(Parameter(
            'Input{}HealthInterval'.format(self.stack_name),
            Type='String',
            Default='30',
            Description='{} ELB HealthCheck Interval'.format(self.stack_name)
        ))

        health_check_uri = t.add_parameter(Parameter(
            'Input{}HealthURI'.format(self.stack_name),
            Type='String',
            Default='/',
            Description='{} ELB HealthCheck URI'.format(self.stack_name)
        ))

        lb = t.add_resource(elb.LoadBalancer(
            '{}ELB'.format(self.stack_name),
            Scheme=self.get_scheme(),
            Listeners=self.listeners,
            CrossZone=self.crosszone,
            SecurityGroups=security_groups,
            HealthCheck=elb.HealthCheck(
                Target=Join("", ["HTTP:", '80', Ref(health_check_uri)]),
                HealthyThreshold=Ref(health_check_healthy_threshold),
                UnhealthyThreshold=Ref(health_check_unhealthy_threshold),
                Interval=Ref(health_check_interval),
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
