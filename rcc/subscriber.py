'''Redis subscriber built on Streams, not PubSub

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import base64

import json
import logging
import re
import traceback
from abc import ABC, abstractmethod
from typing import Optional

from rcc.client import RedisClient

POSITION_PATTERN = re.compile('^(?P<id1>[0-9]+)-(?P<id2>[0-9]+)')


def validatePosition(position):
    if position is None or position == '$':
        return True

    return POSITION_PATTERN.match(position)


class RedisSubscriberMessageHandlerClass(ABC):
    def __init__(self, args):
        pass  # pragma: no cover

    @abstractmethod
    def log(self, msg):
        pass  # pragma: no cover

    @abstractmethod
    async def on_init(self, initInfo: dict):
        pass  # pragma: no cover

    @abstractmethod
    async def handleMsg(self, msg: dict, position: str, payloadSize: int) -> bool:
        return True  # pragma: no cover


async def getClientIdForKey(client, key):
    return await client.send('CLIENT', 'ID', key=key)


async def getHostForKey(client, key):
    # Check whether redis is running in cluster mode or not
    try:
        info = await client.send('INFO')
    except Exception:
        return f'{client.host}:{client.port}'

    if info.get('cluster_enabled') == '0':
        return f'{client.host}:{client.port}'

    # Redis is running in cluster mode.
    # 1. get the slot for a key
    slot = await client.send('CLUSTER', 'KEYSLOT', key)

    # 2. find which node is handling a slot
    slots = await client.send('CLUSTER', 'SLOTS')

    for slotInfo in slots:
        if slotInfo[0] <= slot <= slotInfo[1]:
            host = slotInfo[2][0].decode()
            port = slotInfo[2][1]
            return f'{host}:{port}'

    # this should not happen, unless the cluster is being reconfigured
    return 'unknown-host'


async def redisSubscriber(
    client: RedisClient,
    stream: str,
    position: Optional[str],
    messageHandlerClass: RedisSubscriberMessageHandlerClass,  # noqa
    obj,
):
    messageHandler = messageHandlerClass(obj)

    logPrefix = f'subscriber[{stream}]: {client}'

    streamExists = False
    redisHost = client.host
    clientId = -1

    if client:
        # query the stream size
        try:
            streamExists = await client.send('EXISTS', stream)
            clientId = await client.send('CLIENT', 'ID', key=stream)
            redisHost = await getHostForKey(client, stream)
        except Exception as e:
            logging.error(f"{logPrefix} cannot retreive stream metadata: {e}")
            client = None

    initInfo = {
        'success': client is not None,
        'redis_node': redisHost,
        'redis_client_id': clientId,
        'stream_exists': streamExists,
    }

    try:
        await messageHandler.on_init(initInfo)
    except Exception as e:
        logging.error(f'{logPrefix} cannot initialize message handler: {e}')
        client = None

    if client is None:
        return messageHandler

    # lastId = '0-0'
    lastId = '$' if position is None else position

    try:
        # wait for incoming events.
        while True:
            results = await client.send(
                'XREAD', 'BLOCK', b'0', b'STREAMS', stream, lastId
            )

            results = results[stream.encode()]

            for result in results:
                lastId = result[0].decode()
                msg = result[1]
                data = msg[b'json']

                payloadSize = len(data)
                try:
                    msg = json.loads(data)
                except json.JSONDecodeError:
                    msgEncoded = base64.b64encode(data)
                    err = f'malformed json: base64: {msgEncoded} raw: {data}'
                    logging.error(err)
                    continue

                ret = await messageHandler.handleMsg(msg, lastId, payloadSize)
                if not ret:
                    break

    except asyncio.CancelledError:
        messageHandler.log('Cancelling redis subscription')
        raise

    except Exception as e:
        messageHandler.log(e)
        backtrace = traceback.format_exc()
        messageHandler.log(f'{logPrefix} Generic Exception caught in {backtrace}')

    finally:
        messageHandler.log('Closing redis subscription')

        # When finished, close the connection.
        client.close()

        return messageHandler


def runSubscriber(
    client: RedisClient, channel: str, position: str, messageHandlerClass, obj=None
):
    asyncio.get_event_loop().run_until_complete(
        redisSubscriber(client, channel, position, messageHandlerClass, obj)
    )
