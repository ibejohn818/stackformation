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
        self.cors_enabled = False
        self.cors_rules = []
        self.policies = []
        self.lifecycle_rules = []

    def add_expiration_rule(self, path, days=30, enabled=True):
        lcr = s3.LifecycleRule(
                ExpirationInDays=days,
                Prefix=path,
                Status=('Enabled' if enabled else 'Disabled')
                )
        self.lifecycle_rules.append(lcr)

    def add_cors_rule(self, name, headers, methods, origins, age, **kwargs):

        rule = s3.CorsRules(
            AllowedHeaders=headers,
            AllowedMethods=methods,
            AllowedOrigins=origins,
            MaxAge=age,
            Id=name
        )
        self.cors_rules.append(rule)

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

    def output_website_url(self):
        return "{}{}WebsiteUrl".format(
            self.stack.get_stack_name(),
            self.name
        )

    def _build_template(self, template):
        raise Exception("_build_template must be implemented!")


class S3Bucket(BaseS3Bucket):

    def __init__(self, name, **kwargs):

        super(S3Bucket, self).__init__(name)
        self.website_mode = kwargs.get('website_mode', False)
        self.website_config = {
            'IndexDocument': 'index.html',
            'ErrorDocument': 'error.html'
        }

    def _build_template(self, template):

        t = template
        s3b = t.add_resource(s3.Bucket(
            self.name
        ))

        if self.public_read:
            s3b.AccessControl = s3.PublicRead
            t.add_resource(s3.BucketPolicy(
                '{}BucketPolicy'.format(self.name),
                Bucket=Ref(s3b),
                PolicyDocument= {
                    "Statement":[{
                        "Action":["s3:GetObject"],
                        "Effect":"Allow",
                        "Resource": Join('', ["arn:aws:s3:::", Ref(s3b), "/*"]),
                        "Principal":"*"
                        }]}
                ))

        versioning = "Suspended"

        if self.versioning:
            versioning = "Enabled"

        s3b.VersioningConfiguration = s3.VersioningConfiguration(
            Status=versioning
        )

        if self.website_mode:
            s3b.WebsiteConfiguration = s3.WebsiteConfiguration(
                **self.website_config)

        if self.cors_enabled is True \
                and len(self.cors_rules) <= 0:
            self.add_cors_rule("CorsAll", ['*'], ['GET'], ['*'], 3000)

        if len(self.cors_rules) > 0:
            cors = s3.CorsConfiguration(
                CorsRules=self.cors_rules
            )
            s3b.CorsConfiguration = cors

        if len(self.lifecycle_rules) > 0:
            s3b.LifecycleConfiguration=s3.LifecycleConfiguration(
                    Rules=[]
            )
            for lcr in self.lifecycle_rules:
                s3b.LifecycleConfiguration.Rules.append(lcr)



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
            ),
            Output(
                '{}WebsiteUrl'.format(self.name),
                Value=GetAtt(s3b, 'WebsiteURL')
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
