from stackformation.aws.stacks import BaseStack
from awacs import aws
import awacs.sts
import awacs.s3
import troposphere.iam as iam
from troposphere import (
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

    def __init__(self, name):

        super(IAMRole, self).__init__(name)

        self.principals = ["*"]
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

        role = t.add_resource(iam.Role(
            self.name,
            AssumeRolePolicyDocument=aws.Policy(
                Statement=[
                    aws.Statement(
                        Action=[awacs.sts.AssumeRole],
                        Effect=aws.Allow,
                        Principal=aws.Principal("Service", self.principals)
                    )
                ]
            ),
            Path="/",
            Policies=[],
            ManagedPolicyArns=[]
        ))

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
    """

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
            "{}EC2".format(name)
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


class S3FullBucketAccess(IAMPolicy):

    def __init__(self, bucket):

        self.buckets = []
        self.add_bucket(bucket)

    def add_bucket(self, bucket):
        self.buckets.append(bucket)

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
                            awacs.s3.GetObject,
                            awacs.s3.ListBucket,
                            awacs.s3.ListBucketVersions,
                            awacs.aws.Action('s3', 'GetObject*'),
                            awacs.aws.Action('s3', 'ListAllMyBuckets')
                        ],
                        Resource=[
                            Join("", ["arn:aws:s3:::", Ref(i), "/*"])
                            for i in brefs
                        ]
                    ),
                    aws.Statement(
                        Effect=aws.Allow,
                        Action=[
                            awacs.s3.GetObject,
                            awacs.s3.ListBucket,
                            awacs.s3.ListBucketVersions,
                            awacs.aws.Action('s3', 'GetObject*'),
                            awacs.aws.Action('s3', 'ListAllMyBuckets')
                        ],
                        Resource=[
                            Join("", ["arn:aws:s3:::", Ref(i), "*"])
                            for i in brefs
                        ]
                    )
                ]
            )
        ))


class IAMStack(BaseStack):

    def __init__(self, name=""):

        super(IAMStack, self).__init__("IAM", 20)

        self.stack_name = name

        self.roles = []
        self.policies = []
        self.users = []

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

        return t
