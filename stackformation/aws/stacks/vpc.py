from stackformation.aws.stacks import BaseStack, SoloStack
from troposphere import ec2
from troposphere import (
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)
import inflection


class SecurityGroup(object):

    def __init__(self, name):
        self.name = name
        self.stack = None

    def _build_security_group(self, template, vpc):
        raise Exception("Must implement _build_security_group!")

    def _build_template(self, template, vpc):

        t = template
        sg = self._build_security_group(t, vpc)

        t.add_output([
            Output(
                '{}SecurityGroup'.format(self.name),
                Value=Ref(sg)
            )
        ])

    def output_security_group(self):
        return "{}{}SecurityGroup".format(
            self.stack.get_stack_name(),
            self.name
        )


class SelfReferenceSecurityGroup(SecurityGroup):

    def __init__(self):
        name = "SelfReferenceSecurityGroup"
        super(SelfReferenceSecurityGroup, self).__init__(name)

    def _build_security_group(self, t, vpc):

        sg = t.add_resource(
            ec2.SecurityGroup(
                '{}'.format(
                    self.name),
                GroupDescription="{} Self Reference Security Group".format(
                    self.stack.get_stack_name()),
                GroupName="{} {}".format(
                    self.stack.get_stack_name(),
                    self.name),
                VpcId=Ref(vpc),
                SecurityGroupIngress=[]))

        t.add_resource(ec2.SecurityGroupIngress(
            '{}Ingress'.format(self.name),
            ToPort='-1',
            FromPort='-1',
            IpProtocol='-1',
            SourceSecurityGroupId=Ref(sg),
            GroupId=Ref(sg),
        ))
        return sg


class SSHSecurityGroup(SecurityGroup):

    def __init__(self, name="SSH"):

        super(SSHSecurityGroup, self).__init__(name)

        self.allowed_cidrs = []
        self.ssh_port = 22

    def allow_cidr(self, cidr):
        self.allowed_cidrs.append(cidr)

    def _build_security_group(self, t, vpc):

        rules = []

        # if no cidrs were added add wildcard
        if len(self.allowed_cidrs) == 0:
            self.allow_cidr('0.0.0.0/0')

        for c in self.allowed_cidrs:
            rules.append(ec2.SecurityGroupRule(
                CidrIp=c,
                ToPort=self.ssh_port,
                FromPort=self.ssh_port,
                IpProtocol='tcp'
            ))

        sg = t.add_resource(ec2.SecurityGroup(
            '{}SecurityGroup'.format(self.name),
            GroupDescription="{} SSH Security Group".format(self.name),
            GroupName="{}SecurityGroup".format(self.name),
            VpcId=Ref(vpc),
            SecurityGroupIngress=rules
        ))

        return sg


class WebSecurityGroup(SecurityGroup):

    def __init__(self, name="Web"):

        super(WebSecurityGroup, self).__init__(name)

        self.allowed_cidrs = []

        self.http_port = 80
        self.https_port = 443

    def allow_cidr(self, cidr):
        self.allowed_cidrs.append(cidr)

    def _build_security_group(self, t, vpc):

        if len(self.allowed_cidrs) == 0:
            self.allow_cidr('0.0.0.0/0')

        rules = []

        for cidr in self.allowed_cidrs:
            rules.append(
                ec2.SecurityGroupRule(
                    CidrIp=cidr,
                    ToPort=self.http_port,
                    FromPort=self.http_port,
                    IpProtocol='tcp'
                )
            )
            rules.append(
                ec2.SecurityGroupRule(
                    CidrIp=cidr,
                    ToPort=self.https_port,
                    FromPort=self.https_port,
                    IpProtocol='tcp'
                )
            )

        sg = t.add_resource(ec2.SecurityGroup(
            "{}SecurityGroup".format(self.name),
            GroupName="{}SecurityGroup".format(self.name),
            GroupDescription="{} Web Security Group".format(self.name),
            VpcId=Ref(vpc),
            SecurityGroupIngress=rules
        ))

        return sg


class AllPortsSecurityGroup(SecurityGroup):

    def __init__(self, name):

        super(AllPortsSecurityGroup, self).__init__(name)

    def _build_security_group(self, template, vpc):

        t = template

        sg = t.add_resource(ec2.SecurityGroup(
            '{}AllPortsSecurityGroup'.format(self.name),
            VpcId=Ref(vpc),
            GroupName='{}AllPortsSecurityGroup'.format(self.name),
            GroupDescription="{} All Ports Security Group ".format(self.name),
            SecurityGroupIngress=[
                ec2.SecurityGroupRule(
                    CidrIp='0.0.0.0/0',
                    ToPort="-1",
                    FromPort="-1",
                    IpProtocol="-1"
                )
            ]
        ))

        return sg


