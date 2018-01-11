from stackformation import (BaseStack)
from stackformation.aws.stacks import (eip)
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

    def __init__(self, name, value):

        self.name = name
        self.ttl = str(3600)
        self.stack = None
        self.weight = 0
        self.value = value

    def set_ttl(self, val):
        self.ttl = str(val)

    def _safe_dns_name(self, name):
        return name.replace(".", "")

    def _return_resource_param(self, template):

        param_type = ""
        param_name = ""

        if isinstance(self.value, eip.EIP):
            param_name = self.value.output_eip()
            param_type = "String"
        elif self._is_ip(self.value):
            input_name = "Input{}ARecordValue".format(self.stack.stack_name)
            self.stack.infra.add_var({
                input_name: self.value
            })
            param_name = input_name
            param_type = "String"

        return template.add_parameter(Parameter(
            param_name,
            Type=param_type
        ))

    def add_to_template(self, template):
        raise Exception("must implement add_to_template()")


class ARecord(Record):

    def _is_ip(self, ip):

        if not isinstance(ip, (str)):
            return False

        return re.match(
            '^([0-9]){,3}(\.)([0-9]){,3}(\.)([0-9]){,3}(\.)([0-9]){,3}$', ip)

    def add_to_template(self, template, zoneRecord):

        record = route53.RecordSet(
            '{}ARecord'.format(self._safe_dns_name(self.name)),
            Name="{}".format(zoneRecord.Name),
            Type="A",
            TTL=self.ttl,
            Weight=self.weight
        )

        param = self._return_resource_param(template)

        record.ResourceRecords = [Ref(param)]

        return record


class CName(object):
    pass


class Route53Stack(BaseStack):

    def __init__(self, domain_name):

        super(Route53Stack, self).__init__('Route53', 800)

        self.stack_name = inflection.camelize(domain_name.replace(".", "_"))
        self.domain_name = domain_name
        self.public = True
        self.records = []

    def add_record(self, record):
        record.stack = self
        self.records.append(record)

    def set_public(self, val):
        self.public = val

    def build_template(self):
        t = self._init_template()

        zone = t.add_resource(route53.HostedZone(
            '{}HostedZone'.format(self.stack_name),
            HostedZoneConfig=route53.HostedZoneConfiguration(
                Comment='{} DNS Hosted Zone'.format(self.domain_name)
            ),
            Name=self.domain_name
        ))

        t.add_output([
            Output(
                '{}HostedZone'.format(self.stack_name),
                Value=Ref(zone)
            )
        ])

        rs = []

        for r in self.records:
            rs.append(r.add_to_template(t, zone))

        t.add_resource(route53.RecordSetGroup(
            '{}RecordGroup'.format(self.stack_name),
            RecordSets=rs,
            HostedZoneId=Ref(zone)
        ))

        return t
