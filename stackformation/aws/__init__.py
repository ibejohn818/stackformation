import sys
import os
import stackformation
import inflection
import subprocess
import jinja2
import yaml
import json
import shlex
import logging


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

logger = logging.getLogger(__name__)


class PackerImage(object):

    ansible_dir = None
    ansible_roles = None

    def __init__(self, name):

        self.name = name
        self.roles = {}
        self.os_type = None
        self.boto_session = None
        self.stack = None
        self.base_path = None
        self.path = "./"
        self.builders = []
        self.provisioners = []

    def get_ssh_user(self):
        users = {
                'awslinux': 'ec2-user',
                'ubuntu': 'ubuntu'
                }

        return users[self.os_type]

    def add_builder(self, builder):
        self.builders.append(builder)

    def add_provisioner(self, provisioner):
        self.provisioners.append(provisioner)

    def generate_packer_file(self):

        packer = {
                'builders': self.builders,
                'provisioners': self.provisioners
                }

        return packer



    def generate_playbook(self):

        pb = {
                'name': '{} Playbook'.format(self.name),
                'become': 'Yes',
                'become_method': 'sudo',
                'roles': []
        }

        for role, data in self.roles.items():
            line = {
                    'role': role
                    }
            line.update(data['vars'])
            pb['roles'].append(json.dumps(line))

        return yaml.dump(pb, default_flow_style=False)

    def generate(self):

        self.save_packer_file()


    def save_packer_file(self):
        packer = self.generate_packer_file()
        file_name = "{}/packer.json".format(self.save_path())
        with open(file_name, "w") as f:
                f.write(json.dumps(packer, indent=True))

    def set_path(self, path):
        self.path = path

    def save_path(self):
        path = inflection.dasherize(self.name)
        path = "{}/{}".format(self.path.strip("/"), path)
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def get_full_path(self):
        dirname = inflection.camelize(self.name)
        return "{}/{}".format(self.base_path, dirname)

    def make_template_env(self, template_path):
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=template_path))
        return env

    def template_env(self):
        pass

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

        self.generate()

        cmd = "packer build -machine-readable {}/packer.json ".format(self.save_path())

        cmd = subprocess.Popen(shlex.split(cmd),
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE
                )

        while cmd.poll() is None:
            line = cmd.stdout.readline().decode('utf-8')
            if line is not None and len(line)>0:
                logger.info(line.strip())



    def describe(self):
        """Describe the image build
        """
        raise Exception("Must implement describe()")

    def get_ami(self):
        raise Exception("Must implement get_ami()")
