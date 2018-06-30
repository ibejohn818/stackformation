from stackformation.aws.stacks import TemplateComponent


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
        return self.text


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
        super(MountEBS, self).__init__('MountEBS{}'.format(ebs_volume.name))
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
        """.format(self.ebs_volume.name, self.path)  # noqa


class SwapFile(UserData):

    def __init__(self, size='1G', filename='/swapfile'):
        self.size = size
        self.filename = filename
        super(SwapFile, self).__init__('SwapFile{}'.format(self.filename))

    def render(self):
        out = [
           '',
           '# Build & register swap file',
           'fallocate -l {} {}'.format(self.size, self.filename),
           'chmod 600 {}'.format(self.filename),
           'mkswap {}'.format(self.filename),
           'swapon {}'.format(self.filename),
           '',
        ]
        return '\n'.join(out)



class InstallSSMAgent(UserData):
    """Install the SSM Agent
    """

    def __init__(self):
        super(InstallSSMAgent, self).__init__("InstallSSMAgent")

    def render(self):
        return """
        if [ -d /etc/yum.repos.d ]; then
            yum install -y https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_amd64/amazon-ssm-agent.rpm
        else
            cd /tmp
            wget https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/debian_amd64/amazon-ssm-agent.deb
            dpkg -i amazon-ssm-agent.deb
            systemctl enable amazon-ssm-agent
        fi
"""  # noqa


class InstallCodeDeployAgent(UserData):

    def __init__(self, stack):
        self.stack = stack
        super(InstallCodeDeployAgent, self).__init__('InstallCodeDeployAgent')

    def render(self):
        # get the region from the stacks infra
        region = self.stack.infra.boto_session.get_conf('region_name')
        return """
        wget https://aws-codedeploy-%s.s3.amazonaws.com/latest/install -O /tmp/cd-install
        chmod +x /tmp/cd-install
        /tmp/cd-install auto
""" % (region) # noqa


class ECSJoinCluster(UserData):

    def __init__(self, ecs_cluster):

        name = "ECSJoin{}".format(ecs_cluster.name)

        super(ECSJoinCluster, self).__init__(name)

        self.ecs_cluster = ecs_cluster

    def render(self):
        return """
iptables -t nat -A PREROUTING -p tcp -d 169.254.170.2 --dport 80 -j DNAT --to-destination 127.0.0.1:51679
iptables -t nat -A OUTPUT -d 169.254.170.2 -p tcp -m tcp --dport 80 -j REDIRECT --to-ports 51679

if [ -d /etc/apt ]; then
    sh -c "echo 'net.ipv4.conf.all.route_localnet = 1' >> /etc/sysctl.conf"
    sysctl -p /etc/sysctl.conf
    echo "Ubuntu/Debian Save iptables"
    sh -c 'mkdir -p /etc/iptables'
    sh -c 'iptables-save > /etc/iptables/rules.v4'
fi

if [ -d /etc/yum.repos.d ]; then
    echo "Centos/RHEL Save iptables"
    sh -c 'iptables-save > /etc/sysconfig/iptables'
fi

echo 'Write ECS Config'
mkdir -p /etc/ecs
cat << EOF > /etc/ecs/ecs.config
ECS_DATADIR=/data
ECS_ENABLE_TASK_IAM_ROLE=true
ECS_ENABLE_TASK_IAM_ROLE_NETWORK_HOST=true
ECS_LOGFILE=/var/log/ecs-agent.log
ECS_AVAILABLE_LOGGING_DRIVERS=["json-file","awslogs"]
ECS_LOGLEVEL=info
ECS_CLUSTER={{{{context('{0}')}}}}
EOF
""".format(self.ecs_cluster.output_cluster())  # noqa
