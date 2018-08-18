from stackformation.aws.stacks import BaseStack, s3
from awacs import aws
import awacs.sts
import awacs.s3
import troposphere.iam as iam
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)


class IAMBase(object):

    def __init__(self, name):
        self.stack = None
        self.name = name

    def _build_template(self, template):
        raise Exception("_build_template must be implemented!")


class IAMRole(IAMBase):

    def __init__(self, name, principals="*"):

        super(IAMRole, self).__init__(name)

        self.principals = principals
        self.managed_policies = []
        self.policies = []

    def add_policy(self, p):
        self.policies.append(p)

    def add_managed_policy(self, name):
        self.managed_policies.append(
            "arn:aws:iam::aws:policy/{}".format(name)
        )

    def output_role(self):
        return "{}{}Role".format(
            self.stack.get_stack_name(),
            self.name
        )

    def output_role_arn(self):
        return "{}{}RoleArn".format(
            self.stack.get_stack_name(),
            self.name
        )

    def _build_template(self, template):

        t = template

        if self.principals == "*":
            principal_title = "*"
        else:
            principal_title = "Service"

        role = t.add_resource(
            iam.Role(
                self.name,
                AssumeRolePolicyDocument=aws.Policy(
                    Statement=[
                        aws.Statement(
                            Action=[
                                awacs.sts.AssumeRole],
                            Effect=aws.Allow,
                            Principal=aws.Principal(
                                principal_title,
                                self.principals))]),
                Path="/",
                Policies=[],
                ManagedPolicyArns=[]))

        for p in self.policies:
            p._bind_role(t, role)

        for m in self.managed_policies:
            role.ManagedPolicyArns.append(m)

        t.add_output([
            Output(
                '{}Role'.format(self.name),
                Value=Ref(role)
            ),
            Output(
                '{}RoleArn'.format(self.name),
                Value=GetAtt(role, "Arn")
            )
        ])

        return t


class IAMAdminRole(IAMRole):

    def __init__(self):

        super(IAMAdminRole, self).__init__('IAMAdminRole')
        self.add_managed_policy("AdministratorAccess")
        self.principals = [
            'ecs-tasks.amazonaws.com',
        ]


class IAMPolicy(IAMBase):

    def __init__(self, name=''):

        super(IAMPolicy, self).__init__(name)
        self.statements = []

    def _bind_role(self, template, role):
        raise Exception("You must implement _bind_role!")

    def _build_template(self, template):
        pass


class CustomPolicy(IAMPolicy):
    """ Custom IAM inline policy

    Args:
        name (str): policy name
        statements (List[:obj:`awacs.aws.Statement`]): List of policy statement objects.
    """  # noqa

    def __init__(self, name, statements=None):
        super(CustomPolicy, self).__init__(name)
        self.statements = statements or []

    def _bind_role(self, template, role):
        role.Policies.append(iam.Policy(
            self.name,
            PolicyName=self.name,
            PolicyDocument=aws.Policy(
                Statement=self.statements
            )
        ))

    def add_statement(self, statement):
        """ Add a Statement to the custom policy

        Args:
            statement (awacs.aws.Statement): Statement to add to the policy
        """
        self.statements.append(statement)

    def allow(self, allowed):
        ''' Allow custom iam permissions to be added to policy

        Args:
            allowed (dict): Dict of "aws service" : "action"
        '''

        actions = []

        for service, action in allowed.items():
            actions.append(aws.Action(service, action))

        statement = aws.Statement(
            Effect=aws.Allow,
            Action=actions,
            Resource=['*']
        )

        self.add_statement(statement)


class EC2Profile(IAMRole):

    def __init__(self, name):
        super(EC2Profile, self).__init__(
            name
        )
        self.principals = [
            "ec2.amazonaws.com", "ssm.amazonaws.com"
        ]

    def output_instance_profile(self):
        return "{}{}InstanceProfile".format(
            self.stack.get_stack_name(),
            self.name
        )

    def _build_template(self, template):

        t = super(EC2Profile, self)._build_template(template)

        role = t.resources[self.name]

        instance_profile = t.add_resource(iam.InstanceProfile(
            "{}EC2Profile".format(self.name),
            Path="/",
            Roles=[Ref(role)]
        ))

        t.add_output([
            Output(
                '{}InstanceProfile'.format(self.name),
                Value=Ref(instance_profile)
            )
        ])


