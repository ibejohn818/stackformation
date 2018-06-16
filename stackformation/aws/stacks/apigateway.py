from stackformation.aws.stacks import BaseStack
from stackformation.aws.stacks import TemplateComponent
from stackformation.aws import Ami
import logging
from colorama import Fore, Style, Back  # noqa
from troposphere import apigateway, awslambda
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export, Base64
)
import json
from stackformation.utils import md5str


class SwaggerJsonTemplate(TemplateComponent):

    def __init__(self, template):
        self.name = 'SwaggerTemplate'
        self.template = template

    def render(self):
        return self.template


class SwaggerApiStack(BaseStack):

    def __init__(self, stack_name):

        super(SwaggerApiStack, self).__init__("SwaggerApiStack", 600)
        self.stack_name = stack_name
        self.lambda_funcs = []
        self.ep_type = 'REGIONAL'
        self.template_str = ''
        self.stages = []

    def add_stage(self, stage):
        self.stages.append(stage)

    def add_swagger(self, template):
        self.template_str = template
        self.add_template_component('Swagger', SwaggerJsonTemplate(template))

    def add_lambda_func(self, func):
        self.lambda_funcs.append(func)

    def before_deploy(self, context, parameters):
        swag_key = '{}Swagger'.format(self.stack_name)

        if context.check_var(swag_key):

            swag_data = context.get_var(swag_key)
            n = 4096

            swag_list = [swag_data[i:i + n]
                         for i in range(0, len(swag_data), n)]

            for k, v in enumerate(swag_list):
                varname = "{}{}".format(swag_key, k)
                context.add_vars({varname: v})

    def build_template(self):

        t = self._init_template()

        swag_data = []
        for i in range(0, 4):
            swag_data.append(
                Ref(t.add_parameter(Parameter(
                    '{}Swagger{}'.format(self.stack_name, i),
                    Type='String',
                    Default=' ',
                    Description='Swagger Data #{}'.format(i)
                )))
            )

        api = t.add_resource(apigateway.RestApi(
            '{}RestApi'.format(self.stack_name),
            Body=Join('', swag_data),
            EndpointConfiguration=apigateway.EndpointConfiguration(
                Types=[self.ep_type]
            )
        ))

        if len(self.stages) <= 0:
            self.add_stage('prod')

        for stage in self.stages:
            deployment = t.add_resource(
                apigateway.Deployment(
                    '{}{}{}Deployment'.format(
                        self.stack_name, md5str(
                            self.template_str), stage), RestApiId=Ref(api), StageName=md5str(
                        self.template_str + stage), ))
            stage_res = t.add_resource(apigateway.Stage(
                '{}{}Stage'.format(self.stack_name, stage),
                StageName=stage,
                Description='{}{}'.format(self.stack_name, stage),
                RestApiId=Ref(api),
                DeploymentId=Ref(deployment),
            ))

        for func in self.lambda_funcs:
            func_param = t.add_parameter(Parameter(
                func.output_func_arn(),
                Type='String',
                Description='Function to grant invoke access to'
            ))

            t.add_resource(awslambda.Permission(
                'SwagFuncPerm{}'.format(func.output_func_name()),
                SourceArn=Join("", [
                    'arn:aws:execute-api:',
                    Ref('AWS::Region'),
                    ':',
                    Ref('AWS::AccountId'),
                    ':',
                    Ref(api),
                    "/*/*/*"
                ]),
                FunctionName=Ref(func_param),
                Action='lambda:invokeFunction',
                Principal='apigateway.amazonaws.com',
                DependsOn="{}RestApi".format(self.stack_name)
            ))

        t.add_output([
            Output(
                'ApiId'.format(self.stack_name),
                Description='Root id for API',
                Value=Ref(api)
            ),
            Output(
                'ApiUrl'.format(self.stack_name),
                Value=Join('', [
                    Ref(api),
                    '.execute-api.',
                    Ref('AWS::Region'),
                    '.amazonaws.com'
                ])
            )
        ])

        return t

    def output_id(self):
        return "{}ApiId".format(self.get_stack_name())

    def output_url(self):
        return "{}ApiUrl".format(self.get_stack_name())


class CustomDomainStack(BaseStack):

    def __init__(self, name, apigw):
        super(CustomDomainStack, self).__init__("APIGWDomain", 700)
        self.stack_name = name
        self.api_stack = apigw
        self.domain_name = None
        self.region_ssl_arn = None
        self.stage = None
        self.base_path = None

    def add_stage(self, stage):
        self.stage = stage

    def add_domain(self, domain):
        self.domain_name = domain

    def add_base_path(self, path):
        self.base_path = path

    def add_region_ssl_arn(self, arn):
        self.region_ssl_arn = arn

    def build_template(self):

        t = self._init_template()

        api_param = t.add_parameter(Parameter(
            '{}ApiId'.format(self.api_stack.get_stack_name()),
            Type='String'
        ))

        domain = t.add_resource(apigateway.DomainName(
            '{}Domain'.format(self.stack_name),
            DomainName=self.domain_name,
            EndpointConfiguration=apigateway.EndpointConfiguration(
                Types=[self.api_stack.ep_type]
            )
        ))

        # if self.certificate_arn is not None:
        # domain.CertificateArn = self.certificate_arn

        if self.region_ssl_arn is not None:
            domain.RegionalCertificateArn = self.region_ssl_arn

        mapping = t.add_resource(apigateway.BasePathMapping(
            '{}Mapping'.format(self.stack_name),
            DomainName=Ref(domain),
            RestApiId=Ref(api_param)
        ))

        if self.base_path is not None:
            mapping.BasePath = self.base_path

        if self.stage is not None:
            mapping.Stage = self.stage

        t.add_output([
            Output(
                'DomainId',
                Value=Ref(domain),
                Description="API Gateway Custom Domain ID"
            )
        ])

        return t
