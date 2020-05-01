'''Keyspace analyzer, used for resharding

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import collections
import csv
import statistics

from rcc.client import RedisClient
from rcc.cluster.reshard import makeClientfromNode

import click


class KeySpace(object):
    def __init__(self):
        self.notifications = 0
        self.keys = collections.defaultdict(int)
        self.nodes = collections.defaultdict(int)
        self.commands = collections.defaultdict(int)

    def describe(self):
        if len(self.nodes) > 1:
            self.describeData('Nodes', self.nodes)

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
    redisUser: str,
    timeout: int,
    count: int = -1,
    monitor: bool = False,
):
    pattern = '__key*__:*'

    redisUrls = redisUrlsStr.split(';')
    redisUrl = redisUrls[0]

    redisClient = RedisClient(redisUrl, redisPassword, redisUser)
    await redisClient.connect()

    clients = []
    if redisClient.cluster:
        nodes = await redisClient.cluster_nodes()
        masterNodes = [node for node in nodes if node.role == 'master']
        for node in masterNodes:
            client = makeClientfromNode(node, redisPassword, redisUser)
            clients.append(client)
    else:
        clients = [RedisClient(url, redisPassword, redisUser) for url in redisUrls]

    #
    # E for Keyevent events, published with __keyevent@<db>__ prefix.
    # A Alias for g$lshztxe, to catch all events
    #
    keyspaceConfig = 'AE'

    async def pubSubCallback(client, obj, message):
        '''Need to extract a key and a command from the pubsub payload'''

        msg = message[2].decode()
        _, _, cmd = msg.partition(':')
        cmd = cmd.upper()

        key = message[3].decode()
        obj.keys[key] += 1
        obj.notifications += 1

        node = f'{client.host}:{client.port}'
        obj.nodes[node] += 1
        obj.commands[cmd] += 1

    async def monitorCallback(client, obj, message):
        '''Need to extract a key and a command from the monitor payload'''

        #
        # We need to skip the beginning of such lines
        # 1586739509.775473 [0 [::1]:54588] "XADD" "58c52262_channel_99" "MAXLEN" ...
        #
        line = message.decode()

        # FIXME / parsing is not robust, if there are spaces in keys
        tokens = line.split()
        tokens = tokens[3:]

        cmd = tokens[0][1:-1]  # we need to remove the double quotes from key and cmd
        cmd = cmd.upper()

        # Some keys are located in odd places
        if len(tokens) > 1:
            key = tokens[1][1:-1]

            if cmd in ('XREAD', 'XREADGROUP'):
                try:
                    idx = tokens.index('"STREAMS"') + 1
                except ValueError:
                    raise ValueError(
                        "{0} arguments do not contain STREAMS operand".format(cmd)
                    )
                key = tokens[idx]
            elif cmd in ('XGROUP', 'XINFO'):
                key = tokens[2]
            else:
                key = tokens[1]

            key = key[1:-1]
            obj.keys[key] += 1

        # We need key and command
        obj.notifications += 1

        node = f'{client.host}:{client.port}'
        obj.nodes[node] += 1
        obj.commands[cmd] += 1

    tasks = []

    keySpace = KeySpace()

    # First we need to make sure keyspace notifications are ON
    # Do this manually with redis-cli -p 10000 config set notify-keyspace-events KEAt
    if not monitor:
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
            if monitor:
                task = asyncio.ensure_future(client.monitor(monitorCallback, keySpace))
            else:
                task = asyncio.ensure_future(
                    client.psubscribe(pattern, pubSubCallback, keySpace)
                )
            tasks.append(task)

        if count > 0:
            label = f'Capturing {count} events'
            with click.progressbar(length=count, label=label) as bar:

                progress = 0
                while keySpace.notifications < count:
                    await asyncio.sleep(0.1)
                    bar.update(keySpace.notifications - progress)
                    progress = keySpace.notifications
        else:
            label = f'Capturing events during {timeout} seconds'
            with click.progressbar(length=timeout, label=label) as bar:
                # Monitor during X seconds
                for i in range(timeout):
                    await asyncio.sleep(1)
                    bar.update(1)

        for task in tasks:
            # Cancel the tasks
            task.cancel()
            await task

    finally:
        if not monitor:
            # Now restore the notification
            for client, conf in zip(clients, confs):
                # reset the previous conf
                print(f'resetting old config {conf}')
                await client.send('CONFIG', 'SET', 'notify-keyspace-events', conf)

    keySpace.describe()

    return keySpace


def writeWeightsToCsv(weights: dict, path: str):
    with open(path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)

        for key, weight in sorted(weights.items()):
            writer.writerow([key, weight])
