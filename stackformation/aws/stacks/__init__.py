import logging
import stackformation
from stackformation import utils
import re
import datetime
import pytz
import time
import troposphere
import inflection
import botocore
from colorama import Fore, Style, Back  # noqa

logger = logging.getLogger(__name__)


class StackComponent(object):

    def __init__(self, name):
        self.name = name
        self.prefix = []

    def get_full_name(self):
        return "{}{}".format(
            ''.join([i.capitalize() for i in self.prefix]),
            self.name.capitalize()
        )


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

    """  # noqa

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
        self._stack_info = None
        self.stack_inputs = {}
        self._deploying = False

    def _init_template(self):

        temp = troposphere.Template(
            "{} Template. Stackformation Version: {}".format(
                self.name,
                stackformation.__version__
            ))
        return temp

    def add_template_component(self, var, component):

        if not isinstance(component, TemplateComponent):
            raise Exception("Not instance of template component")

        var = "{}{}".format(self.stack_name, var)

        if not self.template_components.get(var):
            self.template_components.update({var: []})

        self.template_components[var].append(component)

    def render_template_components(self, env, context):

        results = {}

        if len(self.template_components) <= 0:
            return

        for k, v in self.template_components.items():
            for c in v:
                text = c.render()
                t = env.from_string(text)
                if not results.get(k):
                    results[k] = []
                results[k].append(t.render(context.vars))

        for k, v in results.items():
            context.add_vars({k: ''.join(v)})

        return results

    def get_stack_name(self):

        return "{}{}{}{}".format(
            ''.join([utils.ucfirst(i) for i in self.infra.prefix]),
            utils.ucfirst(self.infra.name),
            utils.ucfirst(self.stack_name),
            utils.ucfirst(self.name)
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

        if kwargs.get("skip_prefixing") and kwargs.get(
                "skip_prefixing") is True:
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

    def upload_to_s3(self, infra, name, json_template):

        sts = infra.boto_session.client('sts')

        account_id = sts.get_caller_identity().get('Account')

        bucket_name = 'stackformation-templates-{}'.format(account_id)

        s3 = infra.boto_session.client('s3')

        # make sure the bucket exists
        try:
            s3.head_bucket(Bucket=bucket_name)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == '404':
                s3.create_bucket(
                    Bucket=bucket_name, CreateBucketConfiguration={
                        'LocationConstraint': infra.boto_session.get_conf('region_name')}, )

        # upload the template
        s3.put_object(
            Bucket=bucket_name,
            Key='{}.json'.format(name),
            Body=json_template,
        )

        # this is what CF wants for the url
        uri = 'https://s3.amazonaws.com/{}/{}.json'.format(
            bucket_name, name
        )

        logger.info("Template Uploaded to s3: {}".format(uri))
        return uri

    def start_deploy(self, infra, context):
        """

        """

        present = True

        # check if the stack has been deployed
        cf = infra.boto_session.client("cloudformation")

        try:
            cf.describe_stacks(StackName=self.get_remote_stack_name())
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "ValidationError":
                present = False
            else:
                print(e.response['Error']['Code'])
                print("FATAL ERROR")
                exit(1)

        env = utils.jinja_env(context)

        self._deploying = True
        template = self.build_template()
        self._deploying = False
        parameters = self.get_parameters()
        template_vars = self.render_template_components(env[0], context)  # noqa

        self.before_deploy(context, parameters)

        parameters = self.fill_params(parameters, context)

        dep_kw = {
            'StackName': self.get_remote_stack_name(),
            'Parameters': parameters,
            'Capabilities': ['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM']
        }

        # check template size constraint
        json_template = template.to_json()
        if len(json_template) < 5100:
            dep_kw['TemplateBody'] = json_template
        else:
            dep_kw['TemplateURL'] = self.upload_to_s3(
                infra, self.get_remote_stack_name(), json_template)
        # import json
        # print(json.dumps(dep_kw, indent=True))
        # exit(1)

        try:
            if present:
                cf.update_stack(**dep_kw)
                logger.info(
                    '{}UPDATING STACK:{} {}'.format(
                        utils.colors('b'),
                        Style.RESET_ALL,
                        self.get_stack_name()))
            else:
                cf.create_stack(**dep_kw)
                logger.info(
                    '{}CREATING STACK:{} {}'.format(
                        utils.colors(
                            'b',
                            True),
                        Style.RESET_ALL,
                        self.get_stack_name()))
        except botocore.exceptions.ClientError as e:
            err = e.response['Error']
            if(err['Code'] == "ValidationError" and re.search("No updates", err['Message'])):  # noqa
                return False
            else:
                raise e

        return True

    def before_destroy(self, infra, context):
        pass

    def start_destroy(self, infra, context):

        present = True

        # check if the stack has been deployed
        cf = infra.boto_session.client("cloudformation")

        try:
            cf.describe_stacks(StackName=self.get_remote_stack_name())
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "ValidationError":
                present = False
            else:
                print(e.response['Error']['Code'])
                print("FATAL ERROR")
                exit(1)

        if not present:
            logger.info(
                "{} Has yet to be created...Skipping...".format(
                    self.get_stack_name()))
            return

        kw = {
            'StackName': self.get_remote_stack_name()
        }

        try:
            self.before_destroy(infra, context)
            cf.delete_stack(**kw)
            logger.info(
                '{}DESTROYING STACK:{} {}'.format(
                    utils.colors(
                        'r',
                        True),
                    Style.RESET_ALL,
                    self.get_stack_name()))
        except botocore.exceptions.ClientError as e:
            err = e.response['Error']
            if(err['Code'] == "ValidationError" and re.search("No updates", err['Message'])):  # noqa
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
                info = cf.describe_stacks(
                    StackName=self._deploy_event['stack_name'])
                info = info['Stacks'][0]

                self._deploy_event['stack_id'] = info['StackId']
            except botocore.exceptions.ClientError as e:
                logger.warn(e)
                return

        name = self._deploy_event['stack_name']  # noqa
        ts = self._deploy_event['ts']
        stack_id = self._deploy_event['stack_id']
        token = self._deploy_event['token']

        try:
            info = cf.describe_stacks(StackName=self._deploy_event['stack_id'])
            info = info['Stacks'][0]

            status = info['StackStatus']

            if status.endswith('_FAILED'):
                raise Exception(
                    "STACK DEPLOY FAILED: {}".format(
                        self.get_stack_name()))

            if status.endswith("ROLLBACK_COMPLETE"):
                raise Exception(
                    "STACK ROLLED BACK: {}".format(
                        self.get_stack_name()))

            if status.endswith('_COMPLETE'):
                self._deploying = False
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

                        # term colors
                        color = Fore.MAGENTA
                        rs = e['ResourceStatus']

                        if rs.endswith("COMPLETE"):
                            color = utils.colors('g', True)
                        elif rs.startswith("DELETE"):
                            color = utils.colors('b')
                        elif rs.endswith("FAILED") or \
                                re.match('(ROLLBACK)', rs):
                            color = utils.colors('r')
                        elif rs.endswith('PROGRESS'):
                            color = utils.colors('y')
                        elif re.match('^(CREATE_|UPDATE_)', e['ResourceStatus']):  # noqa
                            color = utils.colors('g')

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

    def review(self, infra):

        review = {
            'dependent_stacks': [],
        }

        review['info'] = self.stack_info()

        # get stack dependencies
        deps = infra.get_dependent_stacks(self)  # noqa

        for k, v in deps.items():
            info = v.stack_info()
            v.load_stack_outputs(self.infra)
            outputs = v.get_outputs()
            params = {}
            if info and info.get('Parameters'):
                for p in info.get('Parameters'):
                    params.update({p['ParameterKey']:
                                   p['ParameterValue']})
            review['dependent_stacks'].append({
                'stack': v,
                'outputs': outputs,
                'stack_info': info,
                'parameters': params
            })

        context = self.infra.context

        env = utils.jinja_env(context)

        review['template'] = self.build_template()
        parameters = self.get_parameters()
        template_vars = self.render_template_components(env[0], context)  # noqa

        self.before_deploy(context, parameters)

        review['parameters'] = self.fill_params(parameters, context)
        review['template_vars'] = template_vars

        return review

    def stack_info(self, force_update=False, return_exception=False):

        if self._stack_info is None or force_update:
            cf = self.infra.boto_session.client('cloudformation')

            try:

                info = cf.describe_stacks(
                    StackName=self.get_remote_stack_name())
                self._stack_info = info['Stacks'][0]
            except botocore.exceptions.ClientError as e:
                if return_exception:
                    return e
                self._stack_info = False

        return self._stack_info

    def build_template(self):
        raise NotImplementedError("Must implement method to extend Stack")


class TemplateComponent(object):

    def render(self, infra, context):
        raise Exception("Must implement get_template method")
