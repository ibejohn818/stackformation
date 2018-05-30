from stackformation.aws.stacks import BaseStack
from troposphere import (sns, iam, dynamodb)
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

        """
        self.stack = None
        self.name = name
        self.key_schema = kwargs.get('key_schema')
        self.attrs = kwargs.get('attrs', [])
        self.read_units=1
        self.write_units=1
        self.use_table_name = False
        self.stream_spec = None

    def build_table(self, t):

        tbl = t.add_resource(dynamodb.Table(
            '{}Table'.format(self.name),
            ProvisionedThroughput=dynamodb.ProvisionedThroughput(
                ReadCapacityUnits=self.read_units,
                WriteCapacityUnits=self.write_units
            )
            ))

        if self.use_table_name:
            tbl.TableName = self.name


        tbl.KeySchema=[
            dynamodb.KeySchema(
                    AttributeName=v['name'],
                    KeyType=v['type']
                )
            for v in self.key_schema
        ]

        tbl.AttributeDefinitions=[
            dynamodb.AttributeDefinition(
                AttributeName=attr['name'],
                AttributeType=attr['type']
            )
            for attr in self.attrs
        ]

        tbl.GlobalSecondaryIndexes=[]

        if self.stream_spec:
            tbl.StreamSpecification=dynamodb.StreamSpecification(
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

        return tbl

    def output_table(self):
        return "{}{}Table".format(self.stack.get_stack_name(), self.name)

    def output_table_arn(self):
        return "{}{}TableArn".format(self.stack.get_stack_name(), self.name)

    def output_stream(self):
        return "{}{}TableStreamArn".format(self.stack.get_stack_name(), self.name)

class DynamoDBStack(BaseStack):

    def __init__(self, name, **kwargs):
        super(DynamoDBStack, self).__init__('DynamoDB', 100)
        self.stack_name = name
        self.tables = []

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
                        tab.table_resource.DependsOn = \
                            chunks[i-1][0].table_resource.name
        return t

