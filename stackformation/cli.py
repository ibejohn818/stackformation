# -*- coding: utf-8 -*-

"""Console script for stackformation."""

import click
import imp
import stackformation.deploy as dep
import logging
from stackformation.utils import (match_stack)

INFRA_FILE="infra.py"


@click.group()
def main():
    configure_logging()


@main.group()
def stacks():
    pass

@stacks.command()
@click.argument('selector', nargs=-1)
def deploy(selector):

    selector = list(selector)

    infra = load_infra_file()

    deploy = dep.SerialDeploy()

    if not deploy.cli_confirm(infra, selector):
        exit(0)

    deploy.deploy(infra, selector)

@stacks.command()
@click.argument('selector', nargs=-1)
def template(selector):

    selector = list(selector)

    infra = load_infra_file()

    stacks = infra.list_stacks()

    results = []

    for stack in stacks:
        if match_stack(selector, stack):
            results.append(stack)

    for stack in results:
        t = stack.build_template()
        print(t.to_json())




@stacks.command(help="List stack dependencies")
def dependencies():

    infra = load_infra_file()

    stacks = infra.list_stacks()


    for stack in stacks:
        deps = infra.get_dependent_stacks(stack)
        click.echo("Stack: {}".format(stack.get_stack_name()))
        click.echo("Dependencies:")
        for k, v in deps.items():
            click.echo(" -{} ({})".format(k, v))
        click.echo('----------------')

def load_infra_file():

    module = imp.load_source('deploy', INFRA_FILE)

    infra = module.infra

    return infra


def configure_logging():

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    stream = logging.StreamHandler()
    stream.setFormatter(
            logging.Formatter('%(levelname)s - %(message)s'))
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
