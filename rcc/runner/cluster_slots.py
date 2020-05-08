'''Display cluster slots info

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''
import asyncio
import logging

import click

from rcc.client import RedisClient
from rcc.cluster.info import getSlotsToNodesMapping


async def clusterSlotInfo(client, slot, details):
    slotToNodes = await getSlotsToNodesMapping(client)
    node = slotToNodes[int(slot)]

    if details:
        nodeId = node.node_id
        print(f'{node.ip}:{node.port} -> {nodeId}')
    else:
        nodeId = node.node_id
        print(nodeId)


@click.command()
@click.option(
    '--redis-url', '-u', envvar='RCC_REDIS_URL', default='redis://localhost:30001'
)
@click.option('--password', '-a')
@click.option('--user')
@click.option('--slot', '-s', required=True)
@click.option('--details', '-l', is_flag=True)
def cluster_slots(redis_url, password, user, slot, details):
    '''Display cluster slots info'''

    redisClient = RedisClient(redis_url, password, user)

    try:
        asyncio.get_event_loop().run_until_complete(
            clusterSlotInfo(redisClient, slot, details)
        )
    except Exception as e:
        logging.error(f'cluster_nodes error: {e}')
