from stackformation.aws.stacks import TemplateComponent
from stackformation import utils


class UserData(TemplateComponent):

    def __init__(self, name):
        self.name = name

    def get_output_vars(self):
        pass


class CreateCommonDirs(UserData):

    def __init__(self, name):
        super(CreateCommonDirs, self).__init__(name)

    def render(self):
        return """
mkdir -p /opt/stackformation/serf || true
        """


class CustomUserData(UserData):

    def __init__(self, name, text):

        super(CustomUserData, self).__init__(name)

        self.text = text

    def render(self):
        return text


class WriteEIP(UserData):

    def __init__(self, eip):

        super(WriteEIP, self).__init__("EIP_UserData")

        self.eip = eip

    def render(self):

        return """
echo {{context('%s')}} >> /tmp/testip
        """ % self.eip.output_eip()


class EIPInfo(UserData):

    def __init__(self, eip):
        super(EIPInfo, self).__init__("EIP Info")

        self.eip = eip

    def render(self):
        return """
echo {{{{context('{0}')}}}} >  /opt/ip.eip
echo {{{{context('{1}')}}}} >  /opt/allocation.eip
    """.format(
            self.eip.output_eip(),
            self.eip.output_allocation_id()
        )


class MountEBS(UserData):

    def __init__(self, ebs_volume, path):
        self.ebs_volume = ebs_volume
        self.path = path

    def render(self):

        return """
if file -sL {{{{context('Input{0}EBSDeviceName')}}}} | grep -vq ext4; then
    mkfs.ext4 {{{{context('Input{0}EBSDeviceName')}}}}
fi
mkdir -p {1}
echo '{{{{context('Input{0}EBSDeviceName')}}}} {1} ext4 defaults,nofail 0 2' >> /etc/fstab
mount -a
        """.format(self.ebs_volume.name, self.path)
