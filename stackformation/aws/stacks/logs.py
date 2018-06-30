from stackformation.aws.stacks import (BaseStack)
import troposphere.logs as logs
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)


class LogGroup(object):

    def __init__(self, name):

        self.name = name
        self.stack = None

    def output_log_group(self):
        return "{}{}LogGroup".format(
            self.stack.get_stack_name(),
            self.name
        )

    def build_group(self, t):

        group = t.add_resource(logs.LogGroup(
            "{}LogGroup".format( self.name)
        ))

        t.add_output([
            Output(
                "{}LogGroup".format(
                    self.name
                ),
                Value=Ref(group)
            )
        ])

        return group


class LogStack(BaseStack):

    def __init__(self, name):

        super(LogStack, self).__init__('Logs', 100)

        self.stack_name = name
        self.groups = []

    def add_group(self, group):
        group.stack = self
        self.groups.append(group)
        return group

    def find_group(self, name):
        for g in self.groups:
            if g.name == name:
                return g
        return None

    def build_template(self):

        t = self._init_template()

        retention = t.add_parameter(Parameter(
            "Input{}LogRetentionDays".format(self.stack_name),
            Type='String',
            Default='7',
            Description='{} Log Group Retention Days'.format(self.stack_name)
        ))

        for g in self.groups:
            g.RetentionInDays = Ref(retention)
            g.build_group(t)

        return t
