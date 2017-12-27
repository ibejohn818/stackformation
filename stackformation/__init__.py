# -*- coding: utf-8 -*-
import boto3
import troposphere
import inflection
import logging
import botocore
import sys
import re
import datetime
import pytz
import time
from colorama import Fore, Style, Back
import stackformation.utils as utils


"""Top-level package for StackFormation."""

__author__ = """John Hardy"""
__email__ = 'john@johnchardy.com'
__version__ = '0.1.0'

logger = logging.getLogger(__name__)

status_to_color = {
    'CREATE_IN_PROGRESS': Fore.YELLOW,
    'CREATE_FAILED': Fore.RED,
    'CREATE_COMPLETE': Fore.GREEN,
    'ROLLBACK_IN_PROGRESS': Fore.RED,
    'ROLLBACK_FAILED': Fore.RED,
    'ROLLBACK_COMPLETE': Fore.RED,
    'DELETE_IN_PROGRESS': Fore.YELLOW,
    'DELETE_FAILED': Fore.RED,
    'DELETE_COMPLETE': Fore.GREEN,
    'UPDATE_FAILED': Fore.RED,
    'UPDATE_IN_PROGRESS': Fore.YELLOW,
    'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS': Fore.YELLOW,
    'UPDATE_COMPLETE': Fore.GREEN,
    'UPDATE_ROLLBACK_IN_PROGRESS': Fore.RED,
    'UPDATE_ROLLBACK_FAILED': Fore.RED,
    'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS': Fore.YELLOW,
    'UPDATE_ROLLBACK_COMPLETE': Fore.GREEN,
}

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


