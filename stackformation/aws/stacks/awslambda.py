from stackformation.aws.stacks import BaseStack
from troposphere import (sns, iam, awslambda)
import awacs.kms
import awacs.sns
import awacs.logs
from awacs import aws
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export, Base64,
)
import os
import zipfile
import inflection
import logging
import shutil
import tempfile
import base64
import hashlib
import time


logger = logging.getLogger(__name__)

class BaseLambda(BaseStack):

    def __init__(self, name, **kwargs):

        super(BaseLambda, self).__init__(name, 500)
        self.zip_path = kwargs.get('zip_path', '')
        self.zip_uploaded = False
        self.zip_name = kwargs.get('zip_name', 'Code.zip')
        self._s3 = None
        self.tmp_folder = kwargs.get('tmp_folder', '_code')
        self.s3_bucket = kwargs.get('s3_bucket', None)
        self.code_hash = None
        self.s3_hash = False
        self.s3_version = False
        self.uploaded = False


    def _bucket_name(self):
        name = self.infra.get_var(self.s3_bucket.output_bucket_name())
        return name

    def _code_hash(self):
        if not self.code_hash:
            with open(os.path.join(self.zip_path, self.zip_name), 'rb') as f:
                cs = hashlib.sha256()
                cs.update(f.read())
                f.close()
                sha = cs.digest()
                code_sum = base64.b64encode(sha).decode('utf-8')
                self.code_hash = code_sum

        return self.code_hash

    def _s3_code_hash(self):
        if self.s3_hash and self.s3_version:
            return self.s3_hash

        if not self._bucket_name():
            return False

        try:
            obj = self.s3().head_object(
                Bucket=self._bucket_name(),
                Key=self.zip_name
                )
            self.s3_version = obj['VersionId']
            self.s3_hash = obj['Metadata']['code256sum']
            return True

        except Exception as e:
            return False, False


    def _upload_zip(self):
        try:
            code_hash = self._code_hash()
            with open(os.path.join(self.zip_path, self.zip_name), 'rb') as f:
                logger.info("Uploading zip...")
                self.s3().put_object(
                    Bucket=self._bucket_name(),
                    Key=self.zip_name,
                    Body=f,
                    Metadata={
                        'code256sum': code_hash
                    }
                    )
                self.s3_hash = False
                self.s3_version = False
                self.uploaded = True
        except Exception as e:
            raise e

    def _determine_code_versions(self):
        self._s3_code_hash()
        if not self.s3_hash or \
                self._code_hash() != self.s3_hash:
            self._upload_zip()
            self._s3_code_hash()

    def _prune_uploads(self):
        pass


    def s3(self):
        if not self._s3:
            self._s3 = self.infra.boto_session.client('s3')
        return self._s3


class LambdaStack(BaseLambda):
    """Lambda function stack

    Args:
        name (str): name of the stack
        ...
        **role (str): IAM Role of the function
        **s3_bucket (:obj:`stackformation.aws.stacks.s3.S3Bucket`): S3 Bucket where code will be linked to
        ...

    Returns:
        void
    """

    def __init__(self, name, **kwargs):

        super(LambdaStack, self).__init__("LambdaStack", **kwargs)

        self.stack_name = name
        self.vars = {}
        self.memory = 256
        self.handler = "index.handler"
        self.runtime = kwargs.get('runtime', 'python2.7')
        self.aliaes = []
        self.role = kwargs.get('role', None)
        self.s3_bucket = kwargs.get('s3_bucket', None)
        self.s3_key = kwargs.get('s3_key', None)

    def add_alias(self, alias):
        self.append(alias)

    def build_template(self):

        t = self._init_template()

        role_param = t.add_parameter(Parameter(
            self.role.output_role_arn(),
            Type='String'
        ))
        bucket_ref = t.add_parameter(Parameter(
            self.s3_bucket.output_bucket_name(),
            Type='String'
        ))

        if self._deploying:
            if not self.uploaded and self._bucket_name():
                self._determine_code_versions()
                logger.info("S3 Key: {}".format(self.zip_name))

        func = t.add_resource(awslambda.Function(
            '{}Function'.format(self.get_stack_name()),
            FunctionName=self.get_stack_name(),
            Handler=self.handler,
            MemorySize=self.memory,
            Runtime=self.runtime,
            Role=Ref(role_param),
            Environment=awslambda.Environment(
                Variables=self.vars
            ),
            Code=awslambda.Code(
                S3Bucket=Ref(bucket_ref),
                S3Key=self.zip_name
            )
        ))

        if self.s3_version:
            func.Code.S3ObjectVersion = self.s3_version

        t.add_output([
            Output(
                'FunctionName',
                Value=Ref(func)
            ),
            Output(
                'FunctionArn',
                Value=GetAtt(func, "Arn")
            )
        ])

        return t

    def output_func_name(self):
        return '{}FunctionName'.format(self.get_stack_name())

    def output_func_arn(self):
        return '{}FunctionArn'.format(self.get_stack_name())
