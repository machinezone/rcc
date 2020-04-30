'''Test utilities

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio

from rcc.client import RedisClient


def makeClient(port=None, redisPassword='', redisUser=''):
    # redis_url = 'redis://localhost:10000'  # for cluster
    redisUrl = 'redis://localhost'

    if port is not None:
        redisUrl += f':{port}'

    client = RedisClient(redisUrl, redisPassword, redisUser)
    return client


# Start redis server at a given port
async def runRedisServer(port):
    cmd = f'redis-server --port {port}'

    try:
        proc = await asyncio.create_subprocess_shell(cmd)
        stdout, stderr = await proc.communicate()
    finally:
        proc.terminate()
