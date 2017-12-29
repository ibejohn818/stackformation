

DEFAULT_AMIS = {
    'us-east-1':{
        'awslinux': '',
        'ubuntu': ''
    },
    'us-east-2': {
        'awslinux': '',
        'ubuntu': ''
    },
    'us-west-1': {
        'awslinux': '',
        'ubuntu': ''
    },
    'us-west-2': {
        'awslinux': '',
        'ubuntu': ''
    },
}

class PackerImage(object):

    def __init__(self, name):

        self.name = name
        self.roles = {}
        self.os_type = None
        self.boto_session = None
        self.stack = None

    def get_base_ami(self):
        region = self.boto_session.get_conf('region')
        ami = DEFAULT_AMIS[region][self.os_type]
        return ami

    def add_role(self, role_name, vars = {}, weight=900):
        """Add ansible role to image

        Args:
            role_name (str): the name of the role
            vars (dict}: dict of role variables

        """
        self.roles.update({role_name: {'vars': vars, 'weight': weight}})

    def del_role(self, role_name):
        if role_name in self.roles:
            del self.roles[role_name]

    def build(self):
        """Abstract method to trigger the build
        """
        raise Exception("Need to implement build()")

    def describe(self):
        """Describe the image build
        """
        raise Exception("Must implement describe()")

    def get_ami(self):
        raise Exception("Must implement get_ami()")
