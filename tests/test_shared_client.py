'''Test sending command over multiple client

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import random
import time

import pytest
from test_utils import makeClient, runRedisServer


async def sharedClient():
    port = random.randint(1000, 9000)
    client = makeClient(port=port)
    port = client.port

    redisServerTask = asyncio.ensure_future(runRedisServer(port))
    await asyncio.sleep(0.1)  # wait a bit until the server is running

    await client.send('DEL', 'a')
    val = await client.send('INCR', 'a')

    async def incrementer(client, count):
        for i in range(count):
            await client.send('INCR', 'a')

            if False:
                # wait a random amount of time, a tenth of a millisecond
                waitTime = random.randint(1, 8) / 10000
                await asyncio.sleep(waitTime)

    start = time.time()

    taskA = asyncio.ensure_future(incrementer(client, 1000))
    taskB = asyncio.ensure_future(incrementer(client, 1000))
    taskC = asyncio.ensure_future(incrementer(client, 1000))
    taskD = asyncio.ensure_future(incrementer(client, 1000))
    taskE = asyncio.ensure_future(incrementer(client, 1000))

    await taskA
    await taskB
    await taskC
    await taskD
    await taskE

    delta = time.time() - start
    print(delta)

    val = await client.send('GET', 'a')
    assert val == b'5001'

    # Now cancel the server and wait a bit (do we need this ?)
    redisServerTask.cancel()
    await redisServerTask

    await asyncio.sleep(0.1)  # wait a bit until the server is not running

    with pytest.raises(Exception):
        await client.send('PING')

    assert not client.connected()


def test_ping():
    asyncio.get_event_loop().run_until_complete(sharedClient())
