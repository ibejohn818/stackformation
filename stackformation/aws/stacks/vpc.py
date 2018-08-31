from stackformation.aws.stacks import BaseStack, SoloStack
from stackformation.aws.stacks import (eip)
from troposphere import (ec2, iam)  # noqa
import awacs  # noqa
from awacs import aws  # noqa
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)
import inflection
import ipaddress

MIN_HOSTS = 16


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
    """Self Referenced security group. Will allow full access
    to resources which share this security group
    """

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

    def __init__(self, name=''):

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
    """The VPC Stack will create the VPC and public/private
    subnet for each AZ (Based on the number of AZ's specified ).
    In addition, a routetable for public-subnets and a routetable
    for private-subnets will be created.

    Public Subnet = Subnet with routetable that routes
    all traffic to an internet gateway and has 'allocate_public_ip'
    set to True.
    Private Subnet = Subnet with routetable that does not
    route all traffic to an internet gateway. In the case
    a Nat-Gateway is chosen, egress traffic only will be routed
    thorugh the Nat-Gateway.

    The VPC Base CIDR will be a /16 and each subnet /23

    A single ACL table will be created with default rules
    The default rules will allow all traffic and ephermaal
    port in/out of the VPC. You can overwrite these default
    rules to be more specific.

    # TODO(john@johnchardy.com): create methods to create custom ACL tables
    and methods to associate them with subnets

    Security groups are also created in the VPC stack.

    # TODO(john@johnchardy.com): Create SecurityGroup and
    Routes/Acls stacks for large VPC with many resources
    """

    def __init__(self, **kwargs):

        super(VPCStack, self).__init__("VPC", 1)
        config = {
            'private_subnets': 2,
            'public_subnets': 2,
            'subnet_mask': 24,
            'base_ip': '10.10'
        }
        config.update(kwargs)
        self.conf = config
        self.stack_name = ''
        self.security_groups = []
        self.nat_eip = None
        self.enable_dns = True,
        # bool: enable internal DNS Hostname resolution. Default is True
        self.enable_dns_hostnames = True
        # bool: add nat-gateway to private subnets and private routetable
        self.nat_gateway = False
        # int: the number of availability zones to build into the VPC
        self.num_azs = 2

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

    def add_nat_gateway(self, nat_eip):
        """Add nat-gateay to VPC

        Args:
            eip (:obj:`stackformation.aws.stacks.eip.EIP`): EIP For Nat-Gateway endpoint
        """  # noqa

        if not isinstance(nat_eip, (eip.EIP)):
            raise Exception("Natgateway Requires EIP Instance")

        self.nat_gateway = True
        self.nat_eip = nat_eip

    def add_security_group(self, secgroup):
        """Add security group to VPC

        Args:
            secgroup (:obj:`stackformation.aws.stacks.vpc.SecurityGroup`): Security Group to add to VPC
        """  # noqa

        if not isinstance(secgroup, SecurityGroup):
            raise Exception("Security group must extend SecGroup")

        secgroup.stack = self

        self.security_groups.append(secgroup)

        return secgroup

    def find_security_group(self, clazz, name=None):

        return self.find_class_in_list(self.security_groups, clazz, name)

    def get_subnet_ip(self, subnet_index):
        """
        Generate and return the next ip for the given
        subnet index

        Args:
            subnet_index (int): The subnet index

        Returns:
            string: IPv4
        """
        start = ipaddress.IPv4Address(self.get_base_ip())
        if subnet_index <= 0:
            return str(ipaddress.IPv4Address(start))
        else:
            # get current number of hosts
            current_num_hosts = self.calc_num_hosts(
                self.conf['subnet_mask']) * subnet_index
            # get the next host
            next = ipaddress.ip_address(str(start)) + current_num_hosts
            return str(next)

    def calc_num_hosts(self, netmask):
        """
        Return the number of hosts for given subnet mask
        * Subtract 2 (broadcast & gateway) and 3
        (AWS Usage https://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/VPC_Subnets.html#VPC_Sizing)
        to get total number of 'usable' hosts.

        Args:
            netmask (int): Subnet mask

        Returns:
            int: Total number of hosts
        """
        hosts = 2**(32 - int(netmask))
        if hosts < MIN_HOSTS:
            raise Exception("CALC HOSTS ERROR: AWS VPC does not support netmasks with less-than {} hosts".format(MIN_HOSTS))  # noqa
        return hosts

    def get_base_ip(self):
        return "{}.0.0".format(self.conf['base_ip'])

    def build_template(self):

        t = self._init_template()

        # add az outputs
        for i in range(0, self.num_azs):
            t.add_output([
                Output(
                    'AZ{}'.format(i + 1),
                    Value=Select(str(i), GetAZs(Ref("AWS::Region")))
                )
            ])

        # add vpc
        vpc = t.add_resource(ec2.VPC(
            "VPC",
            CidrBlock="{}/16".format(self.get_base_ip()),
            EnableDnsSupport="true" if self.enable_dns else "false",
            EnableDnsHostnames="true" if self.enable_dns_hostnames else "false",  # noqa
            Tags=Tags(
                Name=inflection.humanize(inflection.underscore(self.get_stack_name()))  # noqa
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

        t.add_resource(ec2.VPCGatewayAttachment(
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

        pub_subs = [
            str(i)
            for i in range(0, self.conf['public_subnets'] * 2, 2)
        ]
        for k, i in enumerate(pub_subs):

            subnet_ip = self.get_subnet_ip(int(i))
            sn = t.add_resource(ec2.Subnet(
                "PublicSubnet{}".format(i),
                VpcId=Ref(vpc),
                AvailabilityZone=Select(k, GetAZs("")),
                MapPublicIpOnLaunch=True,
                CidrBlock="{}/{}".format(subnet_ip, self.conf['subnet_mask']),
                Tags=Tags(
                    Name="PublicSubnet{}".format(i)
                )
            ))
            self.subnets['public'].append(sn)

            # associate route table
            t.add_resource(ec2.SubnetRouteTableAssociation(
                'PublicSubnetAssoc{}'.format(i),
                RouteTableId=Ref(public_route_table),
                SubnetId=Ref(sn)
            ))
            # associate acl
            t.add_resource(ec2.SubnetNetworkAclAssociation(
                'PublicSubnetAcl{}'.format(i),
                SubnetId=Ref(sn),
                NetworkAclId=Ref(default_acl_table)
            ))
            t.add_output([
                Output(
                    'PublicSubnet{}'.format(i),
                    Value=Ref(sn)
                )
            ])

        priv_subs = [
            str(i + 1)
            for i in range(0, self.conf['private_subnets'] * 2, 2)
        ]

        for k, i in enumerate(priv_subs):

            subnet_ip = self.get_subnet_ip(int(i))
            sn = t.add_resource(ec2.Subnet(
                "PrivateSubnet{}".format(i),
                VpcId=Ref(vpc),
                AvailabilityZone=Select(k, GetAZs("")),
                CidrBlock="{}/{}".format(subnet_ip, self.conf['subnet_mask']),
                Tags=Tags(
                    Name="PrivateSubnet{}".format(i)
                )
            ))
            self.subnets['private'].append(sn)

            # associate route table
            t.add_resource(ec2.SubnetRouteTableAssociation(
                'PrivateSubnetAssoc{}'.format(k),
                RouteTableId=Ref(private_route_table),
                SubnetId=Ref(sn)
            ))
            # associate acl
            t.add_resource(ec2.SubnetNetworkAclAssociation(
                'PrivateSubnetAcl{}'.format(k),
                SubnetId=Ref(sn),
                NetworkAclId=Ref(default_acl_table)
            ))
            t.add_output([
                Output(
                    'PrivateSubnet{}'.format(i),
                    Value=Ref(sn)
                )
            ])

        if self.nat_gateway:

            # nat EIP Allocation ID Param
            nat_eip_param = t.add_parameter(Parameter(
                self.nat_eip.output_allocation_id(),
                Type='String',
                Description='Nat Gateway EIP'
            ))

            # Nat Gateway Resource
            nat_gw = t.add_resource(ec2.NatGateway(
                "{}NatGateway".format(self.stack_name),
                AllocationId=Ref(nat_eip_param),
                SubnetId=Ref(self.subnets['public'][0]),
                Tags=Tags(
                    Name="{} Nat-Gateway".format(self.stack_name)
                )
            ))

            # Create route in private route-table
            t.add_resource(ec2.Route(
                'NatGatewayRoute',
                DestinationCidrBlock='0.0.0.0/0',
                NatGatewayId=Ref(nat_gw),
                RouteTableId=Ref(private_route_table)
            ))

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
            for i in range(0, self.num_azs)
        ]

    def output_private_subnets(self):
        return [
            "{}PrivateSubnet{}".format(self.get_stack_name(), i + 1)
            for i in range(0, self.conf['public_subnets'] * 2, 2)
        ]

    def output_public_subnets(self):
        return [
            "{}PublicSubnet{}".format(self.get_stack_name(), i)
            for i in range(0, self.conf['private_subnets'] * 2, 2)
        ]

    def output_vpc(self):
        return "{}VpcId".format(self.get_stack_name())


class VPCPeeringStack(BaseStack):
    """Create VPC Peering connections
    """

    def __init__(self, name=""):

        self.stack_name = name
        super(VPCPeeringStack, self).__init__('VPCPeering', 30)

        self.vpc_peers = []
        self.outputs = {}

    def add_peering(self, from_vpc, to_vpc, add_role=False):
        """Add VPC's to peer
        """

        peer = {
            'from_vpc': from_vpc,
            'to_vpc': to_vpc,
        }

        # for stack in peer.items():
        # if not isinstance(stack, (VPCStack)):
        # raise Exception("Stack must be VPCStack: {}".format(stack.__name__))

        self.vpc_peers.append(peer)

        return peer

    def get_connection_output(self, from_vpc, to_vpc):
        output_name = "{}{}{}VpcPeerConn".format(
            self.get_stack_name(),
            from_vpc.from_vpc.get_stack_name(),
            to_vpc.to_vpc.get_stack_name()
        )
        return output_name

    def build_template(self):

        t = self._init_template()

        for peers in self.vpc_peers:
            # create iam role
            # if peers.add_role is True:
                # role = t.add_resource(iam.Role(
                    # "VPCPeerRole{}To{}".format(
                        # peers.from_stack.get_stack_name(),
                        # peers.to_stack.get_stack_name()
                    # ),
                    # AssumeRolePolicyDocument=aws.Policy(
                        # Statement=[
                            # aws.Statement(
                                # Action=[awacs.sts.AssumeRole],
                                # Effect=aws.Allow,
                                # Principal=aws.Principal(
                                    # "Service", ["lambda.amazonaws.com"])
                            # )
                        # ]
                    # ),
                    # Path="/",
                    # Policies=[

                    # ],
                    # ManagedProlicyArns=[
                    # ]
                # ))

            to_param = t.add_parameter(Parameter(
                peers['to_vpc'].output_vpc(),
                Type='String'
            ))
            from_param = t.add_parameter(Parameter(
                peers['from_vpc'].output_vpc(),
                Type='String'
            ))

            conn = t.add_resource(ec2.VPCPeeringConnection(
                "VPCPeer{}to{}".format(
                    peers['from_vpc'].get_stack_name(),
                    peers['to_vpc'].get_stack_name()
                ),
                VpcId=Ref(from_param),
                PeerVpcId=Ref(to_param),
                Tags=Tags(
                    Name='VPCPeer{}To{}'.format(
                        peers['from_vpc'].get_stack_name(),
                        peers['to_vpc'].get_stack_name()
                    )
                )
            ))

            output_name = "{}{}{}VpcPeerConn".format(
                self.get_stack_name(),
                peers['from_vpc'].get_stack_name(),
                peers['to_vpc'].get_stack_name()
            )

            t.add_output(Output(
                output_name,
                Value=Ref(conn)
            ))

        return t


class VPCRoutesStack(BaseStack):
    """Create additional VPC Routes
    """

    def __init__(self, vpc, name=""):
        super(VPCRoutesStack, self).__init__('VPCRoutes', 31)

        self.stack_name = name
        self.vpc = vpc
