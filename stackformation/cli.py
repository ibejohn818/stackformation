# -*- coding: utf-8 -*-

"""Console script for stackformation."""

import click
import imp
import stackformation.deploy as dep
import logging
import os
from stackformation.utils import (match_stack)
import jinja2
from colorama import Fore, Style, Back
import re
from pprint import pprint

INFRA_FILE = "infra.py"

HELP = {

    'images_build':"""
Select the image to build from your configured images in your {0} file.
If this is the first image being built it will automatically be made active.
If there are more than one builds present, make sure to mark the image --active/-a
if you wish for this to be the current build in-scope
""".format(INFRA_FILE)



}


@click.group()
@click.option("--infrafile", default=None)
def main(infrafile=None):

    if infrafile is not None:
        global INFRA_FILE
        INFRA_FILE = infrafile

    configure_logging()
    load_configuration()


@main.group()
def stacks():
    pass


@main.group()
def images():
    pass


@images.command(help="", name='list')
def list_images():

    infra = load_infra_file()

    images = infra.list_images()

    for image in images:

        click.echo('----------------')

        amis = image.query_amis()
        click.echo(
            "Name: {}{} ({}){}".format(
                Style.BRIGHT,
                image.name,
                len(amis),
                Style.RESET_ALL))
        if len(amis) <= 0:
            click.echo(
                "   {}No AMI's have been built{}".format(
                    Fore.RED, Style.RESET_ALL))
        else:
            for ami in amis:

                flag = ""
                flag_style = Fore.CYAN

                for t in ami['Tags']:
                    if t['Key'] == 'ACTIVE':
                        flag = "(ACTIVE)"
                        flag_style = Fore.GREEN

                click.echo(
                    "  Date: {} {}AMI: {}{}{}".format(
                        ami['CreationDate'],
                        flag_style,
                        ami['ImageId'],
                        flag,
                        Style.RESET_ALL))
        click.echo('----------------')

@images.command(help="", name='generate')
@click.argument("name", required=True)
def generate_image(name):

    infra = load_infra_file()

    images = infra.list_images()

    # for image in images:
    # if image.name.startswith(name):


@images.command(help=HELP['images_build'], name='build')
@click.argument("name", required=True)
@click.option('--active','-a', is_flag=True, default=False, help='Make image active')
def build_image(name, active):

    infra = load_infra_file()

    images = infra.list_images()

    results = []

    for image in images:
        if image.name.startswith(name):
            click.echo("Matched: {}".format(image.name))
            results.append(image)
    if active:
        click.echo("Images will be made active")

    click.confirm("Do you wish to build the matched images?", abort=True)

    for image in results:
        image.build(active)

@images.command(help="", name='activate')
@click.argument("name", required=True)
@click.option('--id', required=True)
def images_activate(name, id):


    infra = load_infra_file()

    images = infra.list_images()

    results = []

    for image in images:
        if name == image.name:
            result = image

    click.confirm("Make {} the active AMI for {}".format(id, result.name), abort=True)

    result.promote_ami(id)

    click.echo("{} Now active".format(id))


@stacks.command(name='list')
@click.argument('selector', nargs=-1)
def list_stack(selector=None):

    if len(selector) <= 0:
        selector = None

    infra = load_infra_file()

    stacks = infra.list_stacks()

    results = []

    for stack in stacks:
        if selector is None or match_stack(selector, stack):
            results.append(stack)

    stacks = results

    for stack in stacks:
        click.echo("{}Stack:{} {} {}[{}]{}".format(
            Style.BRIGHT,
            Style.RESET_ALL + Fore.GREEN,
            stack.get_stack_name(),
            Fore.YELLOW,
            stack.get_remote_stack_name(),
            Style.RESET_ALL
        ))
        click.echo("{}Type: {}{}{}".format(
            Style.BRIGHT,
            Style.RESET_ALL + Fore.CYAN,
            stack.__class__,
            Style.RESET_ALL
        ))


@stacks.command(help='Deploy stacks')
@click.argument('selector', nargs=-1)
def review(selector=None):

    if len(selector) <= 0:
        selector = None

    infra = load_infra_file()

    stacks = infra.list_stacks()

    results = []

    for stack in stacks:
        if match_stack(selector, stack):
            results.append(stack)

    for stack in results:
        stack.review(infra)


@stacks.command(help='Deploy stacks')
@click.argument('selector', nargs=-1)
def deploy(selector):

    selector = list(selector)

    infra = load_infra_file()

    deploy = dep.SerialDeploy()

    if not deploy.cli_confirm(infra, selector):
        exit(0)

    deploy.deploy(infra, selector)


@stacks.command(help='Destroy stacks')
@click.argument('selector', nargs=-1)
def destroy(selector):

    selector = list(selector)

    infra = load_infra_file()

    deploy = dep.SerialDeploy()

    if not deploy.cli_confirm(infra, selector, reverse=True):
        exit(0)

    deploy.destroy(infra, selector, reverse=True)


@stacks.command(help='Dump Cloudformation template')
@click.option("--yaml", is_flag=True, default=False)
@click.argument('selector', nargs=-1)
def template(selector, yaml):

    selector = list(selector)

    infra = load_infra_file()

    stacks = infra.list_stacks()

    results = []

    for stack in stacks:
        if match_stack(selector, stack):
            results.append(stack)

    for stack in results:

        t = stack.build_template()

        if yaml:
            print(t.to_yaml())
        else:
            print(t.to_json())


@stacks.command(help="List stack dependencies")
def dependencies():

    infra = load_infra_file()

    stacks = infra.list_stacks()

    env = jinja_env()

    results = []

    for stack in stacks:

        deps = infra.get_dependent_stacks(stack)

        result = {
            'Stack': (stack.get_stack_name(), str(stack).split(' ')[0][1:]),
            'Dependencies': [(k, str(v).split(' ')[0][1:]) for k, v in deps.items()]
        }
        results.append(result)

    t = env.get_template("stack-dependencies.j2")
    context = {
        'results': results
    }
    view = t.render(context)
    click.echo(view)


def load_configuration():

    HOME = os.environ['HOME']

    if HOME is None:
        raise Exception(
            "$HOME environment variable needs to be set to save configuration")


def jinja_env():

    path = os.path.dirname(os.path.realpath(__file__))

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(
            searchpath="{}/templates/".format(path)))

    return env


def load_infra_file():

    try:

        module = imp.load_source('deploy', INFRA_FILE)
        infra = module.infra

    except Exception as e:
        click.echo("Infra file ({}) not found!".format(INFRA_FILE))
        exit(1)

    return infra


def configure_logging():

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    stream = logging.StreamHandler()
    stream.setFormatter(
        logging.Formatter('%(levelname)s ➤ %(message)s'))
    logger.addHandler(stream)

    # config boto logger
    boto_silences = [
        'botocore.vendored.requests',
        'botocore.credentials',
    ]
    for name in boto_silences:
        boto_logger = logging.getLogger(name)
        boto_logger.setLevel(logging.WARN)


if __name__ == "__main__":
    main()
