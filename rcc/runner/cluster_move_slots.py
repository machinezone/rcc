'''Move cluster slots from a source node to target one

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import logging

import click

from rcc.cluster.reshard import moveSlotsReshardCoroutine


@click.command()
@click.option(
    '--redis_url', '-r', envvar='RCC_REDIS_URL', default='redis://localhost:11000'
)
@click.option('--password', '-a')
@click.option('--user')
@click.option('--port', default=6379)
@click.option('--dry', is_flag=True)
@click.option('--cluster_from')
@click.option('--cluster_to')
@click.option('--slots', type=int, default=100)
@click.option('--timeout', default=15, help='Max time to wait for consistency check')
def cluster_move_slots(
    port, redis_url, password, user, cluster_from, cluster_to, slots, timeout, dry
):
    '''Move cluster slots from a source node to target one'''

    try:
        asyncio.get_event_loop().run_until_complete(
            moveSlotsReshardCoroutine(
                redis_url, password, user, cluster_from, cluster_to, slots, timeout, dry
            )
        )
    except Exception as e:
        logging.error(f'cluster-move-slots error: {e}')
