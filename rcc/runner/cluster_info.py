'''Repeatitly print cluster info

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''
import asyncio

import click
import tabulate

from rcc.client import RedisClient


async def printRedisClusterInfoCoro(redisUrl, redisPassword, stats, role=None):
    redisClient = RedisClient(redisUrl, redisPassword)
    nodes = await redisClient.cluster_nodes()

    clients = []
    for node in nodes:
        if role is not None and node.role != role:
            continue

        url = f'redis://{node.ip}:{node.port}'
        client = RedisClient(url, redisPassword)
        clients.append((node, client))

    while True:
        rows = [['node', 'role', *stats]]

        for node, client in clients:
            info = await client.info()

            row = [node.ip + ':' + node.port, node.role]
            for stat in stats:
                row.append(info[stat])

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


@click.command()
@click.option('--redis_url', '-r', default='redis://localhost:11000')
@click.option('--redis_password', '-a')
@click.option('--stats', '-s', default=['redis_version'], multiple=True)
@click.option('--role', '-r')
def cluster_info(redis_url, redis_password, stats, role):
    '''Monitor redis metrics from the INFO command'''

    asyncio.run(printRedisClusterInfoCoro(redis_url, redis_password, stats, role))
