'''Multiplexed Redis client

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.

wip code, use with care
'''
import asyncio

import hiredis

from rcc.client import RedisClient
from rcc.response import convertResponse


class MultiPlexedRedisClient(RedisClient):
    async def send(self, cmd, *args, **kargs):
        '''Small wrapper to be able to disconnect on error
        1. to avoid resource leaks
        2. to handle redis cluster re-configuring itself
        '''
        try:
            # We need to extract the key to hash it in cluster mode
            # key is at different spot than first args for
            # some commands such as STREAMS

            key = kargs.get('key')
            if key is None:
                key = self.findKey(cmd, *args)

            return await self.doSendMultiplexed(cmd, key, *args)
        except asyncio.CancelledError:
            raise
        except Exception:
            self.close()
            raise

    async def doSendMultiplexed(self, cmd, key, *args):
        '''Send a command to the redis server.
        Handle cluster mode redirects with the MOVE response
        '''
        # we should optimize this for the common case
        connection = await self.getConnection(key)

        fut = await connection.send(cmd, key, *args)
        response = await fut

        if self.needsRedirect(response):
            return await self.handleRedirect(response, cmd, *args)

        # we should handle other hiredis reply-error here,
        # and potentially rethrow

        return response

    # FIXME locks / static method / ASKING
    def needsRedirect(self, response):
        responseType = type(response)
        if responseType != hiredis.ReplyError:
            return False

        responseStr = str(response)
        return responseStr.startswith('MOVED')

    # FIXME locks
    async def handleRedirect(self, response, cmd, *args):
        responseStr = str(response)
        tokens = responseStr.split()
        slotStr = tokens[1]
        slot = int(slotStr)
        url = tokens[2]
        url = 'redis://' + url

        self.urls[slot] = url

        # We need to extract the key to hash it in cluster mode
        key = self.findKey(cmd, *args)

        # we should optimize this for the common case
        connection = await self.getConnection(key)

        fut = await connection.send(cmd, key, *args)
        response = await fut
        return response

    async def doSend(self, cmd, *args):
        '''Send a command to the redis server.
        Handle cluster mode redirects with the MOVE response
        '''
        # We need to extract the key to hash it in cluster mode
        key = self.findKey(cmd, *args)

        # key is at different spot than first args for some commands such as STREAMS
        attempts = 10

        async with self.lock:
            while attempts > 0:
                # we should optimize this for the common case
                connection = await self.getConnection(key)

                await connection.send(cmd, *args)
                response = await self.readResponse(connection)

                responseType = type(response)
                if responseType != hiredis.ReplyError:
                    return convertResponse(response, cmd)

                attempts -= 1

                responseStr = str(response)
                if responseStr.startswith('MOVED'):
                    tokens = responseStr.split()
                    slotStr = tokens[1]
                    slot = int(slotStr)
                    url = tokens[2]
                    url = 'redis://' + url

                    self.urls[slot] = url
                else:
                    raise response

        raise ValueError(f'Error sending command, too many redirects: {cmd} {args}')

    def __repr__(self):
        return f'<RedisClient at {self.host}:{self.port}>'
