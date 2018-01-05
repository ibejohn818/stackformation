from stackformation import BaseStack
from stackformation.aws.stacks import ec2, asg
import troposphere.codedeploy as cdeploy
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export, Base64
)


class App(object):

    def __init__(self, name):

        self.name = name
        self.stack = None
        self.strategy = 'CodeDeployDefault.OneAtATime'
        self.targets = []
        self.load_balancers = []

    def add_load_balancer(self, lb):
        self.load_balancers.append(lb)

    def add_target(self, target):
        self.targets.append(target)

    def output_app(self):
        return "{}{}App".format(
            self.stack.get_stack_name(),
            self.name
        )

    def output_group(self):
        return "{}{}Group".format(
            self.stack.get_stack_name(),
            self.name
        )

    def add_to_template(self, template):

        t = template
        app = t.add_resource(cdeploy.Application(
            self.name
        ))

        group = t.add_resource(cdeploy.DeploymentGroup(
            '{}Group'.format(self.name),
            ServiceRoleArn=Ref(self.stack.role_parameter),
            ApplicationName=Ref(app),
            DeploymentConfigName=self.strategy
        ))

        group.AutoScalingGroups = []
        group.Ec2TagFilters = []

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
            Output(
                '{}App'.format(self.name),
                Value=Ref(app)
            )
        ])


class CodeDeployStack(BaseStack):

    def __init__(self, name, role):

        super(CodeDeployStack, self).__init__("CodeDeploy", 900)

        self.stack_name = name
        self.apps = []
        self.role_parameter = None
        self.role = role

    def add_app(self, app):
        app.stack = self
        self.apps.append(app)
        return app

    def build_template(self):

        t = self._init_template()

        self.role_parameter = t.add_parameter(Parameter(
            self.role.output_role_arn(),
            Type='String'
        ))

        for app in self.apps:
            app.add_to_template(t)

        return t
