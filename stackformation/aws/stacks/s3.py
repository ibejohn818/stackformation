from stackformation.aws.stacks import BaseStack
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)
import troposphere.s3 as s3
import logging

logger = logging.getLogger(__name__)

class BaseS3Bucket(object):

    def __init__(self, name):

        self.name = name
        self.policies = []
        self.config = {}
        self.versioning = False
        self.public_read = False
        self.stack = None

    def set_public_read(self, val):
        self.public_read = val

    def output_bucket_name(self):
        return "{}{}BucketName".format(
            self.stack.get_stack_name(),
            self.name
        )

    def output_bucket_url(self):
        return "{}{}BucketUrl".format(
            self.stack.get_stack_name(),
            self.name
        )

    def _build_template(self, template):
        raise Exception("_build_template must be implemented!")


class S3Bucket(BaseS3Bucket):

    def __init__(self, name):

        super(S3Bucket, self).__init__(name)

    def _build_template(self, template):

        t = template
        s3b = t.add_resource(s3.Bucket(
            self.name
        ))

        if self.public_read:
            s3b.AccessControl = s3.PublicRead

        versioning = "Suspended"

        if self.versioning:
            versioning = "Enabled"

        s3b.VersioningConfiguration = s3.VersioningConfiguration(
            Status=versioning
        )

        t.add_output([
            Output(
                "{}BucketName".format(self.name),
                Value=Ref(s3b),
                Description="{} Bucket Name".format(self.name)
            ),
            Output(
                "{}BucketUrl".format(self.name),
                Value=GetAtt(s3b, "DomainName"),
                Description="{} Bucket Name".format(self.name)
            )
        ])

        return s3b

class LambdaCodeBucket(S3Bucket):

    def __init__(self, name):
        super(LambdaCodeBucket, self).__init__(name)
        self.versioning = True


class S3Stack(BaseStack):

    def __init__(self, name="Buckets"):

        super(S3Stack, self).__init__("S3", 10)

        self.stack_name = name
        self.buckets = []

    def add_bucket(self, bucket):
        bucket.stack = self
        self.buckets.append(bucket)
        return bucket

    def find_bucket(self, clazz, name=None):

        return self.find_class_in_list(self.buckets, clazz, name)

    def before_destroy(self, infra, ctx):
        self.load_stack_outputs(infra)
        # iterate all buckets and delete all objects
        s3 = infra.boto_session.resource('s3')
        for bkt in self.buckets:
            bucket_name = infra.get_var(bkt.output_bucket_name())
            logger.info("Clearing bucket: {}".format(bucket_name))
            try:
                bucket = s3.Bucket(bucket_name)
                bucket.objects.all().delete()
            except Exception as e:
                logger.info(str(e))

    def build_template(self):

        t = self._init_template()
        for b in self.buckets:
            b._build_template(t)
        return t
