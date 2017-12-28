from stackformation.aws.stacks import (BaseStack, SoloStack)
import troposphere.cloudwatch as alarm
from troposphere import (
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)


class Alarm(object):

    def __init__(self, name):

        self.name = name
        self.stack = None

    def _build_alarm(self, template, topics):
        raise Exception("Must implement _build_alarm")


class EC2CpuBaseAlarm(Alarm):

    def get_defaults(self):
        return {
            'threshold': 75,
            'period': 60,
            'evaluations': 3,
        }

    def get_default_attrs(self):
        return {
            'Namespace': 'AWS/EC2',
            'MetricName': 'CPUUtilization',
            'ComparisonOperator': 'GreaterThanThreshold',
            'TreatMissingData': 'notBreaching',
            'Statistic': 'Average'
        }


class EC2HighCpuAlarm(EC2CpuBaseAlarm):
    """EC2 High CPU Alarm

    Args:
        ec2_stack (:obj:`stackformation.aws.ec2.EC2Stack`): EC2 Stack to attach alarm to

    Returns:
        void

    """

    def __init__(self, ec2_stack):
        name = '{}HighCpuAlarm'.format(ec2_stack.get_stack_name())
        super(EC2HighCpuAlarm, self).__init__(name)

        self.ec2_stack = ec2_stack

    def _build_alarm(self, t, topics):

        defaults = self.get_defaults()
        default_attrs = self.get_default_attrs()

        instance_output = self.ec2_stack.output_instance()

        if instance_output in t.parameters:
            instance_param = t.parameters[instance_output]
        else:
            instance_param = t.add_parameter(Parameter(
                instance_output,
                Type='String'
            ))

        a = t.add_resource(
            alarm.Alarm(
                '{}EC2HighCpuAlarm'.format(
                    self.name),
                AlarmDescription='Alarm for high CPU (>{})'.format(
                    defaults['threshold']),
                Period=str(
                    defaults['period']),
                Threshold=str(
                    defaults['threshold']),
                EvaluationPeriods=str(
                    defaults['evaluations']),
                AlarmActions=topics,
                InsufficientDataActions=topics,
                OKActions=topics,
                Dimensions=[
                    alarm.MetricDimension(
                        Name='InstanceId',
                        Value=Ref(instance_param))],
            ))

        for k, v in default_attrs.items():
            setattr(a, k, v)


class EC2InstanceFailAlarm(Alarm):

    def __init__(self, ec2_stack):

        name = "{}EC2InstanceFailAlarm".format(ec2_stack.stack_name)

        super(EC2InstanceFailAlarm, self).__init__(name)

        self.alarm_params = {
            'threshold': 0,
            'evaluations': 2,
            'period': 60
        }
        self.ec2_stack = ec2_stack

    def _build_alarm(self, template, topics):

        instance_output = self.ec2_stack.output_instance()

        if instance_output in template.parameters:
            instance_param = template.parameters[instance_output]
        else:
            instance_param = template.add_parameter(Parameter(
                instance_output,
                Type='String'
            ))

        template.add_resource(alarm.Alarm(
            '{}InstanceFailAlarm'.format(self.ec2_stack.get_stack_name()),
            AlarmDescription='Alarm for instance failure',
            Namespace='AWS/EC2',
            MetricName="StatusCheckFailed_System",
            Dimensions=[
                alarm.MetricDimension(
                    Name="InstanceId",
                    Value=Ref(instance_param)
                )
            ],
            Statistic="Average",
            Period=str(self.alarm_params['period']),
            Threshold=str(self.alarm_params['threshold']),
            EvaluationPeriods=str(self.alarm_params['evaluations']),
            ComparisonOperator="GreaterThanThreshold",
            AlarmActions=topics,
            InsufficientDataActions=topics,
            OKActions=topics
        ))


class AlarmStack(BaseStack, SoloStack):

    def __init__(self, name=""):

        super(AlarmStack, self).__init__("Alarms", 600)
        self.stack_name = name
        self.topics = []
        self.alarms = []

    def add_alarm(self, alarm):
        self.stack = self
        self.alarms.append(alarm)
        return alarm

    def add_topic(self, topic):
        self.topics.append(topic)
        return topic

    def build_template(self):

        t = self._init_template()

        # topic param/refs
        topics = [
            Ref(t.add_parameter(Parameter(
                topic.output_topic(),
                Type='String'
            ))
            )
            for topic in self.topics
        ]

        for a in self.alarms:
            a._build_alarm(t, topics)

        return t
