'''Publish to a channel (with XADD)

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import uuid
from urllib.parse import urlparse

import click
from rcc.client import RedisClient


async def pub(
    redisUrl, redisPassword, redisUser, channel, random_channel, msg, batch, maxLen
):
    client = RedisClient(redisUrl, redisPassword, redisUser)
    await client.connect()

    if batch:
        while True:
            chan = channel
            if random_channel:
                chan = str(uuid.uuid4())

            streamId = await client.send(
                'XADD', chan, 'MAXLEN', '~', maxLen, b'*', 'json', msg
            )
    else:
        streamId = await client.send(
            'XADD', channel, 'MAXLEN', '~', maxLen, b'*', 'json', msg
        )
        print('Stream id:', streamId)


@click.command()
@click.option('--redis-url', '-u', default='redis://localhost')
@click.option('--port', '-p')
@click.option('--password', '-a')
@click.option('--user')
@click.option('--channel', default='foo')
@click.option('--random_channel', is_flag=True)
@click.option('--msg', default='{"bar": "baz"}')
@click.option('--batch', is_flag=True)
@click.option('--max_len', default='100')
def publish(
    redis_url, port, password, user, channel, random_channel, msg, batch, max_len
):
    '''Publish (with XADD) to a channel
    '''

    if port is not None:
        netloc = urlparse(redis_url).netloc
        host, _, _ = netloc.partition(':')
        redis_url = f'redis://{host}:{port}'

    asyncio.get_event_loop().run_until_complete(
        pub(redis_url, password, user, channel, random_channel, msg, batch, max_len)
    )
