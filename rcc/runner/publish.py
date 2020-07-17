'''Publish to a channel (with XADD)

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import csv
import logging
import uuid
import time
import traceback
from urllib.parse import urlparse

import click
from rcc.client import RedisClient


async def pub(
    redisUrl,
    redisPassword,
    redisUser,
    channel,
    random_channel,
    msg,
    batch,
    maxLen,
    csvPath,
):
    client = RedisClient(redisUrl, redisPassword, redisUser)
    await client.connect()

    if batch:
        if csvPath:
            start = time.time()

            publishedCount = 0
            with open(csvPath) as csvfile:
                reader = csv.reader(csvfile)
                try:
                    for row in reader:
                        chan = row[0]
                        count = int(row[1])
                        publishedCount += count

                        for i in range(count):
                            streamId = await client.send(
                                'XADD', chan, 'MAXLEN', '~', maxLen, b'*', 'json', msg
                            )
                except csv.Error as ex:
                    logging.error(
                        'error parsing csv file {}, line {}: {}'.format(
                            csvPath, reader.line_num, ex
                        )
                    )
                    return

            secs = '%0.2f' % (time.time() - start)
            click.secho(
                f'published {publishedCount} events in {secs} seconds', bold=True
            )
        else:
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
@click.option(
    '--redis-url', '-u', envvar='RCC_REDIS_URL', default='redis://localhost:30001'
)
@click.option('--port', '-p')
@click.option('--password', '-a')
@click.option('--user')
@click.option('--channel', default='foo')
@click.option('--random_channel', is_flag=True)
@click.option('--msg', default='{"bar": "baz"}')
@click.option('--batch', is_flag=True)
@click.option('--max_len', default='100')
@click.option('--csv_path', envvar='RCC_PUBLISH_BATCH_CSV_FILE')
def publish(
    redis_url,
    port,
    password,
    user,
    channel,
    random_channel,
    msg,
    batch,
    max_len,
    csv_path,
):
    '''Publish (with XADD) to a channel
    '''

    if port is not None:
        netloc = urlparse(redis_url).netloc
        host, _, _ = netloc.partition(':')
        redis_url = f'redis://{host}:{port}'

    try:
        asyncio.get_event_loop().run_until_complete(
            pub(
                redis_url,
                password,
                user,
                channel,
                random_channel,
                msg,
                batch,
                max_len,
                csv_path,
            )
        )
    except Exception as e:
        backtrace = traceback.format_exc()
        logging.debug(f'traceback: {backtrace}')
        logging.error(f'publish error: {e}')