class VPCStack(BaseStack, SoloStack):

    def __init__(self, **kwargs):

        super(VPCStack, self).__init__("VPC", 1)

        # defaults
        self.defaults = {
            'num_azs': 2,
            'nat_gateway': False
        }

        self.defaults.update(kwargs)

        self.security_groups = []
        self.base_cidr = "10.0"
        self.enable_dns = True,
        self.enable_dns_hostnames = True

        self.route_tables = {
            'private': [],
            'public': []
        }

        self.subnets = {
            'private': [],
            'public': []
        }

        self.default_acls = {}

        self.add_default_acl("HTTP", 80, 80, 6, 'false', 100)
        self.add_default_acl("HTTPS", 443, 443, 6, 'false', 101)
        self.add_default_acl("SSH", 22, 22, 6, 'false', 102)
        self.add_default_acl("SSH", 22, 22, 6, 'false', 103)
        self.add_default_acl("EPHEMERAL", 49152, 65535, 6, 'false', 104)
        self.add_default_acl("ALLIN", None, None, 6, 'true', 100)

    def add_default_acl(
            self,
            service_name,
            port_a,
            port_b,
            proto,
            access,
            weight=100):
        """

        """
        self.default_acls.update({service_name: (
            port_a, port_b, proto, access, weight
        )})

    def add_security_group(self, secgroup):

        if not isinstance(secgroup, SecurityGroup):
            raise Exception("Security group must extend SecGroup")

        secgroup.stack = self

        self.security_groups.append(secgroup)

        return secgroup

    def find_security_group(self, clazz, name=None):

        return self.find_class_in_list(self.security_groups, clazz, name)

    def build_template(self):

        t = self._init_template()

        # add az outputs
        for i in range(0, self.defaults['num_azs']):
            t.add_output([
                Output(
                    'AZ{}'.format(i + 1),
                    Value=Select(str(i), GetAZs(Ref("AWS::Region")))
                )
            ])

        # add vpc
        vpc = t.add_resource(ec2.VPC(
            "VPC",
            CidrBlock="{}.0.0/16".format(self.base_cidr),
            EnableDnsSupport="true" if self.enable_dns else "false",
            EnableDnsHostnames="true" if self.enable_dns_hostnames else "false",
            Tags=Tags(
                Name=inflection.humanize(inflection.underscore(self.get_stack_name()))
            )
        ))

        t.add_output([
            Output(
                "VpcId",
                Value=Ref(vpc),
                Description="VPC Id"
            )
        ])

        igw = t.add_resource(
            ec2.InternetGateway(
                'InternetGateway',
                Tags=Tags(
                    Name='{}{}InternetGateway'.format(
                        self.infra.prefix,
                        self.infra.name))))

        # t.add_output([
        # Output(
        # 'InternetGateway',
        # Value=Ref(igw),
        # Description="Internet Gateway"
        # )
        # ])

        igwa = t.add_resource(ec2.VPCGatewayAttachment(
            'InternetGatewayAttachment',
            VpcId=Ref(vpc),
            InternetGatewayId=Ref(igw)
        ))

        public_route_table = t.add_resource(
            ec2.RouteTable(
                'PublicRouteTable',
                VpcId=Ref(vpc),
                Tags=Tags(
                    Name="{} {}Public Route Table".format(
                        ''.join(
                            self.infra.prefix),
                        self.infra.name))))

        # Attach internet gateway
        t.add_resource(ec2.Route(
            'IGWRoute',
            DestinationCidrBlock='0.0.0.0/0',
            GatewayId=Ref(igw),
            RouteTableId=Ref(public_route_table)
        ))

        private_route_table = t.add_resource(
            ec2.RouteTable(
                'PrivateRouteTable',
                VpcId=Ref(vpc),
                Tags=Tags(
                    Name="{} {}Private Route Table".format(
                        ''.join(
                            self.infra.prefix),
                        self.infra.name))))

        default_acl_table = t.add_resource(ec2.NetworkAcl(
            "DefaultNetworkAcl",
            VpcId=Ref(vpc),
            Tags=Tags(
                Name="Default ACL"
            )
        ))

        t.add_output([
            Output(
                'PublicRouteTable',
                Value=Ref(public_route_table)
            ),
            Output(
                'PrivateRouteTable',
                Value=Ref(private_route_table)
            ),
            Output(
                'DefaultAclTable',
                Value=Ref(default_acl_table)
            )
        ])

        t.add_resource(ec2.NetworkAclEntry(
            'AclAllIn',
            Egress='false',
            NetworkAclId=Ref(default_acl_table),
            Protocol='-1',
            CidrBlock='0.0.0.0/0',
            RuleNumber='100',
            RuleAction='allow'
        ))

        t.add_resource(ec2.NetworkAclEntry(
            'AclAllOut',
            Egress='true',
            NetworkAclId=Ref(default_acl_table),
            Protocol='-1',
            CidrBlock='0.0.0.0/0',
            RuleNumber='100',
            RuleAction='allow'
        ))
        # Add default entries
        for k, v in self.default_acls.items():
            continue
            ae = t.add_resource(ec2.NetworkAclEntry(
                'NetworkAclEntry{}'.format(k),
                Protocol=v[2],
                RuleAction='allow',
                Egress=v[3],
                NetworkAclId=Ref(default_acl_table),
                RuleNumber=v[4],
                CidrBlock='0.0.0.0/0',
            ))
            if v[0] is not None and v[1] is not None:
                ae.PortRange = ec2.PortRange(From=v[0], To=v[1])

        # create public subnets
        cls_c = 0
        for i in range(self.defaults['num_azs']):
            cls_c += 1
            key = i + 1
            sname = 'PublicSubnet{}'.format(key)
            sn = t.add_resource(ec2.Subnet(
                sname,
                VpcId=Ref(vpc),
                AvailabilityZone=Select(i, GetAZs(Ref("AWS::Region"))),
                CidrBlock="{}.{}.0/24".format(self.base_cidr, cls_c),
                Tags=Tags(
                    Name=sname
                )
            ))
            self.subnets['public'].append(sn)

            # associate route table
            t.add_resource(ec2.SubnetRouteTableAssociation(
                'PublicSubnetAssoc{}'.format(key),
                RouteTableId=Ref(public_route_table),
                SubnetId=Ref(sn)
            ))
            # associate acl
            t.add_resource(ec2.SubnetNetworkAclAssociation(
                'PublicSubnetAcl{}'.format(key),
                SubnetId=Ref(sn),
                NetworkAclId=Ref(default_acl_table)
            ))
            t.add_output([
                Output(
                    'PublicSubnet{}'.format(key),
                    Value=Ref(sn)
                )
            ])

        # create private subnets
        for i in range(self.defaults['num_azs']):
            cls_c += 1
            key = i + 1
            sname = 'PrivateSubnet{}'.format(key)
            sn = t.add_resource(ec2.Subnet(
                sname,
                VpcId=Ref(vpc),
                AvailabilityZone=Select(i, GetAZs(Ref("AWS::Region"))),
                CidrBlock="{}.{}.0/24".format(self.base_cidr, cls_c),
                Tags=Tags(
                    Name=sname
                )
            ))
            self.subnets['private'].append(sn)

            # associate route table
            t.add_resource(ec2.SubnetRouteTableAssociation(
                'PrivateSubnetAssoc{}'.format(key),
                RouteTableId=Ref(private_route_table),
                SubnetId=Ref(sn)
            ))
            # associate acl
            t.add_resource(ec2.SubnetNetworkAclAssociation(
                'PrivateSubnetAcl{}'.format(key),
                SubnetId=Ref(sn),
                NetworkAclId=Ref(default_acl_table)
            ))
            t.add_output([
                Output(
                    'PrivateSubnet{}'.format(key),
                    Value=Ref(sn)
                )
            ])

        # build security groups
        for sg in self.security_groups:
            sg._build_template(t, vpc)

        return t

    def output_default_acl_table(self):
        return "{}DefaultAclTable".format(self.get_stack_name())

    def output_public_routetable(self):
        return "{}PublicRouteTable".format(self.get_stack_name())

    def output_private_routetable(self):
        return "{}PrivateRouteTable".format(self.get_stack_name())

    def output_azs(self):
        return [
            "{}AZ{}".format(self.get_stack_name(), i + 1)
            for i in range(0, self.defaults['num_azs'])
        ]

    def output_private_subnets(self):
        return [
            "{}PrivateSubnet{}".format(self.get_stack_name(), i + 1)
            for i in range(0, self.defaults['num_azs'])
        ]

    def output_public_subnets(self):
        return [
            "{}PublicSubnet{}".format(self.get_stack_name(), i + 1)
            for i in range(0, self.defaults['num_azs'])
        ]

    def output_vpc(self):
        return "{}VpcId".format(self.get_stack_name())
