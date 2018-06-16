import os
import stackformation
import inflection
import subprocess
import jinja2
import yaml
import json
import shlex
import logging
import time
import jmespath

CWD = os.path.realpath(os.path.dirname(stackformation.__file__)).strip('/')


ANSIBLE_INSTALL = {
    'ubuntu': [
        'sleep 90',
        'while ! grep "Cloud-init .* finished" /var/log/cloud-init.log; do',
        'echo "$(date -Ins) Waiting for cloud-init to finish"',
        'sleep 10',
        'done',
        'while fuser /var/lib/dpkg/lock >/dev/null 2>&1; do',
        'echo " Waiting for other software managers to finish..."',
        'sleep  5',
        'done',
        'sudo rm /var/lib/dpkg/lock',
        'sudo apt-get update ',
        'sudo apt-get install -y ansible',
    ],
    'awslinux': [
        'sudo yum-config-manager --enable epel',
        'sudo yum install -y git gcc make python-setuptools lib-tool',
        'sudo easy_install pip',
        'sudo pip install ansible'
    ]
}


AMI_INFO = {
    'ubuntu': {
        'username': 'ubuntu',
        'ami_filters': [
            {
                'Name': 'name',
                'Values': ['Ubuntu*16*']
            },
        ]
    },
    'awslinux': {
        'username': 'ec2-user',
        'ami_filters': [
            {
                'Name': 'name',
                'Values': ['amzn-ami*x86_64-gp2']
            },
            {
                'Name': 'description',
                'Values': ["*Linux*"]
            },
        ]
    }
}

logger = logging.getLogger(__name__)


class PackerImage(object):
    """Base class to launch an AMI build with Hashicorp Packer

    Attributes:
        ANSIBLE_DIR (str): Path the the ansible directory. Reference ansible best-practices for directory layout (http://docs.ansible.com/ansible/latest/playbooks_best_practices.html#directory-layout)
        ANSIBLE_ROLES (list[str]): List of paths to invidual roles.
    """  # noqa

    ANSIBLE_DIR = None
    ANSIBLE_ROLES = None

    def __init__(self, name):

        self.name = name
        self.roles = []
        self.os_type = None
        self.boto_session = None
        self.stack = None
        self.base_path = None
        self.path = "./__packer__"
        self.builders = []
        self.provisioners = []
        self.promote = False
        self._ami = None

    def get_ssh_user(self):
        users = {
            'awslinux': 'ec2-user',
            'ubuntu': 'ubuntu',
            'centos': 'root',
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
            'hosts': 'all',
            'roles': []
        }

        for role in sorted(self.roles, key=lambda e: e['weight']):
            line = {
                'role': role['role']
            }
            line.update(role['vars'])
            pb['roles'].append(line)

        return yaml.dump([pb], default_flow_style=False, indent=2)

    def save_playbook(self):
        pb = self.generate_playbook()
        file_name = '{}/playbook.yaml'.format(self.save_path())
        with open(file_name, "w") as f:
            f.write(pb)

    def generate(self):

        self.save_packer_file()
        self.save_playbook()

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
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(
                searchpath=template_path))
        return env

    def add_role(self, role_name, vars={}, weight=900):
        """Add ansible role to image

        Args:
            role_name (str): the name of the role
            vars (dict}: dict of role variables

        """
        new = {
            'role': role_name,
            'vars': vars,
            'weight': weight
        }
        self.roles.append(new)

    def del_role(self, role_name):
        if role_name in self.roles:
            del self.roles[role_name]

    def describe(self):
        """Describe the image build
        """
        raise Exception("Must implement describe()")

    def build(self):
        raise Exception("Must implement build()")

    def get_ami(self):
        raise Exception("Must implement get_ami()")