class EC2AdminProfile(EC2Profile):

    def __init__(self, name):
        super(EC2AdminProfile, self).__init__(name)
        # self.principals = ["*"]
        self.add_managed_policy("AdministratorAccess")


class EC2FullAccess(IAMPolicy):

    def _bind_role(self, template, role):

        role.Policies.append(iam.Policy(
            'ec2fullaccess',
            PolicyName='ec2fullaccess',
            PolicyDocument=aws.Policy(
                Statement=[
                    aws.Statement(
                        Action=[awacs.aws.Action("ec2", "*")],
                        Effect=aws.Allow,
                        Resource=["*"]
                    )
                ]
            )
        ))


class ELBFullAccess(IAMPolicy):

    def _bind_role(self, template, role):

        role.Policies.append(iam.Policy(
            'elbfullaccess',
            PolicyName='elbfullaccess',
            PolicyDocument=aws.Policy(
                Statement=[
                    aws.Statement(
                        Action=[awacs.aws.Action("elasticloadbalancing", "*")],
                        Effect=aws.Allow,
                        Resource=["*"]
                    )
                ]
            )
        ))


class DynamoAll(IAMPolicy):

    def _bind_role(self, t, r):
        r.Policies.append(iam.Policy(
            'dynamoall',
            PolicyName='dynamoall',
            PolicyDocument=aws.Policy(
                Statement=[
                    aws.Statement(
                        Action=[awacs.aws.Action("dynamodb", "*")],
                        Effect=aws.Allow,
                        Resource=["*"]
                    )
                ]
            )
        ))


class ECRAll(IAMPolicy):

    def _bind_role(self, t, r):
        r.Policies.append(iam.Policy(
            'ecrall',
            PolicyName='ecrall',
            PolicyDocument=aws.Policy(
                Statement=[
                    aws.Statement(
                        Action=[awacs.aws.Action("ecr", "*")],
                        Effect=aws.Allow,
                        Resource=["*"]
                    )
                ]
            )
        ))


class SqsAll(IAMPolicy):

    def _bind_role(self, t, r):
        r.Policies.append(iam.Policy(
            'sqsall',
            PolicyName='sqsall',
            PolicyDocument=aws.Policy(
                Statement=[
                    aws.Statement(
                        Action=[awacs.aws.Action("sqs", "*")],
                        Effect=aws.Allow,
                        Resource=["*"]
                    )
                ]
            )
        ))


class S3FullBucketAccess(IAMPolicy):

    def __init__(self, bucket):
        self.buckets = []
        self.add_bucket(bucket)

    def add_bucket(self, bucket):
        if not isinstance(bucket, list):
            bucket = [bucket]
        for b in bucket:
            if not isinstance(b, s3.S3Bucket):
                raise TypeError("Object much be s3.S3Bucket")
        self.buckets += bucket

    def _bind_role(self, t, r):
        brefs = []
        for b in self.buckets:
            bn = b.output_bucket_name()
            if bn in t.parameters:
                brefs.append(t.parameters[bn])
            else:
                brefs.append(t.add_parameter(Parameter(
                    bn,
                    Type="String"
                )))

        r.Policies.append(iam.Policy(
            "s3fullaccess",
            PolicyName="s3fullaccess",
            PolicyDocument=aws.Policy(
                Statement=[
                    aws.Statement(
                        Action=[awacs.aws.Action("s3", "*")],
                        Effect=aws.Allow,
                        Resource=[
                            Join("", ["arn:aws:s3:::", Ref(i)])
                            for i in brefs
                        ]
                    ),
                    aws.Statement(
                        Action=[awacs.aws.Action("s3", "*")],
                        Effect=aws.Allow,
                        Resource=[
                            Join("", ["arn:aws:s3:::", Ref(i), "/*"])
                            for i in brefs

                        ]
                    ),
                ]
            )))


