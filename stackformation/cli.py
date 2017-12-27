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

INFRA_FILE = "infra.py"


@click.group()
def main():
    configure_logging()
    load_configuration()


@main.group()
def stacks():
    pass

@main.group()
def image():
    pass

@image.command(help="Build AMI's")
def build():

    infra = load_infra_file()



@stacks.command(name='list')
@click.argument('selector', nargs=-1)
def list_stack(selector):

    selector = list(selector)

    infra = load_infra_file()

    stacks = infra.list_stacks()

    results = []

    for stack in stacks:
        if match_stack(selector, stack):
            results.append(stack)

    stacks = results

    for stack in stacks:
        click.echo("{}Stack:{} {} {}[{}]{}".format(
                    Style.BRIGHT,
                    Style.RESET_ALL+Fore.GREEN,
                    stack.get_stack_name(),
                    Fore.YELLOW,
                    stack.get_remote_stack_name(),
                    Style.RESET_ALL
                    ))
        click.echo("{}Type: {}{}{}".format(
                    Style.BRIGHT,
                    Style.RESET_ALL+Fore.CYAN,
                    stack.__class__,
                    Style.RESET_ALL
                    ))

@stacks.command(help='Deploy stacks')
@click.argument('selector', nargs=-1)
def review(selector):

    selector = list(selector)

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
        raise Exception("$HOME environment variable needs to be set to save configuration")



def jinja_env():

    path = os.path.dirname(os.path.realpath(__file__))

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(
            searchpath="{}/templates/".format(path)))

    return env


def load_infra_file():

    module = imp.load_source('deploy', INFRA_FILE)

    infra = module.infra

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
