from stackformation.aws.stacks import (BaseStack)
from stackformation.utils import ensure_param
from troposphere import rds
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)

class RDSBase(BaseStack):

    def __init__(self, name, vpc, **kw):
        self.public = kw.get('public', False)
        self.vpc = vpc
        self.params = {}
        self.db_type = kw.get('db_type', None)
        self.db_version = kw.get('db_version', None)
        super(RDSBase, self).__init__(name, 700)

    def _db_params(self, t):

        params = t.add_resource(rds.DBParameterGroup(
            '{}RDSParamGroup'.format(self.stack_name),
            Family='{}{}'.format(self.db_type, self.db_version),
            Description="ParamGroup for {}".format(self.stack_name),
            Parameters=self.params
        ))
        return params

    def _subnet_group(self, t):

        if self.public:
            sn_list = self.vpc.output_public_subnets()
        else:
            sn_list = self.vpc.output_private_subnets()

        sn_group = t.add_resource(rds.DBSubnetGroup(
            '{}RDSSubnetGroup'.format(self.stack_name),
            DBSubnetGroupDescription='{} Subnet Group'.format(
                self.stack_name),
            SubnetIds=subnet_refs
        ))

        return sn_group


class RDSClusterStack(RDSBase):

    def __init__(self, name, vpc, **kw):

        super(RDSClusterStack, self).__init__('RDSCluster', vpc, **kw)
        self.stack_name = name
        self.vpc = vpc
        self.multiaz = False
        self.serverless = False

    def build_template(self):

        t = self._init_template()

        backup_retention = t.add_parameter(Parameter(
            'InputBackupRetentionPeriod',
            Type='String',
            Default='7'
        ))




        return t

class RDSStack(BaseStack):

    def __init__(self, name, vpc):

        super(RDSStack, self).__init__("RDS", 700)

        self.stack_name = name
        self.vpc = vpc
        self._db_type = None
        self._db_version = None
        self.public = False
        self.multiaz = False
        self.security_groups = []
        self.params = {}

    @property
    def db_type(self):
        return self._db_type

    @db_type.setter
    def db_type(self, val):
        self._db_type = val
        return self.db_type

    @property
    def db_version(self):
        return self._db_version

    @db_version.setter
    def db_version(self, val):
        self._db_version = val
        return self.db_version

    def add_security_group(self, sg):
        self.security_groups.append(sg)

    def output_instance(self):
        return "{}{}RDS".format(
            self.get_stack_name(),
            self.stack_name
        )

    def build_template(self):

        t = self._init_template()

        username = "dbadmin"
        passwd = "rdspasswd"

        instance_type = t.add_parameter(Parameter(
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
        if self.public:
            sn_list = self.vpc.output_public_subnets()

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
            Description="ParamGroup for {}".format(self.name),
            Parameters=self.params
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
            MasterUsername=username,
            MasterUserPassword=passwd,
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
