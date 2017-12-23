# -*- coding: utf-8 -*-
import boto3
import troposphere
import inflection
import logging

"""Top-level package for StackFormation."""

__author__ = """John Hardy"""
__email__ = 'john@johnchardy.com'
__version__ = '0.1.0'

logger = logging.getLogger(__name__)

class BotoSession():

    def __init__(self, **kwargs):

        self.conf = {
            'region_name': 'us-west-2'
        }

        if kwargs.get('aws_access_key_id'):
            self.conf['aws_access_key_id'] = kwargs.get('aws_access_key_id')

        if kwargs.get('aws_secret_access_key'):
            self.conf['aws_secret_access_key'] = kwargs.get(
                'aws_secret_access_key')

        if kwargs.get('aws_session_token'):
            self.conf['aws_session_token'] = kwargs.get('aws_session_token')

        if kwargs.get('region_name'):
            self.conf['region_name'] = kwargs.get('region_name')

        if kwargs.get('botocore_session'):
            self.conf['botocore_session'] = kwargs.get('botocore_session')

        if kwargs.get('profile_name'):
            self.conf['profile_name'] = kwargs.get('profile_name')

        self._session = boto3.session.Session(**self.conf)

    def get_conf(self, key):
        if key not in self.conf:
            raise Exception("Conf Error: {} not set".format(key))
        return self.conf[key]

    @property
    def session(self):
        return self._session

    def client(self, client):
        return self.session.client(client)


class Context(object):

    def __init__(self):
        self.vars = {}
        self.sessions = {}

    def get_var(self, name):
        if not self.vars.get(name):
            return False
        return self.vars.get(name)

    def add_vars(self, new):
        self.vars.update(new)

    def get_input_var(self, key):
        pass

    def get_output_var(self, key):
        pass

    def get_input_vars(self):
        pass

    def get_output_vars(self):
        pass


class StackComponent(object):

    def __init__(self, name):
        self.name = name
        self.prefix = []

    def get_full_name(self):
        return "{}{}".format(
            self.prefix.capitalize(),
            self.name.captitalize()
        )


class Infra(object):

    def __init__(self, name, boto_session=None):

        self.name = name
        self.prefix = []
        self.stacks = []
        self.boto_session = boto_session
        self.sub_infras = []
        self.input_vars = {}
        self.output_vars = {}
        self.context = Context()

    def add_var(self, name, value):

        return self.context.update({name: value})

    def add_vars(self, inp_vars):

        return self.context.add_vars(inp_vars)

    def get_input_var_name(self, name):
        pass

    def find_input_name(self, name):
        if not self.context.get_var(name):
            raise Exception("ERROR: {} Input Not Set!".format(name))
        return name

    def create_sub_infra(self, prefix):
        """

        """

        infra = Infra(self.name)
        infra.prefix.extend(self.prefix + [prefix])
        infra.boto_session = self.boto_session
        self.sub_infras.append(infra)

        return infra

    def add_stack(self, stack):

        if not isinstance(stack, (BaseStack)):
            raise ValueError("Error adding stack. Invalid Type!")

        if isinstance(stack, SoloStack):
            for stk in self.stacks:
                if isinstance(stack, type(stk)):
                    raise Exception(
                        "Solo Stack Error: {} type already added".format(
                            type(stack).__name__))

        self.stacks.append(stack)
        stack.prefix = self.prefix
        stack.infra = self

        return stack

    def get_stacks(self):

        stacks = []
        for stack in self.stacks:
            stack.load_stack_outputs(self)
            stacks.append(stack)

        for infra in self.sub_infras:
            stacks.extend(infra.get_stacks())

        return stacks

    def gather_contexts(self):

        c = []

        c.append(self.context)

        for infra in self.sub_infras:
            c.extend(infra.gather_contexts())

        return c

    def find_stack(self, clazz):

        stacks = []

        for s in self.stacks:
            if isinstance(s, clazz):
                stacks.append(s)

        if len(stacks) > 0:
            return stacks[0]

        return None


class SoloStack():
    pass


class BaseStack(StackComponent):

    def __init__(self, name, weight=100, **kwargs):
        """
        The base for all cloudformation stacks

        Args:
            name (str): Name of the stack
            weight (int): Weight is used to order stacks in a list

        Returns:
            void
        """

        super(BaseStack, self).__init__(name)

        self.weight = weight
        self.infra = None
        self.stack_name = ""

        defaults = {
            'template': None
        }

        defaults.update(kwargs)

    def _init_template(self, temp=None):

        if temp is None:
            temp = troposphere.Template(
                "{0} Template".format(
                    self.name))
        return temp

    def get_stack_name(self):

        return "{}{}{}{}".format(
            ''.join([i.capitalize() for i in self.infra.prefix]),
            self.infra.name.capitalize(),
            self.stack_name.capitalize(),
            self.name.capitalize()
        )

    def get_remote_stack_name(self):
        return inflection.dasherize(
            inflection.underscore(
                self.get_stack_name()))

    def get_parameters(self):
        """

        """
        t = self.build_template()

        params = {}

        for k, v in sorted(t.parameters.items()):
            try:
                default = v.Default
            except AttributeError:
                default = None
            params[k] = default

        return params

    def get_outputs(self):

        t = self.build_template()

        op = {}

        for k, v in sorted(t.outputs.items()):
            op[k] = None

        return self.prefix_stack_outputs(op)

    def load_stack_outputs(self, infra):

        op = {}
        cf = infra.boto_session.client('cloudformation')

        try:
            stack = cf.describe_stacks(StackName=self.get_remote_stack_name())
            outputs = stack['Stacks'][0]['Outputs']
            for v in outputs:
                op.update({v['OutputKey']: v['OutputValue']})
        except Exception:
            return False

        op = self.prefix_stack_outputs(op)

        self.infra.add_vars(op)

        return op

    def prefix_stack_outputs(self, vari):

        out = {}
        for k, v in vari.items():
            out.update({"{}{}".format(self.get_stack_name(), k): v})

        return out

    def build_template(self):
        raise NotImplementedError("Must implement method to extend Stack")

    def start_deploy(self, infra):
        """

        """
        template = self.build_template()
        parameters = self.get_parameters()


class DeployStacks(object):

    def __init__(self):
        pass

    def fill_params(self, params, context):

        p = []

        for k, v in params.items():
            val = context.get_var(k)
            if not val:
                val = None
            p.append({
                'ParameterKey': k,
                'ParameterValue': val
            })
        return p

    def deploy_stacks(self, infra):

        stacks = infra.get_stacks()

        for s in stacks:
            template = s.build_template()
            print(s.get_stack_name())
            json = template.to_json()
            stack_name = s.get_stack_name()
            params = s.get_parameters()
            params = self.fill_params(params, s.infra.context)
            print(params)
            print(s.get_remote_stack_name())
            # if  stack_name == "ProdJchJchbucketsS3":
            if stack_name == "ProdJchIamIam__":
            # if stack_name == "ProdJchVpc":
                cf = infra.boto_session.client('cloudformation')
                cf.create_stack(
                # cf.update_stack(
                    StackName=s.get_remote_stack_name(),
                    TemplateBody=json,
                    Parameters=params,
                    Capabilities=[
                        "CAPABILITY_NAMED_IAM",
                        "CAPABILITY_IAM"])



