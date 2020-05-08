'''rcc main test driver.

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.

# flake8: noqa
'''

import logging
from pkgutil import walk_packages

import click
import uvloop
import coloredlogs

LOGGING_FORMAT = '%(asctime)s %(levelname)s %(message)s'
coloredlogs.install(level='WARNING', fmt=LOGGING_FORMAT)


@click.option('--verbose', '-v', envvar='RCC_VERBOSE', count=True)
@click.option('--uv', envvar='RCC_UVLOOP', is_flag=True, help='Use uvloop')
@click.group()
@click.version_option()
def main(verbose, uv):
    """\b
_______   ____  ____
\\_  __ \\_/ ___\\/ ___\\
 |  | \\/\\  \\__\\  \\___
 |__|    \\___  >___  >
             \\/    \\/

rcc / Redis Cluster Client / cli
    """
    if uv:
        uvloop.install()

    if verbose:
        level = 'INFO' if verbose == 1 else 'DEBUG'
        coloredlogs.install(level=level, fmt=LOGGING_FORMAT)


for loader, module_name, is_pkg in walk_packages(__path__, __name__ + '.'):
    module = __import__(module_name, globals(), locals(), ['__name__'])
    cmd = getattr(module, module_name.rsplit('.', 1)[-1])
    if isinstance(cmd, click.Command):
        main.add_command(cmd)
