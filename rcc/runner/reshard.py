'''Tools to reshard a redis cluster

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import resource
import click

from rcc.cluster.reshard import binPackingReshard

DEFAULT_WEIGHTS_PATH = 'weights.csv'


@click.command()
@click.option('--redis_url', '-r', default='redis://localhost:11000')
@click.option('--redis_password', '-a')
@click.option('--port', default=6379)
@click.option('--weight', '-w', required=True, default=DEFAULT_WEIGHTS_PATH)
@click.option('--dry', is_flag=True)
@click.option('--node_id')
@click.option('--timeout', default=15, help='Max time to wait for consistency check')
def reshard(port, redis_url, redis_password, weight, timeout, dry, node_id):
    '''Reshard a cluster using the binpacking technique'''

    nofile = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
    click.secho(f'file descriptors ulimit: {nofile}', fg='cyan')

    binPackingReshard(redis_url, redis_password, weight, timeout, dry, node_id)