class StackComponent(object):

    def __init__(self, name):
        self.name = name
        self.prefix = []

    def get_full_name(self):
        return "{}{}".format(
            ''.join([i.capitalize() for i in self.prefix]),
            self.name.capitalize()
        )


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
        self.amis = []

    def add_var(self, name, value):
        return self.context.update({name: value})

    def add_vars(self, inp_vars):
        return self.context.add_vars(inp_vars)

    def check_var(self, name):
        return self.context.check_var(name)

    def get_var(self, name):
        return self.context.get_var(name)

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
        infra.parent_infras.extend(self.parent_infras + [self])
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
        return self.list_stacks()

    def list_stacks(self, **kwargs):

        defaults = {
                'reverse': False
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

        stack.parse_template_components(env[0], Context())


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

    def find_stack(self, clazz):

        stacks = []

        for s in self.stacks:
            if isinstance(s, clazz):
                stacks.append(s)

        if len(stacks) > 0:
            return stacks[0]

        return None

    def add_ami(self, ami):

        ami.prefix = self.prefix
        ami.boto_session = self.boto_session
        self.amis.append(ami)
        return ami


    def list_amis(self):

        amis = []

        for ami in self.amis:
            amis.append(ami)

        for infra in self.sub_infras:
            amis.extend(infra.list_amis())

        return amis

class SoloStack():
    pass


class BaseStack(StackComponent):
    """The base for all cloudformation stacks

    Args:
        name (str): Name of the stack
        weight (int): Weight is used to order stacks in a list

    Attributes:
        weight (int): represents stack order in a list
        infra (:obj:`stackformation.Infra`): Infra obj the stack belongs to
        stack_name (str): Name of the stack instance
        _deploy_event (dict): stub to store previous event during deploying() lookups
        template_components (dict): template components added to stack instance

    """

    def __init__(self, name, weight=100, **kwargs):

        super(BaseStack, self).__init__(name)

        self.weight = weight
        self.infra = None
        self.stack_name = ""
        self._deploy_event = None

        defaults = {
            'template': None
        }

        defaults.update(kwargs)
        self.template_components = {}

    def _init_template(self, temp=None):

        if temp is None:
            temp = troposphere.Template(
                "{0} Template".format(
                    self.name))
        return temp

    def add_template_component(self, var, component):

        if not isinstance(component, TemplateComponent):
            raise Exception("Not instance of template component")

        var = "{}{}".format(self.stack_name, var)

        if not self.template_components.get(var):
            self.template_components.update({var: []})

        self.template_components[var].append(component)

    def parse_template_components(self, env, context):

        results = {}

        if len(self.template_components) <= 0:
            results

        for k, v in self.template_components.items():
            for c in v:
                text = c.text()
                t = env.from_string(text)
                if not results.get(k):
                    results[k] = []
                results[k].append(t.render(context.vars))

        for k, v in results.items():
            context.add_vars({k: ''.join(v)})

        return results


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

    def get_outputs(self, **kwargs):

        t = self.build_template()

        op = {}

        for k, v in sorted(t.outputs.items()):
            op[k] = None

        if kwargs.get("skip_prefixing") and  kwargs.get("skip_prefixing") is True:
            return op

        return self.prefix_stack_vars(op)

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

        op = self.prefix_stack_vars(op)

        infra.add_vars(op)

        return op

    def prefix_stack_vars(self, vari):

        out = {}
        for k, v in vari.items():
            out.update({"{}{}".format(self.get_stack_name(), k): v})

        return out


    def fill_params(self, params, context):

        p = []

        for k, v in params.items():
            val = context.get_var(k)
            if not val and v:
                val = v
            if not val:
                val = None
            p.append({
                'ParameterKey': k,
                'ParameterValue': val
            })
        return p

    def before_deploy(self, infra, context):
        pass

    def start_deploy(self, infra, context):
        """

        """

        present = True

        # check if the stack has been deployed
        cf = infra.boto_session.client("cloudformation")

        try:
            chk = cf.describe_stacks(StackName=self.get_remote_stack_name())
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "ValidationError":
                present = False
            else:
                print(e.response['Error']['Code'])
                print("FATAL ERROR")
                exit(1)

        env = utils.jinja_env(context)

        template = self.build_template()
        parameters = self.get_parameters()
        template_vars = self.parse_template_components(env[0], context)

        self.before_deploy(context, parameters)

        parameters = self.fill_params(parameters, context)

        dep_kw = {
                'StackName': self.get_remote_stack_name(),
                'TemplateBody': template.to_json(),
                'Parameters': parameters,
                'Capabilities':['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM']
                }

        try:
            if present:
                res = cf.update_stack(**dep_kw)
                logger.info('UPDATING STACK: {}'.format(self.get_stack_name()))
            else:
                res = cf.create_stack(**dep_kw)
                logger.info('CREATING STACK: {}'.format(self.get_stack_name()))
        except botocore.exceptions.ClientError as e:
            err = e.response['Error']
            if(err['Code'] == "ValidationError" and re.search("No updates", err['Message'])):
                return False
            else:
                raise e

        return True

    def start_destroy(self, infra, context):

        present = True

        # check if the stack has been deployed
        cf = infra.boto_session.client("cloudformation")

        try:
            chk = cf.describe_stacks(StackName=self.get_remote_stack_name())
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "ValidationError":
                present = False
            else:
                print(e.response['Error']['Code'])
                print("FATAL ERROR")
                exit(1)

        if not present:
            logger.info("{} Has yet to be created...Skipping...".format(self.get_stack_name()))
            return

        kw = {
                'StackName': self.get_remote_stack_name()
            }

        try:
                res = cf.delete_stack(**kw)
                logger.info('DESTROYING STACK: {}'.format(self.get_stack_name()))
        except botocore.exceptions.ClientError as e:
            err = e.response['Error']
            if(err['Code'] == "ValidationError" and re.search("No updates", err['Message'])):
                return False
            else:
                raise e

        return True


    def deploying(self, infra):

        cf = infra.boto_session.client("cloudformation")

        if self._deploy_event is None:
            self._deploy_event = {
                    'stack_name': self.get_remote_stack_name(),
                    'ts': datetime.datetime.now(pytz.utc),
                    'token': '',
                    'stack_id': ''
                    }
            try:
                info = cf.describe_stacks(StackName=self._deploy_event['stack_name'])
                info = info['Stacks'][0]

                self._deploy_event['stack_id'] = info['StackId']
            except botocore.exceptions.ClientError as e:
                logger.warn(e)
                return

        name = self._deploy_event['stack_name']
        ts = self._deploy_event['ts']
        stack_id = self._deploy_event['stack_id']
        token = self._deploy_event['token']

        try:
            info = cf.describe_stacks(StackName=self._deploy_event['stack_id'])
            info = info['Stacks'][0]

            status = info['StackStatus']


            if status.endswith('_FAILED'):
                raise Exception("STACK DEPLOY FAILED: {}".format(self.get_stack_name()))

            if status.endswith("ROLLBACK_COMPLETE"):
                raise Exception("STACK ROLLED BACK: {}".format(self.get_stack_name()))

            if status.endswith('_COMPLETE'):
                return False
            else:
                time.sleep(3)

                if len(token) > 0:
                    event = cf.describe_stack_events(StackName=stack_id,
                            NextToken=token)
                else:
                    event = cf.describe_stack_events(StackName=stack_id)

                event['StackEvents'].sort(key=lambda e: e['Timestamp'])

                for e in event['StackEvents']:
                    if e['Timestamp'] > ts:

                        reason = ""
                        if 'ResourceStatusReason' in e:
                            reason = e['ResourceStatusReason']

                        # logger style
                        if e['ResourceStatus'] in status_to_color:
                            color = status_to_color[
                                e['ResourceStatus']
                            ]
                        else:
                            color = Fore.MAGENTA

                        logger.info("{} {} ({}): [{}]: {}{}{}{}".format(
                            color,
                            e['LogicalResourceId'],
                            e['ResourceType'],
                            e['ResourceStatus'],
                            Style.RESET_ALL,
                            Style.BRIGHT,
                            reason,
                            Style.RESET_ALL
                            ))

                        ts = e['Timestamp']
                self._deploy_event['ts'] = ts
                if 'NextToken' in event:
                    self._deploy_event['token'] = event['NextToken']
        except botocore.exceptions.ClientError as e:
            logger.warn(e)
            return

        return True


    def find_class_in_list(self, ls, clazz, name=None):

        results = []

        for r in ls:
            if clazz is r.__class__:
                results.append(r)

        if len(results) == 1 and (name is None or name == results[0].name):
            return results[0]

        if len(results) > 1 and name is not None:
            for r in results:
                if r.name == name:
                    return r

        return None

    # def get_dependent_stacks(self, infra):

    def build_template(self):
        raise NotImplementedError("Must implement method to extend Stack")


class TemplateComponent(object):

    def text(self, infra, context):
        raise Exception("Must implement get_template method")

class PackerImage(object):

    def __init__(self, name):

        self.name = name
        self.roles = {}
        self.os_type = None
        self.boto_session = None
        self.stack = None

    def add_role(self, role_name, vars = {}):
        """Add ansible role to image

        Args:
            role_name (str): the name of the role
            vars (dict}: dict of role variables

        """
        self.roles.update({role_name: vars})

    def del_role(self, role_name):
        if role_name in self.roles:
            del self.roles[role_name]

    def build(self):
        """Abstract method to trigger the build
        """
        raise Exception("Need to implement build()")

    def describe(self):
        """Describe the image build
        """
        raise Exception("Must implement describe()")
