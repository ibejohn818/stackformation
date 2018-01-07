from stackformation.aws import (PackerImage, Ami)
import moto


def test_packer_image():

    pi = PackerImage("test")

    pi.os_type = 'ubuntu'
    assert pi.get_ssh_user() == 'ubuntu'
    pi.os_type = 'centos'
    assert pi.get_ssh_user() == 'root'
    pi.os_type = 'awslinux'
    assert pi.get_ssh_user() == 'ec2-user'
