# -*- coding: utf-8 -*-
import boto3
import logging
from stackformation.aws.stacks import (BaseStack, SoloStack)
import stackformation.utils as utils


"""Top-level package for StackFormation."""

__author__ = """John Hardy"""
__email__ = 'john@johnchardy.com'
__version__ = '0.2.35'

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
        conf = {}
        return self.session.client(client, **conf)

    def resource(self, service):
        return self.session.resource(service)


class Context(object):
    """Container of variables to pass between Infra's and Stack's

    Attributes:
        vars (dict): containers of variables
    """

    def __init__(self):
        self.vars = {}

    def get_var(self, name):
        """Return variable

        Args:
            name (str): Name of the variable to return

        Returns:
            var (mixed): Variable stored under name

        """

        if not self.vars.get(name):
            return False
        return self.vars.get(name)

    def add_vars(self, new):
        """Add vars to the context

        Args:
            new (dict): dict of variables to add to the context

        """

        self.vars.update(new)

    def check_var(self, name):
        return self.vars.get(name)


class Infra(object):

    def __init__(self, name, boto_session=None):

        self.name = name
        self.prefix = []
        self.stacks = []
        self.boto_session = boto_session
        self.sub_infras = []
        self.parent_infras = []
        self.input_vars = {}
        self.output_vars = {}
        self.context = Context()
        self.images = []

    def add_var(self, name, value):
        return self.context.vars.update({name: value})

    def add_vars(self, inp_vars):
        return self.context.add_vars(inp_vars)

    def check_var(self, name):
        return self.context.check_var(name)

    def get_var(self, name):
        return self.context.get_var(name)

    def add_image(self, image):

        image.prefix = self.prefix
        image.boto_session = self.boto_session
        self.images.append(image)
        return image

    def list_images(self):

        images = []

        for image in self.images:
            images.append(image)

        for infra in self.sub_infras:
            images.extend(infra.list_images())

        return images

    def create_sub_infra(self, prefix):
        """

        """

        infra = Infra(self.name)
        infra.prefix.extend(self.prefix + [prefix])
        infra.boto_session = self.boto_session
        infra.parent_infras.extend(self.parent_infras + [self])
        self.sub_infras.append(infra)

        return infra

    def has_stack(self, stack):
        if not stack.infra:
            return False
        sn = stack.get_stack_name()
        for s in self.stacks:
            if s.get_stack_name() == sn:
                return True
        return False

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
        return self.list_stacks()

    def list_stacks(self, **kwargs):

        defaults = {
            'reverse': False,
        }

        defaults.update(kwargs)

        stacks = []
        for stack in self.stacks:
            stacks.append(stack)

        for infra in self.sub_infras:
            stacks.extend(infra.list_stacks())

        def _cmp(x):
            return x.weight

        stacks = sorted(stacks, key=_cmp, reverse=defaults.get("reverse"))

        return stacks

    def get_dependent_stacks(self, stack):

        results = {}

        params = list(stack.get_parameters().keys())

        env = utils.jinja_env({}, True)

        stack.render_template_components(env[0], Context())

        params += env[1]

        stacks = self.list_stacks()

        for stk in stacks:
            ops = stk.get_outputs().keys()
            for o in ops:
                if o in params:
                    results.update({stk.get_stack_name(): stk})

        return results

    def gather_contexts(self):

        c = []

        c.append(self.context)

        for infra in self.sub_infras:
            c.extend(infra.gather_contexts())

        return c

    def find_stack(self, clazz, name=None):

        stacks = []

        for s in self.stacks:
            if isinstance(s, clazz):
                if name is not None:
                    if name == s.stack_name:
                        stacks.append(s)
                else:
                    stacks.append(s)

        if len(stacks) > 0:
            return stacks[0]

        return None

    def get_prefix(self):
        return ''.join([
            utils.ucfirst(i)
            for i in self.prefix
        ])

    def get_bucket_name(self):
        """Return the bucket name for the infra
        """
        pass

    def ensure_bucket(self):
        """Make sure the infra's bucket is created
        """
        pass

    def destroy_bucket(self):
        """Remove infra bucket
        """
        pass
