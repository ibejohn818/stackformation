from stackformation.aws.stacks import BaseStack
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)
import troposphere.sqs as sqs


class Queue(object):

    def __init__(self, name):
        self.name = name
        self.stack = None
        self.delay = None
        self.timeout = None

    def build_queue(self, t):

        q = t.add_resource(sqs.Queue(
            '{}Queue'.format(self.name)))

        if self.delay:
            q.DelaySeconds = self.delay

        if self.timeout:
            q.VisibilityTimeout = self.timeout

        t.add_output(Output(
            '{}Queue'.format(self.name),
            Value=Ref(q)
        ))
        t.add_output(Output(
            '{}QueueArn'.format(self.name),
            Value=GetAtt(q, 'Arn')
        ))

    def output_queue(self):
        return "{}{}Queue".format(
            self.stack.get_stack_name(),
            self.name)

    def output_queue_arn(self):
        return "{}{}QueueArn".format(
            self.stack.get_stack_name(),
            self.name)


class SQSStack(BaseStack):

    def __init__(self, name=''):

        super(SQSStack, self).__init__('SQS', 200)
        self.stack_name = name
        self.queues = []

    def add_queue(self, queue):
        queue.stack = self
        self.queues.append(queue)
        return queue

    def build_template(self):

        t = self._init_template()

        for q in self.queues:
            q.build_queue(t)

        return t
