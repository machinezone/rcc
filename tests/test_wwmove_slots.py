'''Test redis-cli like resharding

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import os
import tempfile
import uuid

from rcc.cluster.init_cluster import runNewCluster
from rcc.cluster.reshard import moveSlotsReshardCoroutine
from rcc.cluster.info import getClusterSignature, runRedisCliClusterCheck

from test_utils import makeClient, getRedisServerMajorVersion


async def checkStrings(client):
    await client.connect()

    key = str(uuid.uuid4())
    value = str(uuid.uuid4())
    await client.send('SET', key, value)

    result = await client.send('EXISTS', key)
    assert result

    res = await client.send('GET', key)
    assert res.decode() == value

    # delete the key
    await client.send('DEL', key)
    exists = await client.send('EXISTS', key)
    assert not exists


async def coro():
    root = tempfile.mkdtemp()
    clusterReadyFile = os.path.join(root, 'redis_cluster_ready')
    startPort = 12000
    redisUrl = f'redis://localhost:{startPort}'
    size = 3
    redisPassword = 'william'
    redisUser = None
    replicas = 1
    manual = True

    serverVersion = getRedisServerMajorVersion()
    if serverVersion >= 6:
        redisUser = 'bill'

    task = asyncio.ensure_future(
        runNewCluster(root, startPort, size, redisPassword, redisUser, replicas, manual)
    )

    # Wait until cluster is initialized
    while not os.path.exists(clusterReadyFile):
        await asyncio.sleep(0.1)

    client = makeClient(startPort, redisPassword, redisUser)

    # Write once
    for i in range(100):
        for j in range(i):
            key = f'channel_{i}'
            value = f'val_{i}'
            result = await client.send('SET', key, value)
            assert result

    # Validate that we can read back what we wrote
    for i in range(1, 100):
        key = f'channel_{i}'
        value = f'val_{i}'
        val = await client.send('GET', key)
        val = val.decode()
        assert val == value

    signature, balanced, fullCoverage = await getClusterSignature(
        redisUrl, redisPassword, redisUser
    )
    assert balanced
    assert fullCoverage

    # Move slots from the first to the second node
    nodes = await client.cluster_nodes()
    sourceNodeId = nodes[0].node_id
    targetNodeId = nodes[1].node_id
    slots = 500

    ret = await moveSlotsReshardCoroutine(
        redisUrl,
        redisPassword,
        redisUser,
        sourceNodeId,
        targetNodeId,
        slots,
        timeout=15,
        dry=False,
    )
    assert ret

    newSignature, balanced, fullCoverage = await getClusterSignature(
        redisUrl, redisPassword, redisUser
    )
    assert signature != newSignature
    assert balanced
    assert fullCoverage

    # Now run cluster check
    await runRedisCliClusterCheck(startPort, redisPassword, redisUser)

    # Validate that we can read back what we wrote, after resharding
    for i in range(1, 100):
        key = f'channel_{i}'
        value = f'val_{i}'
        val = await client.send('GET', key)
        val = val.decode()
        assert val == value

    # Do another reshard.
    ret = await moveSlotsReshardCoroutine(
        redisUrl,
        redisPassword,
        redisUser,
        sourceNodeId,
        targetNodeId,
        slots,
        timeout=15,
        dry=False,
    )
    assert ret

    newSignature, balanced, fullCoverage = await getClusterSignature(
        redisUrl, redisPassword, redisUser
    )
    assert signature != newSignature
    assert balanced
    assert fullCoverage

    # Validate that we can read back what we wrote, after resharding
    for i in range(1, 100):
        key = f'channel_{i}'
        value = f'val_{i}'
        val = await client.send('GET', key)
        val = val.decode()
        assert val == value

    task.cancel()


def test_move_slots():
    asyncio.get_event_loop().run_until_complete(coro())
