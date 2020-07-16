'''Tools to reshard a redis cluster

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import logging
import traceback

import click

from rcc.cluster.reshard import binPackingReshard

DEFAULT_WEIGHTS_PATH = 'weights.csv'


@click.command()
@click.option(
    '--redis-url', '-u', envvar='RCC_REDIS_URL', default='redis://localhost:30001'
)
@click.option('--password', '-a')
@click.option('--user')
@click.option('--port', default=6379)
@click.option('--weight', '-w', required=True, default=DEFAULT_WEIGHTS_PATH)
@click.option('--dry', is_flag=True)
@click.option('--node_id')
@click.option('--timeout', default=15, help='Max time to wait for consistency check')
def reshard(port, redis_url, password, user, weight, timeout, dry, node_id):
    '''Reshard a cluster using the binpacking technique'''

    try:
        binPackingReshard(redis_url, password, user, weight, timeout, dry, node_id)
    except Exception as e:
        backtrace = traceback.format_exc()
        logging.debug(f'traceback: {backtrace}')
        logging.error(f'reshard error: {e}')
