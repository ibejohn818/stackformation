from stackformation.aws.stacks import BaseStack
from troposphere import (sns, iam, dynamodb) # noqa
import awacs.kms # noqa
import awacs.sns # noqa
import awacs.logs # noqa
from awacs import aws # noqa
from awacs.aws import Allow, Statement, Principal, Action, Policy # noqa
from awacs.sts import AssumeRole # noqa
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export, Base64,
)
from troposphere.applicationautoscaling import (
    ScalableTarget,
    ScalingPolicy,
    TargetTrackingScalingPolicyConfiguration,
    PredefinedMetricSpecification
)
from stackformation.utils import ensure_param

SCALING_DEFS = {
    'in_cooldown': 10800,
    'out_cooldown': 60,
    'min': 1,
    'max': 100,
    'target': 70
}


class DynamoTable(object):

    def __init__(self, name, **kwargs):
        """

        Params:
            key_schema: The key schema, HASH for PK and RANGE for local seconday
            IE:
            [
                {
                    'name': 'attribute_name',
                    'type': "HASH"
                },
                {
                    'name': 'attr name',
                    'type': 'RANGE'
                }
            ]
            attrs (list[{}]):  The defined attributes
            IE:
                [
                    {
                        'name': 'attr name',
                        'type': 'S|N|B'
                    }
                ]

            gsi (list[{}]): List of GlobalSecondaryIndex's
            IE:
                [
                    {
                        'name': 'index name',
                        'keys': [
                            {
                                'name': 'attr name',
                                'type': 'HASH|RANGE'
                            }
                        ],
                        'proj': {
                            'type': 'projection type = INCLUDE|KEYS_ONLY|ALL',
                            'nka': [
                                'list of non key attrs'
                            ]
                        },
                        'write_units': 1,
                        'read_units': 1
                    }
                ]

        """ # noqa
        self.stack = None
        self.name = name
        self.key_schema = kwargs.get('key_schema')
        self.attrs = kwargs.get('attrs', [])
        self.gsi = kwargs.get('gsi', [])
        self.read_units = kwargs.get('read', 1)
        self.write_units = kwargs.get('write', 1)
        self.use_table_name = False
        self.stream_spec = None
        self.resource = None
        self.pitr_enabled = False
        self.scaling_params = {
            'read': SCALING_DEFS,
            'write': SCALING_DEFS
        }
        self.autoscaling = kwargs.get('autoscaling', False)
        self.scale_gsi = kwargs.get('scale_gsi', False)
        self.scaling_role = kwargs.get('scaling_role', None)

    def set_scaling_param(self, key, val, type=None):
        if type is None:
            types = ['read', 'write']
        else:
            types = [type]
        for t in types:
            self.scaling_params[t][key] = val

    def create_scaling_map(self):

        smap = []
        smap.append({
            'resource': ['table', Ref(self.resource)],
            'name': self.name,
            'write_dim': "dynamodb:table:WriteCapacityUnits",
            'read_dim': "dynamodb:table:ReadCapacityUnits"
        })

        if self.scale_gsi:
            for gsi in self.gsi:
                idx_name = gsi['name']
                smap.append({
                    'resource': ['table', Ref(self.resource), 'index/{}'.format(idx_name)], # noqa
                    'name': "{}{}".format(self.name, idx_name.replace('-', '')),
                    'write_dim': "dynamodb:index:WriteCapacityUnits",
                    'read_dim': "dynamodb:index:ReadCapacityUnits"
                })
        return smap

    def __lt__(self, other):
        return self.name < other.name

    def build_table(self, t):

        tbl = t.add_resource(dynamodb.Table(
            '{}Table'.format(self.name),
            ProvisionedThroughput=dynamodb.ProvisionedThroughput(
                ReadCapacityUnits=self.read_units,
                WriteCapacityUnits=self.write_units
            ),
            PointInTimeRecoverySpecification=dynamodb.PointInTimeRecoverySpecification(
                PointInTimeRecoveryEnabled=self.pitr_enabled
            )
        ))

        if self.use_table_name:
            tbl.TableName = self.name

        tbl.KeySchema = [
            dynamodb.KeySchema(
                AttributeName=v['name'],
                KeyType=v['type']
            )
            for v in self.key_schema
        ]

        tbl.AttributeDefinitions = [
            dynamodb.AttributeDefinition(
                AttributeName=attr['name'],
                AttributeType=attr['type']
            )
            for attr in self.attrs
        ]

        tbl.GlobalSecondaryIndexes = []

        for a in self.gsi:
            gsi = dynamodb.GlobalSecondaryIndex()
            gsi.IndexName = a['name']
            gsi.KeySchema = []
            for k in a['keys']:
                gsi.KeySchema.append(
                    dynamodb.KeySchema(
                        AttributeName=k['name'],
                        KeyType=k['type']))
            gsi.Projection = dynamodb.Projection(
                ProjectionType=a['proj']['type']
            )
            if a['proj'].get('nka') and len(a['proj'].get('nka')) > 0:
                gsi.Projection.NonKeyAttributes = []
                for aa in a['proj'].get('nka'):
                    gsi.Projection.NonKeyAttributes.append(aa)

            gsi.ProvisionedThroughput = dynamodb.ProvisionedThroughput(
                ReadCapacityUnits=a['read_units'],
                WriteCapacityUnits=a['write_units']
            )
            tbl.GlobalSecondaryIndexes.append(gsi)

        if self.stream_spec:
            tbl.StreamSpecification = dynamodb.StreamSpecification(
                StreamViewType=self.stream_spec
            )
            t.add_output(
                Output(
                    '{}TableStreamArn'.format(self.name),
                    Value=GetAtt(tbl, 'StreamArn')
                )
            )

        t.add_output(
            Output(
                '{}Table'.format(self.name),
                Value=Ref(tbl)
            )
        )

        t.add_output(
            Output(
                '{}TableArn'.format(self.name),
                Value=GetAtt(tbl, 'Arn')
            )
        )

        self.resource = tbl

        if self.autoscaling:

            role_param = ensure_param(
                t, self.scaling_role.output_role_arn(), "String")

            smap = self.create_scaling_map()
            for m in smap:
                write_target = t.add_resource(ScalableTarget(
                    '{}DDBWriteTarget'.format(m['name']),
                    MinCapacity=self.scaling_params['write']['min'],
                    MaxCapacity=self.scaling_params['write']['max'],
                    ResourceId=Join("/", m['resource']),
                    RoleARN=Ref(role_param),
                    ServiceNamespace="dynamodb",
                    ScalableDimension=m['write_dim']
                ))
                read_target = t.add_resource(ScalableTarget(
                    '{}DDBReadTarget'.format(m['name']),
                    MinCapacity=self.scaling_params['read']['min'],
                    MaxCapacity=self.scaling_params['read']['max'],
                    ResourceId=Join("/", m['resource']),
                    RoleARN=Ref(role_param),
                    ServiceNamespace="dynamodb",
                    ScalableDimension=m['read_dim']
                ))
                t.add_resource(ScalingPolicy(
                    '{}DDBWritePolicy'.format(m['name']),
                    PolicyName='{}DynamoScaleWritePolicy'.format(m['name']),
                    PolicyType='TargetTrackingScaling',
                    ScalingTargetId=Ref(write_target),
                    TargetTrackingScalingPolicyConfiguration=TargetTrackingScalingPolicyConfiguration(  # noqa
                        TargetValue=self.scaling_params[
                            'write']['target'],
                        ScaleInCooldown=self.scaling_params[
                            'write']['in_cooldown'],
                        ScaleOutCooldown=self.scaling_params[
                            'write']['out_cooldown'],
                        PredefinedMetricSpecification=PredefinedMetricSpecification(  # noqa
                            PredefinedMetricType="DynamoDBWriteCapacityUtilization" # noqa
                        )
                    )
                ))
                t.add_resource(ScalingPolicy(
                    '{}DDBReadPolicy'.format(m['name']),
                    PolicyName='{}DynamoScaleReadPolicy'.format(m['name']),
                    PolicyType='TargetTrackingScaling',
                    ScalingTargetId=Ref(read_target),
                    TargetTrackingScalingPolicyConfiguration=TargetTrackingScalingPolicyConfiguration(  # noqa
                        TargetValue=self.scaling_params[
                            'read']['target'],
                        ScaleInCooldown=self.scaling_params[
                            'read']['in_cooldown'],
                        ScaleOutCooldown=self.scaling_params[
                            'read']['out_cooldown'],
                        PredefinedMetricSpecification=PredefinedMetricSpecification(  # noqa
                            PredefinedMetricType="DynamoDBReadCapacityUtilization" # noqa
                        )
                    )
                ))

        return tbl

    def output_table(self):
        return "{}{}Table".format(self.stack.get_stack_name(), self.name)

    def output_table_arn(self):
        return "{}{}TableArn".format(self.stack.get_stack_name(), self.name)

    def output_stream(self):
        return "{}{}TableStreamArn".format(
            self.stack.get_stack_name(), self.name)


class DynamoDBStack(BaseStack):

    def __init__(self, name, **kwargs):
        super(DynamoDBStack, self).__init__('DynamoDB', 100)
        self.stack_name = name
        self.tables = []
        self.scaling_iam_role = None

    def add_table(self, table):
        table.stack = self
        self.tables.append(table)
        return table

    def build_template(self):

        t = self._init_template()

        for tbl in self.tables:
            tbl.build_table(t)

        if len(self.tables) > 10:

            # chunk the tables into groups of 10
            chunks = []
            copied = list(sorted(self.tables))
            while copied:
                chunks.append(list(copied[:10]))
                copied = copied[10:]

            # for each chunk (after the first one) make each table 'DependsOn'
            # a table in the previous group
            for i in range(len(chunks)):
                if i > 0:
                    for tab in chunks[i]:
                        tab.resource.DependsOn = \
                            chunks[i - 1][0].resource.name
        return t