class S3ReadBucketAccess(IAMPolicy):

    def __init__(self, buckets):
        self.buckets = []

        if not isinstance(buckets, list):
            buckets = [buckets]

        self.add_bucket(buckets)

    def add_bucket(self, bucket):
        if isinstance(bucket, list):
            self.buckets.extend(bucket)
        else:
            self.buckets.append(bucket)

    def _bind_role(self, t, r):

        brefs = []

        for b in self.buckets:
            bn = b.output_bucket_name()
            if bn in t.parameters:
                brefs.append(t.parameter[bn])
            else:
                brefs.append(t.add_parameter(Parameter(
                    bn,
                    Type='String'
                )))

        r.Policies.append(iam.Policy(
            's3readaccess',
            PolicyName='s3readaccess',
            PolicyDocument=aws.Policy(
                Statement=[
                    aws.Statement(
                        Effect=aws.Allow,
                        Action=[
                            awacs.aws.Action('s3', 'GetObject*'),
                            awacs.aws.Action('s3', 'ListAllMyBuckets'),
                            awacs.aws.Action('s3', 'GetObject'),
                            awacs.aws.Action('s3', 'ListBucket'),
                            awacs.aws.Action('s3', 'ListBucketVersions'),
                        ],
                        Resource=[
                            Join("", ["arn:aws:s3:::", Ref(i), "/*"])
                            for i in brefs
                        ]
                    ),
                    aws.Statement(
                        Effect=aws.Allow,
                        Action=[
                            awacs.aws.Action('s3', 'GetObject*'),
                            awacs.aws.Action('s3', 'ListAllMyBuckets'),
                            awacs.aws.Action('s3', 'GetObject'),
                            awacs.aws.Action('s3', 'ListBucket'),
                            awacs.aws.Action('s3', 'ListBucketVersions'),
                        ],
                        Resource=[
                            Join("", ["arn:aws:s3:::", Ref(i), "*"])
                            for i in brefs
                        ]
                    )
                ]
            )
        ))


class CloudWatchLogs(IAMPolicy):

    def _bind_role(self, t, r):

        r.Policies.append(iam.Policy(
            'cloudwatch',
            PolicyName='cloudwatch',
            PolicyDocument=aws.Policy(
                Statement=[
                    aws.Statement(
                        Effect=aws.Allow,
                        Resource=['*'],
                        Action=[
                            aws.Action("logs", "*"),
                        ]
                    )
                ]
            )
        ))


class CodeDeployRole(IAMRole):

    def __init__(self, name):
        super(CodeDeployRole, self).__init__(
            "{}CodeDeploy".format(name),
            [
                'codedeploy.us-west-1.amazonaws.com',
                'codedeploy.us-west-2.amazonaws.com',
                'codedeploy.us-east-1.amazonaws.com',
                'codedeploy.us-east-2.amazonaws.com',
                'codedeploy.eu-west-1.amazonaws.com',
                'codedeploy.ap-southeast-2.amazonaws.com'
            ])


class DynamoScalingPolicy(IAMPolicy):

    def _bind_role(self, t, r):
        r.Policies.append(
            iam.Policy(
                'DynamoScaleRolePolicy',
                PolicyName='DynamoScaleRolePolicy',
                PolicyDocument=aws.Policy(
                    Statement=[
                        aws.Statement(
                            Effect=aws.Allow,
                            Action=[
                                aws.Action(
                                    "dynamodb",
                                    "DescribeTable"),
                                aws.Action(
                                    "dynamodb",
                                    "UpdateTable"),
                            ],
                            Resource=["*"]),
                        aws.Statement(
                            Effect=aws.Allow,
                            Action=[
                                aws.Action(
                                    "cloudwatch",
                                    "PutMetricAlarm"),
                                aws.Action(
                                    "cloudwatch",
                                    "DescribeAlarms"),
                                aws.Action(
                                    "cloudwatch",
                                    "GetMetricStatistics"),
                                aws.Action(
                                    "cloudwatch",
                                    "SetAlarmState"),
                                aws.Action(
                                    "cloudwatch",
                                    "DeleteAlarms"),
                            ],
                            Resource=["*"]),
                    ])))


class DynamoScalingRole(IAMRole):

    def __init__(self, name):
        super(DynamoScalingRole, self).__init__(
            "{}DDBScaling".format(name),
            [
                "application-autoscaling.amazonaws.com"
            ])

        self.add_policy(DynamoScalingPolicy())


class CodeDeployPolicy(IAMPolicy):

    def __init__(self):
        super(CodeDeployPolicy, self).__init__('CodeDeployPolicy')

    def _bind_role(self, t, r):

        r.Policies.append(iam.Policy(
            'codedeploy',
            PolicyName='codedeploy',
            PolicyDocument=aws.Policy(
                Statement=[
                    aws.Statement(
                        Effect=aws.Allow,
                        Resource=['*'],
                        Action=[
                            aws.Action('autoscaling', '*'),
                            aws.Action('elasticloadbalancing', 'DescribeLoadBalancers'),  # noqa
                            aws.Action('elasticloadbalancing', 'DescribeInstanceHealth'),  # noqa
                            aws.Action('elasticloadbalancing',
                                       'RegisterInstancesWithLoadBalancer'),
                            aws.Action('elasticloadbalancing',
                                       'DeregisterInstancesFromLoadBalancer'),
                            aws.Action('ec2', 'Describe*'),
                            aws.Action('ec2', 'TerminateInstances'),
                            aws.Action('tag', 'GetTags'),
                            aws.Action('tag', 'GetResources'),
                            aws.Action('tag', 'GetTagsForResource'),
                            aws.Action('tag', 'GetTagsForResourceList'),
                            aws.Action('lambda', '*')
                        ]
                    ),
                ]
            )
        ))


