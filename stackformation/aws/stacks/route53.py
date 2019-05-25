from stackformation import (BaseStack)
from stackformation.aws.stacks import (eip, rds)
from stackformation.utils import ensure_param
import inflection
import re
from troposphere import route53
from troposphere import (  # noqa
    FindInMap, GetAtt, Join,
    Parameter, Output, Ref,
    Select, Tags, Template,
    GetAZs, Export
)


class Record(object):

    def __init__(self, name, value, **kw):

        self.name = name
        self.value = value
        self.ttl = kw.get('ttl', str(3600))
        self.stack = None
        self.weight = kw.get('weight', 0)
        self.type = None

    def _safe_dns_name(self, name):
        return name.replace(".", "")

    def add_to_template(self, template):

        res = self.value

        if not isinstance(res, list):
            res = [res]

        record = route53.RecordSet(
            '{}ARecord'.format(self._safe_dns_name(self.name)),
            Name="{}{}.".format(self.name, self.stack.domain_name),
            Type=self.type,
            TTL=self.ttl,
            ResourceRecords=res
        )

        return record

class ARecord(Record):

    def __init__(self, name, value, **kw):
        super().__init__(name, value, **kw)
        self.type = "A"




class GoogleMX(Record):

    def __init__(self, name, **kw):

        super().__init__(name, [
            '1 ASPMX.L.GOOGLE.COM.',
            '5 ALT1.ASPMX.L.GOOGLE.COM.',
            '5 ALT2.ASPMX.L.GOOGLE.COM.',
            '10 ALT3.ASPMX.L.GOOGLE.COM.',
            '10 ALT4.ASPMX.L.GOOGLE.COM.'
        ], **kw)
        self.type='MX'


class Elb(Record):

    def add_to_template(self, t):
        """
        """
        zone_param = ensure_param(t, self.value.output_hosted_zone(), 'String')
        dns_param = ensure_param(t, self.value.output_dns_name(), 'String')
        r = route53.RecordSet(
            '{}ELBRecord'.format(self._safe_dns_name(self.name)),
            Name="{}{}".format(self.name, self.stack.domain_name),
            Type="A",
            AliasTarget=route53.AliasTarget(
                HostedZoneId=Ref(zone_param),
                DNSName=Ref(dns_param)
            )
        )

        return r

class CName(Record):

    def __init__(self, name, value, **kw):
        super().__init__(name, value, **kw)
        self.type = 'CNAME'


class Rds(CName):

    def add_to_template(self, t):

        dns_param = ensure_param(t, self.value.output_endpoint(), 'String')
        r = route53.RecordSet(
            '{}RDSRecord'.format(self._safe_dns_name(self.name)),
            Name="{}{}".format(self.name, self.stack.domain_name),
            Type="CNAME",
            TTL=self.ttl,
            ResourceRecords=[Ref(dns_param)]
        )

        return r

class Txt(Record):

    def __init__(self, name, value, **kw):
        super().__init__(name, value, **kw)
        self.type = 'TXT'


class Route53Stack(BaseStack):

    def __init__(self, name, domain_name, **kw):

        super(Route53Stack, self).__init__('Route53', 900)

        self.stack_name = name
        self.domain_name = domain_name
        self.vpc = kw.get('vpc', None)
        self.records = []

    def add_record(self, record):
        record.stack = self
        self.records.append(record)
        return record

    def add_a(self, name, ip, **kw):
        a = ARecord(name, ip, **kw)
        self.add_record(a)
        return a

    def add_alias(self, name, stack, **kw):
        pass

    def add_google_mx(self, name, **kw):
        g = GoogleMX(name)
        self.add_record(g)
        return g

    def add_elb(self, name, stack, **kw):
        elb = Elb(name, stack, **kw)
        self.add_record(elb)
        return elb

    def add_cname(self, name, value, **kw):
        c = CName(name, value, **kw)
        self.add_record(c)
        return c

    def add_txt(self, name, value, **kw):
        txt = Txt(name, value, **kw)
        self.add_record(txt)
        return txt

    def add_rds(self, name, stack, **kw):
        """
        """
        rds = Rds(name, stack, **kw)
        self.add_record(rds)
        return rds

    def _safe_name(self, name):
        """
        """
        return inflection.camelize(name.replace('.', '_'))

    def build_template(self):
        t = self._init_template()

        zone = t.add_resource(route53.HostedZone(
            "{}HostedZone".format(self.name),
            Name=self.domain_name
        ))

        if self.vpc:
            vpc_param = ensure_param(t, self.vpc.output_vpc())
            zone.VPCs = [
                route53.HostedZoneVPCs(
                    VPCId=Ref(vpc_param),
                    VPCRegion=Ref("AWS::Region")
                )
            ]

        group = t.add_resource(route53.RecordSetGroup(
            "{}RecordGroup".format(self.name),
            HostedZoneId=Ref(zone),
            DependsOn=zone,
            RecordSets=[
                rs.add_to_template(t)
                for rs in self.records
            ]))


        return t
