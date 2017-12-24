# -*- coding: utf-8 -*-

"""Console script for stackformation."""

import click
import imp
import stackformation.deploy as dep


@click.group()
def main(args=None):
    """Console script for stackformation."""
    click.echo("Replace this message by putting your code into "
               "stackformation.cli.main")
    click.echo("See click documentation at http://click.pocoo.org/")



@main.command()
@click.argument('selector', nargs=-1)
def deploy(selector):

    selector = list(selector)

    module = imp.load_source('deploy', 'infra.py')

    infra = module.infra

    deploy = dep.DeployStacks()

    if not deploy.cli_confirm(infra, selector):
        exit(0)

    deploy.deploy_stacks(infra, selector)

if __name__ == "__main__":
    main()