class IAMUser(IAMBase):

    def __init__(self, name):

        super(IAMUser, self).__init__(name)
        self.policies = []
        self.managed_policy_arns = []
        self._generate_key = True,
        self._login = None
        self._allow_console = False

    def set_login_name(self, login):
        self._login = login

    def disable_key(self):
        self._generate_key = False

    def enable_key(self):
        self._generate_key = True

    def allow_console_login(self):
        self._allow_console = True

    def disable_console_login(self):
        self._allow_console = False

    def add_policy(self, policy):
        self.policies.append(policy)

    def add_managed_arn(self, name):
        self.managed_policy_arns.append(
            "arn:aws:iam::aws:policy/{}".format(name)
        )

    def _build_template(self, template):

        t = template

        user = t.add_resource(iam.User(
            self.name,
            Path="/",
            Policies=[],
            ManagedPolicyArns=[]
        ))

        if self._login is not None:
            user.UserName = self._login

        if self._generate_key:
            key_serial_param = t.add_parameter(Parameter(
                'Input{}IAMUserKeySerial'.format(self.name),
                Type='String',
                Default='1',
                Description='Serial for User:{} key'.format(self.name)
            ))

            key = t.add_resource(iam.AccessKey(
                '{}IAMAccessKey'.format(self.name),
                Serial=Ref(key_serial_param),
                Status='Active',
                UserName=Ref(user)
            ))

            t.add_output([
                Output(
                    '{}IAMSecretKey'.format(self.name),
                    Value=GetAtt(key.title, 'SecretAccessKey'),
                    Description='IAM SecretKey for {}'.format(self.name)
                ),
                Output(
                    '{}IAMAccessKey'.format(self.name),
                    Value=Ref(key),
                    Description='IAM AccessKey for {}'.format(self.name)
                )
            ])

        if self._allow_console:
            def_passwd_param = t.add_parameter(Parameter(
                'Input{}DefaultConsolePasswd'.format(self.name),
                Type='String',
                Default='D3fau1t9a55w0r6_c4ang3m3',
                Description='Default console passwd for {}'.format(self.name)
            ))

            user.LoginProfile = iam.LoginProfile(
                Password=Ref(def_passwd_param),
                PasswordResetRequired=True
            )

        for policy in self.policies:
            policy._bind_role(t, user)

        for arn in self.managed_policy_arns:
            user.ManagedPolicyArns.append(arn)

        t.add_output([
            Output(
                '{}IAMUser'.format(self.name),
                Value=Ref(user),
                Description='{} User Output'.format(self.name)
            )
        ])

    def output_user(self):
        return "{}{}IAMUser".format(
            self.stack.get_stack_name(),
            self.name
        )

    def output_access_key(self):
        return "{}{}IAMAccessKey".format(
            self.stack.get_stack_name(),
            self.name
        )

    def output_secret_key(self):
        return "{}{}IAMSecretKey".format(
            self.stack.get_stack_name(),
            self.name
        )


class AdminUser(IAMUser):
    pass


class CodeDeployUser(IAMUser):
    pass


class IAMStack(BaseStack):

    def __init__(self, name=""):

        super(IAMStack, self).__init__("IAM", 20)

        self.stack_name = name

        self.roles = []
        self.policies = []
        self.users = []
        self.groups = []

    def find_role(self, clazz, name=None):
        return self.find_class_in_list(self.roles, clazz, name)

    def add_role(self, role):
        self.roles.append(role)
        role.stack = self
        return role

    def add_user(self, user):
        self.users.append(user)
        user.stack = self
        return user

    def add_policy(self, policy):
        self.policies.append(policy)
        policy.stack = self
        return policy

    def build_template(self):

        t = self._init_template()

        for role in self.roles:
            role._build_template(t)

        for user in self.users:
            user._build_template(t)

        return t
