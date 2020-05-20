'''Cluster creation (ADDSLOTS, MEET, etc...)

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import collections
import logging
import sys
import time

import click

from rcc.client import RedisClient
from rcc.cluster.info import getClusterNodeCount


SLOTS = 16384  # Total number of slots


ClusterCreateArgs = collections.namedtuple(
    'ClusterCreateArgs',
    ['shards', 'host', 'port', 'password', 'user', 'ips', 'replicas'],
)


def makeCreateCmd(args):
    # FIXME test hack when using redis-4
    # redisCli = '/usr/local/Cellar/redis/5.0.8/bin/redis-cli'

    auth = ''
    if args.password:
        auth += f'-a {args.password}'
        if args.user:
            auth += f' --user {args.user}'

    # --cluster-yes is supported in redis unstable, after 6 got released
    redisCli = 'redis-cli'
    cmd = f'yes | {redisCli} {auth} -h {args.host} -p {args.port} '
    cmd += f'--cluster create {args.ips} --cluster-replicas {args.replicas}'
    return cmd


async def createCluster(args):
    '''
    See clusterManagerCommandCreate in redis-cli.c

    The main difference is that we first set slots
    Then run cluster meet
    Then set replicas, as setting replicas requires the master to be known by th
    replica, and hence the meet to have happened already

    Another difference is master/replica assignment from the input list of ip address
    that could be changed easily to match redis-cli behavior.

    Tested with redis-server 4.x. In redis-4 time there was still redis-trib and no
    redis-cli, so we cannot use redis-cli to initialize the cluster
    '''

    #
    # Hash slot allocation
    #
    click.secho(
        f'>>> Performing hash slots allocation on {args.shards} nodes...', bold=True
    )

    slotsPerNode = SLOTS // args.shards
    offset = 0
    allSlots = []

    for i in range(args.shards):
        nodeSlots = []
        for j in range(slotsPerNode):
            nodeSlots.append(offset + j)

        offset += slotsPerNode
        allSlots.append(nodeSlots)

    # reminder
    for j in range(SLOTS % args.shards):
        allSlots[-1].append(offset + j)

    # Print slot assignment
    for i, nodeSlots in enumerate(allSlots):
        # Master[0] -> Slots 0 - 4095
        print('Master[{}] -> Slotes {} - {}'.format(i, nodeSlots[0], nodeSlots[-1]))

    nodes = args.ips.split()

    # Setting slots
    for i in range(args.shards):
        nodeAddress = nodes[i]
        redisUrl = f'redis://{nodeAddress}'
        masterClient = RedisClient(redisUrl, args.password, args.user)
        await masterClient.send('CLUSTER', 'ADDSLOTS', *allSlots[i])

    # Give each node its own 'epoch'
    click.secho('>>> Assign a different config epoch to each node', bold=True)
    for i, nodeAddress in enumerate(nodes):
        epoch = i + 1
        redisUrl = f'redis://{nodeAddress}'
        client = RedisClient(redisUrl, args.password, args.user)

        try:
            await client.send('CLUSTER', 'SET-CONFIG-EPOCH', epoch)
        except Exception as e:
            logging.warning(f'{redisUrl}: Error with set-config-epoch: {e}')
            pass

    click.secho('>>> Sending CLUSTER MEET messages to join the cluster', bold=True)
    firstNodeIp, _, firstNodePort = nodes[0].partition(':')

    for nodeAddress in nodes[1:]:
        redisUrl = f'redis://{nodeAddress}'
        client = RedisClient(redisUrl, args.password, args.user)
        await client.send('CLUSTER', 'MEET', firstNodeIp, firstNodePort)

    # Wait one second
    await asyncio.sleep(1)

    # Wait for all the nodes in the cluster to agree on node count
    # so that they all know about each other, and we can set replicas
    # Give us 15 seconds max to do that
    start = time.time()
    timeout = 15

    for nodeAddress in nodes:
        redisUrl = f'redis://{nodeAddress}'
        nodeCount = await getClusterNodeCount(redisUrl, args.password, args.user)
        if nodeCount != args.shards:
            await asyncio.sleep(0.1)
            sys.stderr.write('.')
            sys.stderr.flush()

            if time.time() - start > timeout:
                raise ValueError(
                    'Timed out while waiting for all nodes to see each other'
                )

    sys.stderr.write('\n')

    #
    # [m1, m2, ..., mn, r1, r2, ...]
    # [m1, m2, ...,      mn, r1, r2, ..., rn,    s1, s2, ...,    sn]
    #
    # <----- args.shards -> <--- args.shards --> <--- args.shards ->
    #
    # r1 = args.shards + 1
    # ...
    # ri = args.shards + i
    #
    # s1 = replicas * args.shards + 1
    # ...
    # si = replicas * args.shards + i
    #

    # Now we can set the replicas
    click.secho('>>> Assigning replicas', bold=True)
    for i in range(args.shards):
        masterNodeAddress = nodes[i]
        redisUrl = f'redis://{masterNodeAddress}'
        masterClient = RedisClient(redisUrl, args.password, args.user)
        masterNodeId = await masterClient.send('CLUSTER', 'MYID')

        for j in range(args.replicas):
            replicaIp = nodes[(j + 1) * args.shards + i]
            print(f'Setting replica {replicaIp} to {masterNodeAddress}')

            url = f'redis://{replicaIp}'
            replicaClient = RedisClient(url, args.password, args.user)

            await replicaClient.send('CLUSTER', 'REPLICATE', masterNodeId)
