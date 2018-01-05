from stackformation.aws.stacks import BaseStack
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)
import troposphere.s3 as s3


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

    def build_template(self):

        t = self._init_template()
        for b in self.buckets:
            b._build_template(t)
        return t
