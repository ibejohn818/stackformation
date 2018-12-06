# -*- coding: utf-8 -*-

"""Console script for stackformation."""

import stackformation
import stackformation.deploy as dep
from stackformation.utils import (match_stack, match_image)
from stackformation import utils
import click
import logging
import os
import jinja2
from colorama import Fore, Style
import jmespath
from textwrap import dedent

INFRA_FILE = "stacks.py"

HELP = {
    'image_ansible_config': """
    echo the configured ansible dir for the Ami class
""",
    'main': """
    Stackformation {}

    CloudFormation framework to enforce infrastructure-as-code paradigm
""".format(stackformation.__version__),
'stack_file_override': """(Default: {}) Override the infrastructure configuration file
""".format(INFRA_FILE),
    'images_build': """
Select the image to build from your configured images in your {0} file.
If this is the first image being built it will automatically be made active.
If there are more than one builds present, make sure to mark the image --active/-a
if you wish for this to be the current build in-scope
""".format(INFRA_FILE)  # noqa


}
context_settings = {
    'help_option_names': ['-h', '--help']
}


@click.group(help=HELP['main'], context_settings=context_settings)
@click.option(
    "--file-override",
    "-z",
    default=INFRA_FILE,
    help=HELP['stack_file_override'])
def main(file_override=None):

    if file_override is not None:
        global INFRA_FILE
        INFRA_FILE = file_override

    configure_logging()


@main.group()
def stacks():
    pass


@main.group()
def ami():
    pass


@ami.command(help="List images", name='list')
def ami_list():

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
                memo = None
                for t in ami['Tags']:
                    if t['Key'] == 'ACTIVE':
                        flag = "(ACTIVE)"
                        flag_style = Fore.GREEN
                    if t['Key'] == 'MEMO' and \
                            len(t['Value']) > 0:
                        memo = t['Value']

                click.echo(
                    "  Date: {} {}AMI: {} {}{}".format(
                        ami['CreationDate'],
                        flag_style,
                        ami['ImageId'],
                        flag,
                        Style.RESET_ALL))
                if memo is not None:
                    click.echo(
                        "     {}Memo:{} {}".format(
                            Style.BRIGHT,
                            Style.RESET_ALL,
                            memo))


@ami.command(help=HELP['image_ansible_config'], name='ansible-dir')
@click.option("--ansible-roles", is_flag=True, default=False)
def ansible_dir(ansible_roles):

    mod = utils.load_infra_module(INFRA_FILE)

    dir_name = mod.Ami.ANSIBLE_DIR

    click.echo(dir_name)


@ami.command(help=HELP['images_build'], name='build')
@click.argument("name", default="")
@click.option(
    '--active',
    '-a',
    is_flag=True,
    default=False,
    help='Make image active')
# @click.option("--yes","-y", is_flag=True, default=False, help="Force build")
@click.option('--memo', '-m', default='')
def ami_build(name=None, active=False, memo=''):

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
        click.echo("Image(s) will be made active")

    click.confirm("Do you wish to build the matched images?", abort=True)

    for image in results:
        image.build(active, memo)


@ami.command(help="", name='activate')
@click.argument("name", required=True)
@click.option('--id', required=True)
def ami_activate(name, id):

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


@ami.command(help="", name='prune')
@click.argument("name", required=True)
@click.option('--force', is_flag=True, default=False,
              help="Force deletion of active AMI")
def ami_prune(name, force):

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
@click.option("--dependencies", "-d", is_flag=True, default=False)
@click.option("--remote", "-r", is_flag=True, default=False)
def stacks_list(selector=None, dependencies=False, remote=False):

    if len(selector) <= 0:
        selector = None
    else:
        selector = list(selector)

    infra = utils.load_infra_module(INFRA_FILE).infra

    stacks = infra.list_stacks()

    results = match_stack(selector, stacks)

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
            Style.BRIGHT + Fore.CYAN,
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
                    click.echo(
                        "  {} {} ({})".format(
                            rem,
                            utils.colors(
                                'p') +
                            v.get_stack_name() +
                            Style.RESET_ALL,
                            ty))


