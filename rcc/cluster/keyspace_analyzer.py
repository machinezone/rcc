'''Keyspace analyzer, used for resharding

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import collections
import csv
import sys
import statistics

from rcc.client import RedisClient
from rcc.cluster.reshard import makeClientfromNode


class KeySpace(object):
    def __init__(self, progress=True):
        self.progress = progress
        self.notifications = 0
        self.keys = collections.defaultdict(int)
        self.nodes = collections.defaultdict(int)
        self.commands = collections.defaultdict(int)

    def describe(self):
        print(f'notifications {self.notifications}')
        print(f'accessed keys {self.keys}')
        print(f'commands {self.commands}')
        print(f'nodes {self.nodes}')

        if len(self.nodes) > 1:
            self.describeData('Nodes', self.nodes)
        print()

    def describeData(self, title, data):
        print(f'== {title} ==')
        print('Mean', statistics.mean(data.values()))
        print('Median', statistics.median(data.values()))
        print('Stddev', statistics.stdev(data.values()))
        print(
            'Stddev/Mean',
            statistics.stdev(data.values()) / statistics.mean(data.values()),
        )


async def analyzeKeyspace(
    redisUrlsStr: str,
    redisPassword: str,
    timeout: int,
    progress: bool = True,
    count: int = -1,
):
    pattern = '__key*__:*'

    redisUrls = redisUrlsStr.split(';')
    redisUrl = redisUrls[0]

    redisClient = RedisClient(redisUrl, redisPassword)
    await redisClient.connect()

    clients = []
    if redisClient.cluster:
        nodes = await redisClient.cluster_nodes()
        masterNodes = [node for node in nodes if node.role == 'master']
        for node in masterNodes:
            client = makeClientfromNode(node, redisPassword)
            clients.append(client)
    else:
        clients = [RedisClient(url, redisPassword) for url in redisUrls]

    #
    # E for Keyevent events, published with __keyevent@<db>__ prefix.
    # A Alias for g$lshztxe, to catch all events
    #
    keyspaceConfig = 'AE'

    async def cb(client, obj, message):
        if obj.progress:
            sys.stderr.write('.')
            sys.stderr.flush()

        msg = message[2].decode()
        _, _, cmd = msg.partition(':')

        key = message[3].decode()
        obj.keys[key] += 1
        obj.notifications += 1

        node = f'{client.host}:{client.port}'
        obj.nodes[node] += 1
        obj.commands[cmd] += 1

    tasks = []

    keySpace = KeySpace(progress)

    # First we need to make sure keyspace notifications are ON
    # Do this manually with redis-cli -p 10000 config set notify-keyspace-events KEAt
    confs = []
    for client in clients:
        conf = await client.send('CONFIG', 'GET', 'notify-keyspace-events')
        if conf[1]:
            print(f'{client} current keyspace config: {conf[1].decode()}')
            confs.append(conf[1].decode())

        # Set the new conf
        await client.send('CONFIG', 'SET', 'notify-keyspace-events', keyspaceConfig)

    try:
        for client in clients:
            task = asyncio.create_task(client.psubscribe(pattern, cb, keySpace))
            tasks.append(task)

        if count > 0:
            while keySpace.notifications < count:
                await asyncio.sleep(0.1)
        else:
            # Monitor during X seconds
            await asyncio.sleep(timeout)

        for task in tasks:
            # Cancel the tasks
            task.cancel()
            await task

    finally:
        # Now restore the notification
        for client, conf in zip(clients, confs):
            # reset the previous conf
            print(f'resetting old config {conf}')
            await client.send('CONFIG', 'SET', 'notify-keyspace-events', conf)

    # FIXME: note how many things
    keySpace.describe()

    return keySpace


def writeWeightsToCsv(weights: dict, path: str):
    with open(path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)

        for key, weight in sorted(weights.items()):
            writer.writerow([key, weight])
