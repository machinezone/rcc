'''Test analyzing key-space

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import uuid

from rcc.cluster.keyspace_analyzer import analyzeKeyspace
from rcc.client import RedisClient


async def coro():
    '''The caveat with this test is that external clients could
    be hitting redis as well, and we would get notifications for that
    '''
    redisUrl = 'redis://localhost:6379'
    redisPassword = ''
    redisClient = RedisClient(redisUrl, redisPassword)

    # now analyze keyspace for 2 seconds
    task = asyncio.create_task(analyzeKeyspace(redisUrl, redisPassword, 2))

    # wait a tiny bit so that the analyzer is ready
    # (it needs to make a couple of pubsub subscriptions)
    await asyncio.sleep(0.1)

    # Write once
    keys = []
    for i in range(100):
        for j in range(i):
            prefix = uuid.uuid4().hex[:8]
            channel = f'{prefix}_channel_{i}'
            keys.append(channel)

            value = f'val_{i}'
            streamId = await redisClient.send(
                'XADD', channel, 'MAXLEN', '~', '1', b'*', 'foo', value
            )
            assert streamId is not None

    await task
    keySpace = task.result()

    weights = keySpace.keys
    print('weights', weights)
    assert len(weights) >= 50

    # Make sure we did capture one xadd
    assert 'xadd' in keySpace.commands

    # cleanup
    for key in keys:
        await redisClient.send('DEL', key)


def test_analyze_keyspace():
    asyncio.run(coro())
