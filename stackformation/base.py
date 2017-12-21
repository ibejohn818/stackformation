import boto3
import troposphere


class BotoSession():

    def __init__(self, **kwargs):

        self.conf = {
                'region_name': 'us-west-2'
        }

        if kwargs.get('aws_access_key_id'):
            self.conf['aws_access_key_id'] = kwargs.get('aws_access_key_id')

        if kwargs.get('aws_secret_access_key'):
            self.conf['aws_secret_access_key'] = kwargs.get('aws_secret_access_key')

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
        if not key in self.conf:
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
        self.prefix = ''


    def get_full_name(self):
        return "{}{}".format(
                self.prefix.capitalize(),
                self.name.captitalize()
                )

class Infra(object):

    def __init__(self, name, boto_session=None):

        self.name = name
        self.prefix = ''
        self.stacks = []
        self.boto_session = boto_session
        self.sub_infras = []
        self.input_vars = {}
        self.output_vars = {}
        self.context = Context()


    def add_input_var(self, name, value):

        return self.context.update({name: value})


    def add_input_vars(self, inp_vars):

        return self.context.add_input_vars.update(inp_vars)

    def get_input_var_name(self, name):
        pass

    def create_sub_infra(self, prefix):
        """

        """

        infra = Infra(self.name)
        infra.prefix = prefix
        self.sub_infras.append(infra)

        return infra

    def add_stack(self, stack):

        if not isinstance(stack, (BaseStack)):
            raise ValueError("Error adding stack. Invalid Type!")

        if stack.solo:
            for stk in self.stacks:
                if isinstance(stack, type(stk)):
                    raise Exception("Solo Stack Error: {} type already added".format(type(stack).__name__))

        self.stacks.append(stack)
        stack.prefix = self.prefix
        stack.infra = self

        return stack


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
        self.solo = False
        self.infra = None
        self.stack_name = ""

        defaults = {
            'template': None
        }

        defaults.update(kwargs)

        self.template = self.init_template(
            defaults['template'] if isinstance(
                defaults['template'],
                (troposphere.Template)) else None)

    def init_template(self, temp=None):

        if temp is None:
            temp = troposphere.Template(
                "{0} Template".format(
                    self.name))
        return temp


    def get_stack_name(self):

        return "{}{}{}{}".format(
                self.prefix.capitalize(),
                self.infra.name.capitalize(),
                self.stack_name.capitalize(),
                self.name.capitalize()
                )

    def get_template_params(self):
        pass

    def build_template(self, infra):
        raise NotImplementedError("Must implement method to extend Stack")


class DeployStacks(object):

    def  __init__(self):
        pass


    @staticmethod
    def deploy_stacks(infra):

        stacks = []

        infras = [infra] + infra.sub_infras

        for i in infras:
            stacks.extend(i.stacks)

        for s in stacks:
            json = s.build_template().to_json()
            print(json)
