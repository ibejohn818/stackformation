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


class SNSSubscription(object):

    def __init__(self, name):
        self.name = name
        self.stack = None

    def build_subscription(self, template, topic):
        """
            Return a tuple of (protocol, endpoint)
        """
        raise Exception("Must implement build_subscription")

    def output_subscription(self):
        return "{}{}SNSSubscription".format(
            self.stack.get_stack_name(),
            self.name
        )


class SNSTopicStack(BaseStack):

    def __init__(self, name):

        super(SNSTopicStack, self).__init__("SNSTopic", 200)

        self.stack_name = name
        self.subscriptions = []

    def add_subscription(self, subscriber):
        subscriber.stack = self
        self.subscriptions.append(subscriber)
        return subscriber

    def build_template(self, template=None):

        if not template:
            t = self._init_template()
        else:
            t = template

        topic = t.add_resource(sns.Topic(
            "{}SNSTopic".format(self.stack_name),
            TopicName=self.stack_name,
            DisplayName=self.stack_name,
        ))

        for s in self.subscriptions:

            sub = s.build_subscription(t, topic)
            subr = t.add_resource(sns.SubscriptionResource(
                '{}SNSSubscription'.format(s.name),
                Protocol=sub[0],
                Endpoint=sub[1],
                TopicArn=Ref(topic)
            ))
            t.add_output([
                Output(
                    '{}SNSSubscription'.format(s.name),
                    Value=Ref(subr)
                )
            ])

        t.add_output([
            Output(
                "{}SNSTopic".format(self.stack_name),
                Value=Ref(topic)
            )
        ])

        return t

    def output_topic(self):
        return "{}{}SNSTopic".format(
            self.get_stack_name(),
            self.stack_name
        )


class EmailSubscription(SNSSubscription):

    def __init__(self, name):

        super(EmailSubscription, self).__init__(name)

    def build_subscription(self, t, topic):

        ep = t.add_parameter(Parameter(
            'Input{}SNSEmailAddress'.format(self.name),
            Type='String'
        ))

        return ('email', Ref(ep))


class SlackSubscription(SNSSubscription):

    def __init__(self, name):
        super(SlackSubscription, self).__init__(name)

    def build_subscription(self, t, topic):

        policy = t.add_resource(iam.Role(
            "{}SlackSNSRole".format(self.name),
            AssumeRolePolicyDocument=aws.Policy(
                Statement=[
                    aws.Statement(
                        Action=[awacs.sts.AssumeRole],
                        Effect=aws.Allow,
                        Principal=aws.Principal(
                            "Service", ["lambda.amazonaws.com"])
                    )
                ]
            ),
            Path="/",
            Policies=[
                iam.Policy(
                    PolicyName='snspublic',
                    PolicyDocument=aws.PolicyDocument(
                        Statement=[
                            aws.Statement(
                                Effect=aws.Allow,
                                Action=[
                                    awacs.sns.Publish,
                                    awacs.logs.PutLogEvents,
                                    awacs.logs.CreateLogGroup,
                                    awacs.logs.CreateLogStream,
                                ],
                                Resource=["*"]
                            )
                        ]
                    )
                )
            ],
            ManagedPolicyArns=[
                # "arn:aws:iam::aws:policy/AdministratorAccess"
            ]
        ))

        code = ["import sys"]
        # make lambda function
        fn = t.add_resource(awslambda.Function(
            '{}SlackTopicFN'.format(self.name),
            Handler='index.handle',
            Runtime='python3.6',
            Role=GetAtt(policy, "Arn"),
            Code=awslambda.Code(
                    ZipFile=Join("", code)
            )
        ))

        t.add_resource(awslambda.Permission(
            '{}LambdaPerm'.format(self.name),
            Action='lambda:InvokeFunction',
            FunctionName=GetAtt(fn, "Arn"),
            SourceArn=Ref(topic),
            Principal="sns.amazonaws.com"
        ))

        return ("lambda", GetAtt(fn, "Arn"))


class SlackTopicStack(SNSTopicStack):

    def __init__(self, name):

        name = "{}SlackTopic".format(name)

        super(SlackTopicStack, self).__init__(name)

        self.slack_url = None
        self.slack_channel = None

    def build_template(self):

        t = self._init_template()

        # make iam policy
        policy = t.add_resource(iam.Role(
            "{}SlackSNSRole".format(self.stack_name),
            AssumeRolePolicyDocument=aws.Policy(
                Statement=[
                    aws.Statement(
                        Action=[awacs.sts.AssumeRole],
                        Effect=aws.Allow,
                        Principal=aws.Principal(
                            "Service", ["lambda.amazonaws.com"])
                    )
                ]
            ),
            Path="/",
            Policies=[
                iam.Policy(
                    PolicyName='snspublic',
                    PolicyDocument=aws.PolicyDocument(
                        Statement=[
                            aws.Statement(
                                Effect=aws.Allow,
                                Action=[
                                    awacs.sns.Publish,
                                    awacs.logs.PutLogEvents,
                                    awacs.logs.CreateLogGroup,
                                    awacs.logs.CreateLogStream,
                                ],
                                Resource=["*"]
                            )
                        ]
                    )
                )
            ],
            ManagedPolicyArns=[
                # "arn:aws:iam::aws:policy/AdministratorAccess"
            ]
        ))

        code = ["import sys"]
        # make lambda function
        fn = t.add_resource(awslambda.Function(
            '{}SlackTopicFN'.format(self.stack_name),
            Handler='index.handle',
            Runtime='python3.6',
            Role=GetAtt(policy, "Arn"),
            Code=awslambda.Code(
                    ZipFile=Join("", code)
            )
        ))

        topic = t.add_resource(sns.Topic(
            "{}SNSTopic".format(self.stack_name),
            TopicName=self.stack_name,
            DisplayName=self.stack_name,
            Subscription=[
                sns.Subscription(
                    Protocol='lambda',
                    Endpoint=GetAtt(fn, "Arn")
                )
            ],

        ))

        t.add_resource(awslambda.Permission(
            '{}LambdaPerm'.format(self.stack_name),
            Action='lambda:InvokeFunction',
            FunctionName=GetAtt(fn, "Arn"),
            SourceArn=Ref(topic),
            Principal="sns.amazonaws.com"
        ))

        t.add_output([
            Output(
                "{}SNSTopic".format(self.stack_name),
                Value=Ref(topic)
            )
        ])

        return t
