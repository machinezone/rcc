'''Test resharding and capturing keyspace information.
Needs to be run last hence the weid name with zzz

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import json
import os
import tempfile
import uuid

from rcc.cluster.init_cluster import runNewCluster
from rcc.cluster.keyspace_analyzer import analyzeKeyspace
from rcc.cluster.reshard import binPackingReshardCoroutine
from rcc.cluster.info import getClusterSignature, runRedisCliClusterCheck

from test_utils import makeClient


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
    clusterReadyFile = os.path.join(root, 'redis_cluster_ready.json')
    startPort = 0
    redisUrl = f'redis://localhost:{startPort}'
    size = 3
    # redisPassword = 'my-secret-password'
    redisPassword = None
    redisUser = ''
    replicas = 1
    manual = True

    runClusterTask = asyncio.ensure_future(
        runNewCluster(
            root,
            clusterReadyFile,
            startPort,
            size,
            redisPassword,
            redisUser,
            replicas,
            manual,
        )
    )

    # Wait until cluster is initialized
    while not os.path.exists(clusterReadyFile):
        await asyncio.sleep(0.1)

    with open(clusterReadyFile) as f:
        data = json.loads(f.read())
        startPort = data['start_port']

    redisUrl = f'redis://localhost:{startPort}'
    client = makeClient(startPort, redisPassword, redisUser)
    await checkStrings(client)

    # now analyze keyspace for 3 seconds
    task = asyncio.ensure_future(analyzeKeyspace(redisUrl, redisPassword, redisUser, 3))

    # wait a tiny bit so that the analyzer is ready
    # (it needs to make a couple of pubsub subscriptions)
    await asyncio.sleep(0.1)

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

    await task
    keySpace = task.result()
    weights = keySpace.keys

    print('weights', weights)
    signature, balanced, fullCoverage = await getClusterSignature(
        redisUrl, redisPassword, redisUser
    )
    assert balanced
    assert fullCoverage

    ret = await binPackingReshardCoroutine(
        redisUrl, redisPassword, redisUser, weights, timeout=15
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

    # Do another reshard. This one should be a no-op
    # This should return statistics about the resharding
    ret = await binPackingReshardCoroutine(
        redisUrl, redisPassword, redisUrl, weights, timeout=15
    )
    assert ret

    task.cancel()
    await task

    runClusterTask.cancel()
    await runClusterTask


def test_reshard():
    asyncio.get_event_loop().run_until_complete(coro())
