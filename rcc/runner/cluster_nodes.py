'''Display cluster nodes

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''
import asyncio
import logging
import traceback

import click

from rcc.cluster.info import printRedisClusterInfoCoro


@click.command()
@click.option(
    '--redis-url', '-u', envvar='RCC_REDIS_URL', default='redis://localhost:30001'
)
@click.option('--password', '-a')
@click.option('--user')
@click.option('--role')
@click.option('--hide_slots', is_flag=True)
def cluster_nodes(redis_url, password, user, role, hide_slots):
    '''Display cluster nodes'''

    displaySlots = not hide_slots

    try:
        asyncio.get_event_loop().run_until_complete(
            printRedisClusterInfoCoro(redis_url, password, user, role, displaySlots)
        )
    except Exception as e:
        backtrace = traceback.format_exc()
        logging.debug(f'traceback: {backtrace}')
        logging.error(f'cluster_nodes error: {e}')
