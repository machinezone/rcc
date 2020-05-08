'''CLI

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.

rcc cli -p 10000 CLUSTER SETSLOT 12182 STABLE xxxx

Migrating 'foo' key
redis-cli -p 10000 CLUSTER SETSLOT 12182 IMPORTING 7f54416a684564483e83cdfef975d17f1a3950be  # noqa
'''

import asyncio
import logging
from urllib.parse import urlparse

import click
from rcc.client import RedisClient


async def interpreter(redisUrl, redisPassword, redisUser, args):
    client = RedisClient(redisUrl, redisPassword, redisUser)
    await client.connect()

    quit = False

    while not quit:
        printed = False

        if len(args) == 0:
            line = input('> ')
            args = line.split()
        else:
            quit = True

        cmd = args[0]
        cmd = cmd.upper()

        if len(args) > 1:
            cmdArgs = args[1:]
            response = await client.send(cmd, *cmdArgs)
        else:
            response = await client.send(cmd)

        if not printed:
            print(response)

        if not quit:
            args = []

    client.close()


@click.command()
@click.option('--redis_url', '-u', envvar='RCC_REDIS_URL', default='redis://localhost')
@click.option('--port', '-p')
@click.option('--password', '-a')
@click.option('--user')
@click.argument('args', nargs=-1, required=False)
def cli(redis_url, port, password, user, args):
    '''cli tool similar to redis-cli'''

    if port is not None:
        netloc = urlparse(redis_url).netloc
        host, _, _ = netloc.partition(':')
        redis_url = f'redis://{host}:{port}'

    try:
        asyncio.get_event_loop().run_until_complete(
            interpreter(redis_url, password, user, args)
        )
    except Exception as e:
        logging.error(f'cli error: {e}')
