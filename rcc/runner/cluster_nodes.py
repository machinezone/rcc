'''Display cluster nodes

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''
import asyncio
import logging

import click

from rcc.cluster.info import printRedisClusterInfoCoro


@click.command()
@click.option(
    '--redis-url', '-u', envvar='RCC_REDIS_URL', default='redis://localhost:30001'
)
@click.option('--password', '-a')
@click.option('--user')
@click.option('--role')
def cluster_nodes(redis_url, password, user, role):
    '''Display cluster nodes'''

    try:
        asyncio.get_event_loop().run_until_complete(
            printRedisClusterInfoCoro(redis_url, password, user, role)
        )
    except Exception as e:
        logging.error(f'cluster_nodes error: {e}')