@stacks.command(help='Deploy stacks', name='review')
@click.argument('selector', nargs=-1)
def stacks_review(selector=None):

    if len(selector) >= 0:
        selector = list(selector)

    infra = utils.load_infra_module(INFRA_FILE).infra

    stacks = infra.list_stacks()

    results = match_stack(selector, stacks)

    for stack in results:

        wbs = utils.colors('w', True)
        rsall = Style.RESET_ALL

        click.echo("Stack Name: {}{}{}".format(
            wbs,
            stack.get_stack_name(),
            rsall
        ))

        click.echo("Type: {}{}{}".format(
            wbs,
            type(stack).__name__,
            rsall
        ))
        review = stack.review(infra)

        dep_status = styled_bool(False)
        if review['info']:
            dep_status = styled_bool(True)

        click.echo("Deploy Status: {}".format(dep_status))

        if len(review['dependent_stacks']) <= 0:
            click.echo("No dependent stacks")
        else:
            num_dependent = len(review['dependent_stacks'])
            click.echo("Denpendent Stacks: {}".format(num_dependent))
            click.echo("{} = Deployed | {} = Not Deployed".format(
                styled_bool(True),
                styled_bool(False)
            ))
            for v in review['dependent_stacks']:
                if not v['stack_info']:
                    deployed = False
                    status = "Not Deployed"
                else:
                    deployed = True
                    status = "Deployed"

                click.echo("  {} {} ({})".format(
                    styled_bool(deployed),
                    v['stack'].get_stack_name(),
                    type(v['stack']).__name__
                ))

        click.echo("")
        click.echo("Parameter Review:")

        if not review['info'] or not review['info'].get('Parameters'):  # noqa
            params = {}
        else:
            params = {}
            for v in review['info'].get('Parameters'):
                params.update({v['ParameterKey']:
                               v['ParameterValue']})

        # define icons
        nv = "{}?{}".format(
            utils.colors('y', True),
            Style.RESET_ALL
        )
        sv = styled_bool(True)
        cv = styled_bool(False)

        if len(review['parameters']) <= 0:
            click.echo("No Parameters to review")
        else:
            click.echo(
    "{} = New Value | {} = Changed Value | {} = No Change".format(
         nv, cv, sv))  # noqa

        for v in review['parameters']:
            param_name = v['ParameterKey']
            param_value = v['ParameterValue']
            status = ""
            if not params.get(param_name):
                icon = nv
            elif params.get(param_name) == param_value:
                icon = sv
            else:
                icon = cv
                status = "{}Previous Value: {}{} ".format(
                    utils.colors('b', True),
                    params.get(param_name),
                    Style.RESET_ALL)
            click.echo("{} {}: {}".format(icon, param_name, param_value))
            if len(status) > 0:
                click.echo(dedent(status))


@stacks.command(help='Deploy stacks')
@click.argument('selector', nargs=-1)
def deploy(selector=False):

    selector = list(selector)

    infra = utils.load_infra_module(INFRA_FILE).infra

    deploy = dep.SerialDeploy()

    if not deploy.cli_confirm(infra, selector):
        exit(0)

    deploy.deploy(infra, selector)


@stacks.command(help='Destroy stacks')
@click.argument('selector', nargs=-1)
def destroy(selector=False):

    selector = list(selector)

    infra = utils.load_infra_module(INFRA_FILE).infra

    deploy = dep.SerialDeploy()

    if not deploy.cli_confirm(
            infra,
            selector,
            ask='Are you sure you want to destroy these stack(s)?',
            reverse=True):
        exit(0)

    deploy.destroy(infra, selector, reverse=True)


@stacks.command(help='Dump Cloudformation template')
@click.option("--yaml", is_flag=True, default=False)
@click.argument('selector', nargs=-1)
def template(selector, yaml):

    selector = list(selector)

    infra = utils.load_infra_module(INFRA_FILE).infra

    stacks = infra.list_stacks()

    stacks = match_stack(selector, stacks)

    for stack in stacks:

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
