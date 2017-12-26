# -*- coding: utf-8 -*-

"""Console script for stackformation."""

import click
import imp
import stackformation.deploy as dep
import logging


@click.group()
def main():
    configure_logging()


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
