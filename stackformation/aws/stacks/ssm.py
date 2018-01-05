from stackformation import BaseStack
import inflection
import re
import troposphere.ssm as ssm
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)


class SSMType(object):

    def __init__(self, name):
        self.name = inflection.camelize(name)
        if re.search('\s', self.name):
            print("SSM Parameter Names cannot contain spaces! ({})".format(self.name))  # noqa
            exit(1)

        self.stack = None

    def ask(self):
        ans = input("Enter value for ({})".format(self.name))
        return ans


class SecureString(SSMType):

    def add_to_template(self, template):

        value = self.ask()

        val_param = template.add_parameter(Parameter(
            "{}SSMSecureString".format(self.name),
            Type='String',
            Default=value,
            NoEcho=True
        ))

        string = template.add_resource(ssm.Parameter(
            "{}SSMStringType".format(self.name),
            Name=self.name,
            Value=Ref(val_param),
            Type='SecureString'
        ))

        template.add_output([
            Output(
                "{}SSMSecureString".format(self.name),
                Value=Ref(string)
            )
        ])

    def output_ssm_secure_string(self, name):
        return "{}{}SSMSecureString".format(
            self.stack.get_stack_name(),
            self.name
        )


class SSMParamStack(BaseStack):

    def __init__(self, name):

        super(SSMParamStack, self).__init__("SSMParam", 1)

        self.stack_name = name
        self.parameters = []

    def add_param(self, name):
        self.parameters.append(name)

    def build_template(self):

        t = self._init_template()

        for p in self.parameters:
            p.stack = self
            p.add_to_template(t)

        return t
