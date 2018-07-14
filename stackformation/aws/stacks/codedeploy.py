from stackformation import BaseStack
from stackformation.aws.stacks import ec2, asg
import troposphere.codedeploy as cdeploy
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export, Base64
)

from stackformation.utils import ensure_param

class Group(object):

    def __init__(self, targets, name, **kw):
        if not isinstance(targets, list):
            targets = [targets]
        self.name = name
        self.targets = targets
        self.load_balancers = []
        self.strategy = 'CodeDeployDefault.OneAtATime'
        self.stack = None
        self.role = kw.get('role', None)


    def add_load_balancer(self, lb):
        self.load_balancers.append(lb)

    def add_target(self, target):
        self.targets.append(target)

    def build(self, t, app):


        role_param = ensure_param(t, self.role.output_role_arn())

        group = t.add_resource(cdeploy.DeploymentGroup(
            '{}Group'.format(self.name),
            ServiceRoleArn=Ref(role_param),
            ApplicationName=Ref(app),
            DeploymentConfigName=self.strategy,
            # DeploymentStyle=cdeploy.DeploymentStyle(
                # DeploymentType='IN_PLACE',
                # DeploymentOption='WITH_TRAFFIC_CONTROL'
            # ),
            AutoScalingGroups=[]
        ))

        for target in self.targets:

            if isinstance(target, (ec2.EC2Stack)):
                ec2_tag = t.add_parameter(Parameter(
                    target.output_tag_name(),
                    Type='String'
                ))

                group.Ec2TagFilters.append(cdeploy.Ec2TagFilters(
                    Key='Name',
                    Value=Ref(ec2_tag),
                    Type='KEY_AND_VALUE'
                ))

            if isinstance(target, (asg.ASGStack)):

                asg_param = t.add_parameter(Parameter(
                    target.output_asg(),
                    Type='String'
                ))

                group.AutoScalingGroups.append(Ref(asg_param))


        t.add_output([
            Output(
                '{}Group'.format(self.name),
                Value=Ref(group)
            ),
        ])

    def output_group(self):
        return "{}{}Group".format(
            self.stack.get_stack_name(),
            self.name
        )

class App(object):

    def __init__(self, name):

        self.name = name
        self._stack = None
        self.groups = []

    @property
    def stack(self):
        return self._stack

    @stack.setter
    def stack(self, val):
        self._stack = val
        for k, v in enumerate(self.groups):
            self.groups[k].stack = self._stack
        return self._stack


    def add_group(self, group):

        if self.stack is not None:
            group.stack = self.stack
        self.groups.append(group)
        return group


    def output_app(self):
        return "{}{}App".format(
            self.stack.get_stack_name(),
            self.name
        )


    def add_to_template(self, template):

        t = template
        app = t.add_resource(cdeploy.Application(
            self.name
        ))

        for g in self.groups:
            g.build(t, app)

        t.add_output([
            Output(
                '{}App'.format(self.name),
                Value=Ref(app)
            )
        ])


class CodeDeployStack(BaseStack):

    def __init__(self, name):

        super(CodeDeployStack, self).__init__("CodeDeploy", 900)

        self.stack_name = name
        self.apps = []

    def add_app(self, app):
        app.stack = self
        self.apps.append(app)
        return app

    def build_template(self):

        t = self._init_template()

        for app in self.apps:
            app.add_to_template(t)

        return t
