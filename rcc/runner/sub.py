'''Subscribe to a channel (with PUBSUB)

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import click
from rcc.client import RedisClient


async def subscriber(
    redisClient: RedisClient, channel: str, pattern: str, timeout: int
):
    async def cb(obj, message):
        print('Received', message)
        obj.append(message)

    obj = []
    if pattern:
        task = asyncio.ensure_future(redisClient.psubscribe(pattern, cb, obj))
    else:
        task = asyncio.ensure_future(redisClient.subscribe(channel, cb, obj))

    await asyncio.sleep(timeout)

    # Cancel the task
    task.cancel()
    await task

    print()
    print(f'Got {len(obj)} messages')
    for item in obj:
        print(f'Got {item}')


# rcc sub --redis_url redis://localhost:7379 --channel foo


@click.command()
@click.option('--redis_url', default='redis://localhost')
@click.option('--password', '-a')
@click.option('--user')
@click.option('--channel', default='foo')
@click.option('--pattern')
@click.option('--timeout', default=360)
def sub(redis_url, password, user, channel, pattern, timeout):
    '''Subscribe (with PUBSUB) to a channel'''

    redisClient = RedisClient(redis_url, password, user)

    asyncio.get_event_loop().run_until_complete(
        subscriber(redisClient, channel, pattern, timeout)
    )
