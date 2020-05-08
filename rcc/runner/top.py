'''Monitor redis metrics from the INFO command

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''
import asyncio
import logging

import click
import tabulate

from rcc.client import RedisClient

DEFAULT_STATS = [
    'redis_version AS vers',
    'connected_clients AS clients',
    'used_memory_rss_human AS rss',
    'used_cpu_sys AS cpu(s)',
    'used_cpu_user AS cpu(u)',
    'instantaneous_input_kbps AS recv',
    'instantaneous_output_kbps AS sent',
    'instantaneous_ops_per_sec AS ops',
]


async def printRedisClusterInfoCoro(
    redisUrl, redisPassword, redisUser, stats, role=None
):
    redisClient = RedisClient(redisUrl, redisPassword, redisUser)
    nodes = await redisClient.cluster_nodes()

    clients = []
    for node in nodes:
        if role is not None and node.role != role:
            continue

        url = f'redis://{node.ip}:{node.port}'
        client = RedisClient(url, redisPassword, redisUser)
        clients.append((node, client))

    while True:
        rows = [['node', 'role']]
        for stat in stats:
            statAlias = stat
            if ' AS ' in stat:
                statAlias = stat.split()[-1]

            rows[0].append(statAlias)

        for node, client in clients:
            info = await client.send('INFO')

            row = [node.ip + ':' + node.port, node.role]
            for stat in stats:
                statName = stat.split()[0]
                statValue = info[statName]
                row.append(statValue)

            rows.append(row)

        click.clear()
        print(tabulate.tabulate(rows, tablefmt="simple", headers="firstrow"))
        await asyncio.sleep(1)


# rcc cluster-info --stats instantaneous_input_kbps
#
# Example ones:
#
# * instantaneous_input_kbps
# * instantaneous_output_kbps
# * connected_clients
# * used_memory_rss_human
#


@click.command()
@click.option(
    '--redis-url', '-u', envvar='RCC_REDIS_URL', default='redis://localhost:30001'
)
@click.option('--password', '-a')
@click.option('--user')
@click.option('--stats', '-s', default=DEFAULT_STATS, multiple=True)
@click.option('--role')
def top(redis_url, password, user, stats, role):
    '''Monitor redis metrics from the INFO command'''

    while True:
        try:
            asyncio.get_event_loop().run_until_complete(
                printRedisClusterInfoCoro(redis_url, password, user, stats, role)
            )
        except Exception as e:
            logging.error(f'cli error: {e}')
