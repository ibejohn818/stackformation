from stackformation.aws.stacks import (BaseStack)
from troposphere import rds
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)


class RDSStack(BaseStack):

    def __init__(self, name, vpc):

        super(RDSStack, self).__init__("RDS", 700)

        self.stack_name = name
        self.vpc = vpc
        self.db_type = None
        self.db_version = None
        self.public = False
        self.mutliaz = False
        self.security_groups = []

    def add_security_group(self, sg):
        self.security_groups.append(sg)

    def build_template(self):

        t = self._init_template()

        username = "rdsamdin"
        passwd = "rdspasswd"

        instance_type = t.add_parameters(Parameter(
            "Input{}RDSInstanceType".format(self.stack_name),
            Type='String',
            Default='db.t2.medium'
        ))

        instance_size = t.add_parameter(Parameter(
            "Input{}RDSSize".format(self.stack_name),
            Type='String',
            Default='20'
        ))

        storage_type = t.add_parameter(Parameter(
            "Input{}RDSStorageType".format(self.stack_name),
            Type='String',
            Default='gp2'
        ))

        backup_retention = t.add_parameter(Parameter(
            'InputBackupRetentionPeriod',
            Type='String',
            Default='7'
            ))

        sn_list = self.vpc.output_private_subnets()

        subnet_refs = [
                    Ref(
                        t.add_parameter(Parameter(
                            i,
                            Type='String'
                        ))
                    )
                    for i in sn_list
                ]

        sg_refs = [
                    Ref(
                        t.add_parameter(Parameter(
                            i.output_security_group(),
                            Type='String'
                        ))
                    )
                    for i in self.security_groups
                ]

        params = t.add_resource(rds.DBParameterGroup(
                    '{}RDSParamGroup'.format(self.stack_name),
                    Family='{}{}'.format(self.db_type, self.db_version),
                    Params=self.params
                ))

        sn_groups = t.add_resource(rds.DBSubnetGroup(
                        '{}RDSSubnetGroup'.format(self.stack_name),
                        DBSubnetGroupDescription='{} Subnet Group'.format(
                            self.stack_name),
                        SubnetIds=subnet_refs
                        ))

        db = t.add_resource(rds.DBInstance(
                    '{}RDSInstance'.format(self.stack_name),
                    AllocatedStorage=Ref(instance_size),
                    BackupRetentionPeriod=Ref(backup_retention),
                    DBInstanceClass=Ref(instance_type),
                    DBSubnetGroupName=Ref(sn_groups),
                    Engine=self.db_type,
                    EngineVersion=self.db_version,
                    DBParameterGroupName=Ref(params),
                    MasterUsername=Ref(username),
                    MasterUserPassword=Ref(passwd),
                    MultiAZ=self.multiaz,
                    PubliclyAccessible=self.public,
                    StorageType=Ref(storage_type),
                    VPCSecurityGroups=sg_refs,
                ))

        t.add_output([
            Output(
                '{}RDSInstance'.format(self.stack_name),
                Value=Ref(db)
            )
        ])

        return t
