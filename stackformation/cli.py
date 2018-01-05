# -*- coding: utf-8 -*-

"""Console script for stackformation."""

import click
import imp
import stackformation.deploy as dep
import logging
import os
from stackformation.utils import (match_stack, match_image)
import jinja2
from colorama import Fore, Style
import jmespath
from stackformation import utils

INFRA_FILE = "infra.py"

HELP = {

    'images_build': """
Select the image to build from your configured images in your {0} file.
If this is the first image being built it will automatically be made active.
If there are more than one builds present, make sure to mark the image --active/-a
if you wish for this to be the current build in-scope
""".format(INFRA_FILE) # noqa



}


@click.group()
@click.option("--file-override", default=None)
def main(file_override=None):

    if file_override is not None:
        global INFRA_FILE
        INFRA_FILE = file_override

    configure_logging()


@main.group()
def stacks():
    pass


@main.group()
def images():
    pass

@main.command()
def test():


    mod = load_infra_module()

    print(mod.Ami.ANSIBLE_DIR)

@images.command(help="List images", name='list')
def list_images():

    infra = utils.load_infra_module(INFRA_FILE).infra

    images = infra.list_images()

    for image in images:

        click.echo('------------------------')

        amis = image.query_amis()
        click.echo(
            "Name: {}{} ({}){}".format(
                Style.BRIGHT,
                image.name,
                len(amis),
                Style.RESET_ALL))
        click.echo('------------------------')
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


# @images.command(help="", name='generate')
# @click.argument("name", required=True)
# def generate_image(name):

    # infra = load_infra_file()

    # images = infra.list_images()

    # for image in images:
    # if image.name.startswith(name):


@images.command(help=HELP['images_build'], name='build')
@click.argument("name", default="")
@click.option(
    '--active',
    '-a',
    is_flag=True,
    default=False,
    help='Make image active')
def build_image(name=None, active=False):

    infra = utils.load_infra_module(INFRA_FILE).infra

    images = infra.list_images()

    results = []

    for image in images:
        if not name:
            results.append(image)
        elif match_image(name, image.name):
            results.append(image)

    for r in results:
        click.echo("Matched: {}".format(r.name))

    if len(results) <= 0:
        click.echo("No images")
        exit(0)

    if active:
        click.echo("Images will be made active")

    click.confirm("Do you wish to build the matched images?", abort=True)

    for image in results:
        image.build(active)


@images.command(help="", name='activate')
@click.argument("name", required=True)
@click.option('--id', required=True)
def images_activate(name, id):

    infra = utils.load_infra_module(INFRA_FILE).infra

    images = infra.list_images()

    result = False

    for image in images:
        if name == image.name:
            result = image

    if not result:
        click.echo("No image matching the given name")
        exit(1)

    click.confirm(
        "Make {} the active AMI for {}".format(
            id, result.name), abort=True)

    result.promote_ami(id)

    click.echo("{} Now active".format(id))


@images.command(help="", name='prune')
@click.argument("name", required=True)
@click.option('--force', is_flag=True, default=False,
              help="Force deletion of active AMI")
def images_prune(name, force):

    infra = utils.load_infra_module(INFRA_FILE).infra

    images = infra.list_images()

    result = False

    for image in images:
        if name == image.name:
            result = image

    if not result:
        click.echo("No image matching the given name")
        exit(1)

    click.confirm(
        "Prune all in-active images for {}".format(result.name), abort=True)

    amis = result.query_amis()

    if len(amis) <= 0:
        click.echo("No images available")
        exit(0)

    for ami in amis:
        if not force:
            chk = jmespath.search("Tags[?Key=='ACTIVE']", ami)
            if len(chk) > 0:
                continue
        click.echo("Deleting: {}".format(ami['ImageId']))
        result.delete(ami['ImageId'])


@stacks.command(name='list')
@click.argument('selector', nargs=-1)
@click.option("--dependencies","-d", is_flag=True, default=False)
@click.option("--remote","-r", is_flag=True, default=False)
def list_stack(selector=None, dependencies=False, remote=False):

    if len(selector) <= 0:
        selector = None
    else:
        selector = list(selector)

    infra = utils.load_infra_module(INFRA_FILE).infra

    stacks = infra.list_stacks()

    results = []

    for stack in stacks:
        if selector is None or match_stack(selector, stack):
            results.append(stack)

    stacks = results

    for stack in stacks:

        # ty = str(type(v)).split(" ")[1].strip(">")
        ty = type(stack).__name__
        rem = ""
        if remote:
            if stack.stack_info():
                rem = styled_bool(True)
            else:
                rem = styled_bool(False)

        click.echo("{}{} {} {}[{}] {}({}){}".format(
            rem,
            Style.BRIGHT+Fore.CYAN,
            stack.get_stack_name(),
            Fore.YELLOW,
            stack.get_remote_stack_name(),
            Style.RESET_ALL,
            ty,
            Style.RESET_ALL
        ))
        if dependencies:
            deps = infra.get_dependent_stacks(stack)
            if len(deps) > 0:
                for k, v in deps.items():
                    rem = "-"
                    if remote:
                        if v.stack_info():
                            rem = styled_bool(True)
                        else:
                            rem = styled_bool(False)
                    ty = type(v).__name__
                    click.echo("  {} {} ({})".format(rem, v.get_stack_name(), ty))

@stacks.command(help='Deploy stacks')
@click.argument('selector', nargs=-1)
def review(selector=None):

    if len(selector) <= 0:
        selector = None

    infra = utils.load_infra_module(INFRA_FILE).infra

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

    infra = utils.load_infra_module(INFRA_FILE).infra

    deploy = dep.SerialDeploy()

    if not deploy.cli_confirm(infra, selector):
        exit(0)

    deploy.deploy(infra, selector)


@stacks.command(help='Destroy stacks')
@click.argument('selector', nargs=-1)
def destroy(selector):

    selector = list(selector)

    infra = utils.load_infra_module(INFRA_FILE).infra

    deploy = dep.SerialDeploy()

    if not deploy.cli_confirm(infra, selector, reverse=True):
        exit(0)

    deploy.destroy(infra, selector, reverse=True)


@stacks.command(help='Dump Cloudformation template')
@click.option("--yaml", is_flag=True, default=False)
@click.argument('selector', nargs=-1)
def template(selector, yaml):

    selector = list(selector)

    infra = utils.load_infra_module(INFRA_FILE).infra

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


def styled_bool(val):
    chk = "✔"
    ex = "✗"
    if val:
        return "{}{}{}".format(Fore.GREEN, chk, Style.RESET_ALL)
    else:
        return "{}{}{}".format(Fore.RED, ex, Style.RESET_ALL)

def jinja_env():

    path = os.path.dirname(os.path.realpath(__file__))

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(
            searchpath="{}/templates/".format(path)))

    return env



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
