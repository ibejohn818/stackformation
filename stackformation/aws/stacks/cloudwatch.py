from stackformation.aws.stacks import (BaseStack)
from stackformation.aws.stacks import (awslambda)
from stackformation.utils import ensure_param
import troposphere.events as events
import troposphere.awslambda as tlambda
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)


class Event(object):

    def __init__(self, name, **kwargs):

        self.name = name
        self.stack = None
        self.targets = []
        self.enabled = kwargs.get('enabled', True)
        self.schedule = kwargs.get('schedule', "cron(* * * * ? *)")

    def add_target(self, target, role):
        self.targets.append((
            target,
            role
        ))

    def build(self, t):

        evt = t.add_resource(events.Rule(
            '{}Event'.format(self.name),
            Targets=[]

        ))
        if self.schedule is not None:
            evt.ScheduleExpression = self.schedule
        if self.enabled:
            evt.State = 'ENABLED'
        else:
            evt.State = 'DISABLED'

        for val in self.targets:
            tg = val[0]
            r = val[1]
            role_ref = ensure_param(t, r.output_role_arn()) # noqa

            target = events.Target(
            )

            if isinstance(tg, (awslambda.LambdaStack)):
                func_name_ref = ensure_param(t, tg.output_func_name())
                func_arn_ref = ensure_param(t, tg.output_func_arn())
                target.Id = tg.get_stack_name()
                target.Arn = Ref(func_arn_ref)
                t.add_resource(tlambda.Permission(
                    '{}EventPerm'.format(tg.get_stack_name()),
                    Action='lambda:invokeFunction',
                    Principal='events.amazonaws.com',
                    FunctionName=Ref(func_name_ref),
                    SourceArn=GetAtt(evt, 'Arn')
                ))
            evt.Targets.append(target)


class EventStack(BaseStack):

    def __init__(self, name=''):
        super(EventStack, self).__init__('Events', 800)
        self.stack_name = name
        self.events = []

    def add_event(self, event):
        event.stack = self
        self.events.append(event)
        return event

    def build_template(self):
        t = self._init_template()

        for event in self.events:
            event.build(t)

        return t