class Ami(PackerImage):

    def __init__(self, name, os_type='awslinux'):

        super(Ami, self).__init__(name)
        self.os_type = os_type
        self.base_ami_info = None

    def get_base_ami(self):
        """
        Get the latest AWS Linux AMI based on
        the creation date

        Args:
            botoKwargs (dict): the boto3 client kwargs

        Returns:
            amiid (str): The AWS Linux AmiID
        """

        filters = [
            {
                'Name': 'architecture',
                'Values': ["x86_64"]
            },
            {
                'Name': 'root-device-type',
                'Values': ["ebs"]
            },
            {
                'Name': 'virtualization-type',
                'Values': ["hvm"]
            },
            {
                'Name': 'state',
                'Values': ['available']
            },
            {
                'Name': 'ena-support',
                'Values': ['true']
            },
            {
                'Name': 'image-type',
                'Values': ['machine']
            },
            {
                'Name': 'is-public',
                'Values': ['true']
            },
        ]

        filters.extend(AMI_INFO[self.os_type]['ami_filters'])

        amis_query = self.boto_session.client(
            "ec2").describe_images(Filters=filters)

        # sort by CreationDate
        amis_query['Images'].sort(
            key=lambda item: item['CreationDate'],
            reverse=True)

        ami = amis_query['Images'][0]

        self.base_ami_info = ami

        return ami['ImageId']

    def get_ami(self):

        if self._ami is None:

            ec2 = self.boto_session.client('ec2')

            f = [
                {'Name': 'tag:ID',
                 'Values': [self.name]},
                {'Name': 'tag:ACTIVE',
                 'Values': ['YES']}
            ]

            try:
                ami = ec2.describe_images(Owners=['self'], Filters=f)
            except Exception as e:
                print(str(e))
                print("Error with AMI Query")

            if len(ami['Images']) <= 0:
                print(
                    "No active images have been created. Build an image and make --active")  # noqa
                self._ami = ''
                return ''
            self._ami = ami['Images'][0]['ImageId']

        return self._ami

    def get_vpc_id(self):

        ec2 = self.boto_session.client('ec2')

        f = [
            {'Name': 'is-default', 'Values': ['true']}
        ]

        vpc = ec2.describe_vpcs(Filters=f)

        return vpc['Vpcs'][0]['VpcId']

    def generate(self):

        self.region = self.boto_session.get_conf('region_name')

        aws_builder = {
            'type': 'amazon-ebs',
            'source_ami': self.get_base_ami(),
            'instance_type': 't2.medium',
            'communicator': 'ssh',
            'ssh_pty': 'true',
            'ssh_username': self.get_ssh_user(),
            'ami_name': "AMI {} {}".format(self.name, int(time.time())),
            'region': self.region,
            'vpc_id': self.get_vpc_id()

        }

        shell = {
            'type': 'shell',
            'inline': ANSIBLE_INSTALL[self.os_type]
        }

        ansible = {
            'type': 'ansible-local',
            'playbook_file': "{}/playbook.yaml".format(self.save_path())
        }

        if Ami.ANSIBLE_DIR:
            ansible['playbook_dir'] = Ami.ANSIBLE_DIR

        if Ami.ANSIBLE_ROLES:
            if not isinstance(Ami.ANSIBLE_ROLES, (list)):
                Ami.ANSIBLE_ROLES = [Ami.ANSIBLE_ROLES]
            ansible['role_paths'] = Ami.ANSIBLE_ROLES

        self.add_builder(aws_builder)
        self.add_provisioner(shell)
        self.add_provisioner(ansible)

        return super(Ami, self).generate()

    def build(self, active=False, memo=''):

        self.generate()

        cmd = "packer build -machine-readable {}/packer.json ".format(
            self.save_path())

        cmd = subprocess.Popen(shlex.split(cmd),
                               stderr=subprocess.PIPE,
                               stdout=subprocess.PIPE
                               )

        while cmd.poll() is None:
            line = cmd.stdout.readline().decode('utf-8')
            if line is not None and len(line) > 0:

                msg = line.strip().split(",")

                if msg[2] == 'ui':
                    out = msg[4]
                elif msg[2] == 'artifact':
                    if msg[4] == 'id':
                        ami = msg[5].strip().split(":")

                # logger.info("RAW: {}".format("|".join(msg)))

                logger.info(out.replace("%!(PACKER_COMMA)", ","))

        if cmd.returncode != 0:
            raise Exception("AMI BUILD FAILED")

        logger.info("AMI: {}".format(ami[1]))

        # check if there are AMI's
        # if there are none present, make the
        # first one always active
        if not active:
            ami_len = self.query_amis()
            if len(ami_len) <= 0:
                active = True

        self.tag_ami([ami[1]], memo)

        if active:
            logger.info("SETTING AMI TO ACTIVE:YES")
            self.promote_ami(ami[1])

    def promote_ami(self, ami_id):

        f = [
            {'Name': 'tag:ID',
             'Values': [self.name]}
        ]

        ec2 = self.boto_session.client('ec2')

        try:
            amis = ec2.describe_images(Owners=['self'], Filters=f)
            ids = jmespath.search('Images[].ImageId', amis)
            if len(ids) > 0:
                ec2.delete_tags(Resources=ids, Tags=[{'Key': 'ACTIVE'}])
        except Exception as e:
            print(str(e))

        ec2.create_tags(Resources=[ami_id], Tags=[
                        {'Key': 'ACTIVE', 'Value': 'YES'}])

        return ids

    def tag_ami(self, ami_ids, memo=''):

        ec2 = self.boto_session.client('ec2')

        if not isinstance(ami_ids, list):
            ami_ids = [ami_ids]

        params = {
            'Resources': ami_ids,
            'Tags': [
                {'Key': 'ID', 'Value': self.name},
                {'Key': 'OS', 'Value': self.os_type},
                {'Key': 'STACKFORMATION', 'Value': 'STACKFORMATION'},
            ]
        }

        if len(memo) > 0:
            params['Tags'].append({
                'Key': 'MEMO',
                'Value': memo
            })

        ec2.create_tags(**params)

    def query_amis(self):

        ec2 = self.boto_session.client('ec2')

        f = [
            {'Name': 'tag:ID',
             'Values': [self.name]}
        ]

        try:
            amis = ec2.describe_images(Owners=['self'], Filters=f)
        except Exception as e:
            print(str(e))

        return sorted(amis['Images'], key=lambda e: e['CreationDate'])

    def delete(self, ami_id=None):

        if not isinstance(ami_id, list):
            ami_id = [ami_id]

        ec2 = self.boto_session.client('ec2')

        ami = ec2.describe_images(ImageIds=ami_id)

        if len(ami['Images']) <= 0:
            return False

        ami = ami['Images'][0]

        ec2.deregister_image(ImageId=ami['ImageId'])

        if ami['RootDeviceType'] == 'ebs':
            for snap_id in [bdm['Ebs']['SnapshotId'] for bdm in
                            ami['BlockDeviceMappings'] if 'Ebs' in bdm]:
                ec2.delete_snapshot(SnapshotId=snap_id)
