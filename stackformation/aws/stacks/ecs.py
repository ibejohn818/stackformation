from stackformation import (BaseStack)
import troposphere.ecs as ecs
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)


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
