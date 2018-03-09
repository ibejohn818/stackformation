from stackformation.aws.stacks import BaseStack
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


class SwaggerApiStack(BaseStack):

    def __init__(self, stack_name):

        super(SwaggerApiStack, self).__init__("SwaggerApiStack", 600)
        self.stack_name = stack_name


    
