from stackformation.base import BaseStack, SoloStack
from troposphere import ec2
from troposphere import (
        FindInMap, GetAtt, Join,
        Parameter, Output, Ref,
        Select, Tags, Template,
        GetAZs, Export
)


class VpcStack(BaseStack, SoloStack):

    def __init__(self, **kwargs):

        super(VpcStack, self).__init__("VPC", 1)

        # only one allowed per infra
        self.solo = True

        # defaults
        self.defaults = {
                'num_azs': 2,
                'nat_gateway': False
        }

        self.defaults.update(kwargs)

        self.route_tables = {
                'private':[],
                'public': []
        }

        self.subnets = {
                'private': [],
                'public': []
        }

        self.base_cidr = "10.0"

        self.default_acls = {}

        self.add_default_acl_in("HTTP", 80, 80, 6, False, 100)
        self.add_default_acl_in("HTTPS", 443, 443, 6, False, 100)
        self.add_default_acl_in("SSH", 22, 22, 6, False, 100)
        self.add_default_acl_in("ALLIN", -1, -1, 6, True, 100)

    def add_default_acl_in(self, service_name, port_a, port_b, proto, access, weight=100):
        """

        """
        self.default_acls.update({service_name: (
            port_a, port_b, proto, access, weight
        )})

    def build_template(self):

        t = self._init_template()

        # add az outputs
        for i in range(0, self.defaults['num_azs']):
            t.add_output([
                Output(
                    'AZ{}'.format(i+1),
                    Value=Select(str(i), GetAZs(Ref("AWS::Region")))
                )
            ])

        # add vpc
        vpc = t.add_resource(ec2.VPC(
            "VPC",
            CidrBlock="{}.0.0/16".format(self.base_cidr),
        ))


        t.add_output([
            Output(
                "VpcId",
                Value=Ref(vpc),
                Description="VPC Id"
            )
        ])

        igw = t.add_resource(ec2.InternetGateway(
                'InternetGateway',
                Tags=Tags(
                    Name='{}{}InternetGateway'.format(self.infra.prefix,self.infra.name)
                )
            ))

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


        public_route_table = t.add_resource(ec2.RouteTable(
            'PublicRouteTable',
            VpcId=Ref(vpc),
            Tags=Tags(
                Name="{}{}Public Route Table".format(self.infra.prefix, self.infra.name)
            )
        ))

        ## Attach internet gateway
        t.add_resource(ec2.Route(
            'IGWRoute',
            DestinationCidrBlock='0.0.0.0/0',
            GatewayId=Ref(igw),
            RouteTableId=Ref(public_route_table)
        ))

        private_route_table = t.add_resource(ec2.RouteTable(
            'PrivateRouteTable',
            VpcId=Ref(vpc),
            Tags=Tags(
                Name="{}{}Private Route Table".format(self.infra.prefix, self.infra.name)
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
            )
        ])


        default_acl_table = t.add_resource(ec2.NetworkAcl(
                "DefaultNetworkAcl",
                VpcId=Ref(vpc),
                Tags=Tags(
                    Name="Default ACL"
                )
            ))

        # Add default entries
        for k, v in self.default_acls.items():
            t.add_resource(ec2.NetworkAclEntry(
                'NetworkAclEntry{}'.format(k),
                Protocol=v[2],
                RuleAction='allowed',
                Egress=v[3],
                NetworkAclId=Ref(default_acl_table),
                RuleNumber=v[4],
                CidrBlock='0.0.0.0/0',
                PortRange=ec2.PortRange(From=v[0],To=v[1])
            ))


        # create public subnets
        cls_c = 0
        for i in range(self.defaults['num_azs']):
            cls_c += 1
            sn = t.add_resource(ec2.Subnet(
                'PublicSubnet{}'.format(i),
                VpcId=Ref(vpc),
                AvailabilityZone=Select(i, GetAZs(Ref("AWS::Region"))),
                CidrBlock="{}.{}.0/24".format(self.base_cidr, cls_c)
            ))
            self.subnets['public'].append(sn)

            # associate route table
            t.add_resource(ec2.SubnetRouteTableAssociation(
                'PublicSubnetAssoc{}'.format(i),
                RouteTableId=Ref(public_route_table),
                SubnetId=Ref(sn)
            ))
            t.add_output([
                Output(
                    'PublicSubnet{}'.format(i),
                    Value=Ref(sn)
                )
            ])


        # create private subnets
        for i in range(self.defaults['num_azs']):
            cls_c += 1
            sn = t.add_resource(ec2.Subnet(
                'PrivateSubnet{}'.format(i),
                VpcId=Ref(vpc),
                AvailabilityZone=Select(i, GetAZs(Ref("AWS::Region"))),
                CidrBlock="{}.{}.0/24".format(self.base_cidr, cls_c)
            ))
            self.subnets['private'].append(sn)

            # associate route table
            t.add_resource(ec2.SubnetRouteTableAssociation(
                'PrivateSubnetAssoc{}'.format(i),
                RouteTableId=Ref(private_route_table),
                SubnetId=Ref(sn)
            ))
            t.add_output([
                Output(
                    'PrivateSubnet{}'.format(i),
                    Value=Ref(sn)
                )
            ])


        return t

    def output_azs(self):
        return [
                    "{}AZ{}".format(self.get_stack_name(), i+1)
                    for i in range(0, self.defaults['num_azs'])
                ]

    def output_vpc(self):
        return "{}VpcId".format(self.get_stack_name())
