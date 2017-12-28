
class PackerImage(object):

    def __init__(self, name):

        self.name = name
        self.roles = {}
        self.os_type = None
        self.boto_session = None
        self.stack = None

    def add_role(self, role_name, vars = {}):
        """Add ansible role to image

        Args:
            role_name (str): the name of the role
            vars (dict}: dict of role variables

        """
        self.roles.update({role_name: vars})

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
