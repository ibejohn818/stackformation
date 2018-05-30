from stackformation import (BaseStack)
import troposphere.ecs as ecs
import troposphere.ecr as ecr
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)


class TaskDef(object):

    def __init__(self, name, role):

        self.name = name
        self.role = role
        self.stack = None
        self.subnet = None
        self.cpu = '.25'
        self.memory = '0.5GB'
        self.mode = 'FARGATE'
        self.network_mode = 'awsvpc'
        self.containers = []

    def add_container(self, data={}):
        self.containers.append(data)

    def build_task(self, t):

        task = t.add_resource(ec2.TaskDefinition(
            '{}TaskDef'.format(self.name),
            RequiresCompatibility=[self.mode],
            NetworkMode=self.network_mode,
            Cpu=self.cpu,
            Memory=self.memory,
            ContainerDefinitions=[
                ecs.ContainerDefinition(**ctr)
                for ctr in self.containers
            ]
        ))

class ECRRepo(object):

    def __init__(self, name):
        self.name = name
        self.stack = None

    def build_repo(self, t):

        repo = t.add_resource(ecr.Repository(
            '{}ECRRepo'.format(self.name)
        ))

        t.add_output(Output(
            '{}ECRRepo'.format(self.name),
            Value=Ref(repo)
        ))

        return repo

    def output_repo(self):
        return "{}{}ECRRepo".format(self.stack.get_stack_name(), self.name)


class ECRStack(BaseStack):

    def __init__(self, name):
        super(ECRStack, self).__init__("ECRStack", 200)
        self.stack_name = name
        self.repos = []

    def add_repo(self, repo):
        repo.stack = self
        self.repos.append(repo);

    def build_template(self):
        t = self._init_template()

        for r in self.repos:
            r.build_repo(t)
        return t


class ECSTaskStack(BaseStack):
    pass

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
