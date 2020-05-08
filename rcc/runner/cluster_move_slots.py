'''Move cluster slots from a source node to a target one

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import logging

import click

from rcc.cluster.reshard import moveSlotsReshardCoroutine


@click.command()
@click.option(
    '--redis-url', '-u', envvar='RCC_REDIS_URL', default='redis://localhost:30001'
)
@click.option('--password', '-a')
@click.option('--user')
@click.option('--dry', is_flag=True)
@click.option('--cluster-from')
@click.option('--cluster-to')
@click.option('--slots', type=int, default=100)
@click.option('--timeout', default=15, help='Max time to wait for consistency check')
def cluster_move_slots(
    redis_url, password, user, cluster_from, cluster_to, slots, timeout, dry
):
    '''Move cluster slots from a source node to a target one'''

    try:
        asyncio.get_event_loop().run_until_complete(
            moveSlotsReshardCoroutine(
                redis_url, password, user, cluster_from, cluster_to, slots, timeout, dry
            )
        )
    except Exception as e:
        logging.error(f'cluster-move-slots error: {e}')
