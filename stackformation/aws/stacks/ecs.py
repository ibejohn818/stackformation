from stackformation.aws.stacks import (BaseStack, TemplateComponent)
from stackformation.utils import ensure_param
import troposphere.ecs as ecs
import troposphere.ecr as ecr
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)
from stackformation import utils
from copy import deepcopy


class TaskDefTemplate(TemplateComponent):

    def __init__(self, text):
        self.name = 'TaskDefTemplate'
        self.text = text

    def render(self):
        return self.text


class TaskContainer(object):

    def __init__(self, stack, **kwargs):
        self.stack = stack
        self.data = kwargs

        if self.data.get('Environment'):
            for v in self.data.get('Environment'):
                self.stack.add_template_component(
                    'Task', TaskDefTemplate(v['name']))
                self.stack.add_template_component(
                    'Task', TaskDefTemplate(v['value']))
        if self.data.get('Image'):
            self.stack.add_template_component(
                'Task', TaskDefTemplate(
                    self.data.get('Image')))

        if self.data.get('LogConfiguration'):
            if self.data.get('LogConfiguration').get('Options').get('awslogs-group'):
                self.stack.add_template_component(
                    'Task', TaskDefTemplate(self.data.get('LogConfiguration').get('Options').get('awslogs-group')))

        self.stack.add_container(self)

    def jinja_txt(self, value):
        if not self.stack._deploying:
            return value
        context = self.stack.infra.context
        env = utils.jinja_env(context)
        t = env[0].from_string(value)
        return t.render(context.vars)

    def build(self, t):

        env = []
        logConf = None
        data = deepcopy(self.data)

        if data.get('Environment'):
            for v in data.get('Environment'):
                e = ecs.Environment(
                    Name=self.jinja_txt(v['name']),
                    Value=self.jinja_txt(v['value'])
                )
                env.append(e)
            del data['Environment']

        if data.get('Image'):
            data['Image'] = self.jinja_txt(data['Image'])

        if data.get('LogConfiguration'):
            logConf = ecs.LogConfiguration(
                    LogDriver=data.get('LogConfiguration').get('LogDriver'),
                    Options={}
            )
            if data.get('LogConfiguration').get('Options').get('awslogs-group'):
                logConf.Options['awslogs-group'] = self.jinja_txt(data['LogConfiguration']['Options']['awslogs-group'])
            if data.get('LogConfiguration').get('Options').get('awslogs-region'):
                logConf.Options['awslogs-region'] = data['LogConfiguration']['Options']['awslogs-region']
            if data.get('LogConfiguration').get('Options').get('awslogs-stream-prefix'):
                logConf.Options['awslogs-stream-prefix'] = data['LogConfiguration']['Options']['awslogs-stream-prefix']
            del data['LogConfiguration']


        ctr = ecs.ContainerDefinition(**data)
        ctr.Environment = env
        if logConf is not None:
            ctr.LogConfiguration = logConf
        return ctr


class ECSTaskStack(BaseStack):

    def __init__(self, name, **kwargs):

        super(ECSTaskStack, self).__init__('ECSTask', 800)

        self.stack_name = name
        self.execution_role = kwargs.get('execution_role', None)
        self.task_role = kwargs.get('task_role', None)
        self.subnet = None
        self.cpu = kwargs.get('cpu', '256')
        self.memory = kwargs.get('memory', '0.5GB')
        self.mode = kwargs.get('mode', 'FARGATE')
        self.network_mode = kwargs.get('network_mode', 'awsvpc')
        self.containers = []

    def add_container(self, container):
        print(container)
        self.containers.append(container)

    def build_template(self):

        t = self._init_template()

        task_role = ensure_param(t, self.task_role.output_role_arn())
        exe_role = ensure_param(t, self.execution_role.output_role_arn())

        task = t.add_resource(ecs.TaskDefinition(
            '{}TaskDef'.format(self.stack_name),
            TaskRoleArn=Ref(task_role),
            Family=self.stack_name,
            ExecutionRoleArn=Ref(exe_role),
            RequiresCompatibilities=[self.mode],
            NetworkMode=self.network_mode,
            Cpu=self.cpu,
            Memory=self.memory,
            ContainerDefinitions=[
            ]
        ))

        for c in self.containers:
            task.ContainerDefinitions.append(c.build(t))


        t.add_output([
            Output(
                'TaskArn',
                Value=Ref(task)
            )
        ])
        return t


class ECRRepo(object):

    def __init__(self, name):
        self.name = name
        self.stack = None

    def build_repo(self, t):

        repo = t.add_resource(ecr.Repository(
            '{}ECRRepo'.format(self.name)
        ))

        t.add_output([
            Output(
                '{}ECRRepo'.format(self.name),
                Value=Ref(repo)
            ),
            Output(
                '{}ECRRepoUrl'.format(self.name),
                Value=Join('', [
                    Ref("AWS::AccountId"),
                    ".dkr.ecr.",
                    Ref("AWS::Region"),
                    ".amazonaws.com/",
                    Ref(repo)
                ])
            )
        ])

        return repo

    def output_url(self):
        return "{}{}ECRRepoUrl".format(self.stack.get_stack_name(), self.name)

    def output_repo(self):
        return "{}{}ECRRepo".format(self.stack.get_stack_name(), self.name)


class ECRStack(BaseStack):

    def __init__(self, name):
        super(ECRStack, self).__init__("ECRStack", 200)
        self.stack_name = name
        self.repos = []

    def add_repo(self, repo):
        repo.stack = self
        self.repos.append(repo)
        return repo

    def build_template(self):
        t = self._init_template()

        for r in self.repos:
            r.build_repo(t)
        return t


class Cluster(object):

    def __init__(self, name=''):

        self.name = name
        self.stack = None

    def add_to_template(self, template):

        t = template
        cluster = t.add_resource(ecs.Cluster(
            "{}ECSCluster".format(self.name)
        ))

        if len(self.name) > 0:
            cluster.ClusterName = self.name

        t.add_output([
            Output(
                "{}ECSCluster".format(
                    self.name
                ),
                Value=Ref(cluster)
            ),
            Output(
                "{}ECSClusterArn".format(
                    self.name
                ),
                Value=GetAtt(cluster, 'Arn')
            ),
        ])

    def output_cluster(self):
        return "{}{}ECSCluster".format(
            self.stack.get_stack_name(),
            self.name)

    def output_cluster_arn(self):
        return "{}{}ECSClusterArn".format(
            self.stack.get_stack_name(),
            self.name)


class ECSStack(BaseStack):

    def __init__(self, name):

        super(ECSStack, self).__init__("ECS", 200)

        self.stack_name = name
        self.clusters = []

    def add_cluster(self, cluster_name):
        cluster = Cluster(cluster_name)
        cluster.stack = self
        self.clusters.append(cluster)
        return cluster

    def find_cluster(self, name):

        for i in self.clusters:
            if name == i.name:
                return i

    def build_template(self):

        t = self._init_template()

        for c in self.clusters:
            c.add_to_template(t)

        return t
