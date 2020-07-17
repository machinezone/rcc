'''Display cluster slots info

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''
import asyncio
import logging
import traceback

import click

from rcc.cluster.forget import clusterForgetNode


@click.command()
@click.option(
    '--redis-url', '-u', envvar='RCC_REDIS_URL', default='redis://localhost:30001'
)
@click.option('--password', '-a')
@click.option('--user')
@click.option('--node', '-n', required=True)
def cluster_forget(redis_url, password, user, node):
    '''Display cluster slots info'''

    try:
        asyncio.get_event_loop().run_until_complete(
            clusterForgetNode(redis_url, password, user, node)
        )
    except Exception as e:
        backtrace = traceback.format_exc()
        logging.debug(f'traceback: {backtrace}')
        logging.error(f'cluster_forget error: {e}')
