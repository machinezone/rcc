'''Test resharding and capturing keyspace information.
Needs to be run last hence the weird name with zzz

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import os
import tempfile

from rcc.cluster.init_cluster import runNewCluster
from rcc.cluster.reshard import makeClientfromNode, waitForClusterViewToBeConsistent
from rcc.cluster.info import getClusterSignature, runRedisCliClusterCheck
from rcc.cluster.reshard import migrateSlot
from rcc.version import getRedisServerMajorVersion

from test_utils import makeClient


async def coro():
    root = tempfile.mkdtemp()
    clusterReadyFile = os.path.join(root, 'redis_cluster_ready')
    startPort = 0
    redisUrl = f'redis://localhost:{startPort}'

    redisPassword = 'foobar'
    redisUser = None
    replicas = 1
    manual = True

    serverVersion = getRedisServerMajorVersion()
    if serverVersion >= 6:
        redisUser = 'fooser'

    size = 3
    task = asyncio.ensure_future(
        runNewCluster(root, startPort, size, redisPassword, redisUser, replicas, manual)
    )

    # Wait until cluster is initialized
    while not os.path.exists(clusterReadyFile):
        await asyncio.sleep(0.1)

    client = makeClient(startPort, redisPassword, redisUser)

    # Write something in redis
    key = 'channel_2'
    value = 'val_2'
    res = await client.send('SET', key, value)
    assert res is not None

    # Validate that we can read back what we wrote earlier
    results = await client.send('GET', key)
    val = results.decode()
    assert val == value

    signature, balanced, fullCoverage = await getClusterSignature(
        redisUrl, redisPassword, redisUser
    )
    assert balanced
    assert fullCoverage

    # ret = await binPackingReshardCoroutine(redisUrl, weights, timeout=15)
    # assert ret
    slot = 1978
    nodes = await client.cluster_nodes()
    masterNodes = [node for node in nodes if node.role == 'master']
    masterClients = [
        makeClientfromNode(node, redisPassword, redisUser) for node in masterNodes
    ]
    sourceNode = masterNodes[0]
    destinationNode = masterNodes[1]
    await migrateSlot(
        masterClients,
        redisPassword,
        redisUser,
        slot,
        sourceNode,
        destinationNode,
        dry=False,
    )

    consistent = await waitForClusterViewToBeConsistent(
        redisUrl, redisPassword, redisUser, timeout=5
    )
    assert consistent

    newSignature, balanced, fullCoverage = await getClusterSignature(
        redisUrl, redisPassword, redisUser
    )
    assert signature != newSignature
    assert balanced
    assert fullCoverage

    # Now run cluster check
    await runRedisCliClusterCheck(startPort, redisPassword, redisUser)

    # Validate that we can read back what we wrote, after resharding
    results = await client.send('GET', key)
    val = results.decode()
    assert val == value

    task.cancel()
    await task


def test_migrate_one_slot():
    asyncio.get_event_loop().run_until_complete(coro())
