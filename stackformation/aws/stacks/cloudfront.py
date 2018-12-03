from stackformation.aws.stacks import BaseStack
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)
import troposphere.cloudfront as cloudfront
from stackformation.aws.stacks import (s3, apigateway, elb, ec2) # noqa
from troposphere.cloudfront import (Cookies, ForwardedValues)
from stackformation.utils import ensure_param

DEF_COOKIE = Cookies(
    Forward='all'
)


DEF_METHODS = ['HEAD', 'PUT', 'POST', 'DELETE', 'GET', 'OPTIONS', 'PATCH']


class Behavior(object):

    def __init__(self, **kwargs):
        self.default = False
        self.allowed_methods = kwargs.get('methods', DEF_METHODS)
        self.cache_methods = kwargs.get('cache_methods', ['GET', 'HEAD'])
        self.compress = kwargs.get('compress', True)
        self.default_ttl = kwargs.get('default_ttl', 0)
        self.max_ttl = kwargs.get('max_ttl', 0)
        self.min_ttl = kwargs.get('min_ttl', 0)
        self.pattern = kwargs.get('pattern', None)
        self.streaming = False
        self.origin_id = None
        self.default = False
        self.forward_cookies = 'all'
        self.cookie_list = []
        self.forward_querystring = True
        self.querystring_list = []
        self.force_https = kwargs.get('force_https', False)
        self.https = False
        self.headers = kwargs.get('headers', ['*'])

    @classmethod
    def gen_static_assets(cls, **kwargs):
        defaults = {
            'headers': []
        }
        defaults.update(kwargs)
        paths = ["*.jpg", "*.jpeg", "*.gif", "*.png", "*.js", "*.css"]
        b = []
        for path in paths:
            defaults['pattern'] = path
            tmp = Behavior(**defaults)
            b.append(tmp)
        return b

    def set_origin(self, origin):
        self.origin_id = origin.get_id()

    def build(self):

        fw = ForwardedValues(
            QueryString=self.forward_querystring
        )

        if self.forward_cookies == 'all':
            fw.Cookies = Cookies(
                Forward='all'
            )
        else:
            fw.Cookies = Cookies(
                Forward='whitelist',
                WhitelistNames=self.cookie_list
            )

        if len(self.querystring_list) > 0:
            fw.QueryStringCacheKeys = self.querystring_list

        if self.headers:
            fw.Headers = self.headers

        kw = {
            'AllowedMethods': self.allowed_methods,
            'CachedMethods': self.cache_methods,
            'Compress': self.compress,

            'ForwardedValues': fw,
            'SmoothStreaming': self.streaming,
            'TargetOriginId': self.origin_id,
        }

        if self.default_ttl is not None:
            kw['DefaultTTL']= self.default_ttl
        if self.max_ttl is not None:
            kw['MaxTTL']= self.max_ttl
        if self.min_ttl is not None:
            kw['MinTTL']= self.min_ttl

        if self.force_https:
            kw['ViewerProtocolPolicy'] = 'redirect-to-https'
        elif self.https:
            kw['ViewerProtocolPolicy'] = 'https-only'
        else:
            kw['ViewerProtocolPolicy'] = 'allow-all'

        if self.default:
            b = cloudfront.DefaultCacheBehavior(**kw)
        else:
            kw['PathPattern'] = self.pattern
            b = cloudfront.CacheBehavior(**kw)
        return b


class Origin(object):

    def __init__(self, name, origin, **kwargs):
        self.name = name
        self.origin = origin
        self.path = kwargs.get('path', '')
        self.origin_timeout = kwargs.get('timeout', 30)
        self.origin_proto = kwargs.get('origin_proto', 'match-viewer')
        self.ssl_protocols = ['TLSv1.1', 'TLSv1.2']

    def get_id(self):
        return self.name

    def build(self, t):

        o = cloudfront.Origin(
            OriginPath=self.path,
            Id=self.get_id())

        if isinstance(self.origin, s3.S3Bucket):
            domain_ref = t.add_parameter(Parameter(
                self.origin.output_bucket_url(),
                Type='String'
            ))
        elif isinstance(self.origin, apigateway.SwaggerApiStack):
            domain_ref = ensure_param(t, self.origin.output_url())
        else:
            domain_ref = t.add_parameter(Parameter(
                'Input{}Origin'.format(self.name),
                Type='String'
            ))

        co = cloudfront.CustomOrigin(
            OriginReadTimeout=self.origin_timeout,
            OriginProtocolPolicy=self.origin_proto,
            OriginSSLProtocols=self.ssl_protocols
            )

        o.CustomOriginConfig = co
        o.DomainName = Ref(domain_ref)

        return o


class CloudfrontStack(BaseStack):

    def __init__(self, name, **kwargs):
        super(CloudfrontStack, self).__init__('Cloudfront', 700)
        self.stack_name = name

        self.behaviors = []
        self.origins = []
        self.default_behavior = None
        self.domains = []
        self.index_file = "index.html"
        self.errors = []
        self.acm_ssl_arn = kwargs.get('acm_ssl_arn', None)
        self.iam_ssl_id = kwargs.get('iam_ssl_id', None)

    def add_errors(self, **kwargs):
        err = cloudfront.CustomErrorResponse()

        err.ErrorCachingMinTTL = kwargs.get('ttl', 300)

        if kwargs.get('ErrorCode'):
            err.ErrorCode = kwargs.get('ErrorCode')

        if kwargs.get('ResponseCode'):
            err.ResponseCode = kwargs.get('ResponseCode')

        if kwargs.get('ResponsePagePath'):
            err.ResponsePagePath = kwargs.get('ResponsePagePath')

        self.errors.append(err)

    def add_domain(self, domain):
        self.domains.append(domain)

    def add_origin(self, origin):
        self.origins.append(origin)

    def add_behavior(self, behavior, default=False):
        if default:
            behavior.default = True
            self.default_behavior = behavior.build()
        else:
            self.behaviors.append(behavior.build())

    def build_template(self):

        t = self._init_template()

        dist = t.add_resource(cloudfront.Distribution(
            '{}Cloudfront'.format(self.stack_name),
            DistributionConfig=cloudfront.DistributionConfig(
                Aliases=self.domains,
                DefaultRootObject=self.index_file,
                DefaultCacheBehavior=self.default_behavior,
                Enabled=True,
                Origins=[],
                CacheBehaviors=self.behaviors
            )
        ))

        if self.acm_ssl_arn:
            dist.DistributionConfig.ViewerCertificate = cloudfront.ViewerCertificate( # noqa
                AcmCertificateArn=self.acm_ssl_arn,
                SslSupportMethod='sni-only',
                MinimumProtocolVersion='TLSv1')
        elif self.iam_ssl_id:
            dist.DistributionConfig.ViewerCertificate = cloudfront.ViewerCertificate( # noqa
                IamCertificateId=self.iam_ssl_id,
                SslSupportMethod='sni-only',
                MinimumProtocolVersion='TLSv1')

        for o in self.origins:
            dist.DistributionConfig.Origins.append(o.build(t))

        if len(self.errors) > 0:
            dist.DistributionConfig.CustomErrorResponses = self.errors

        t.add_output([
            Output(
                'DistID',
                Value=Ref(dist)
            )
        ])

        return t

    def output_id(self):
        return "{}DistID".format(self.get_stack_name())
