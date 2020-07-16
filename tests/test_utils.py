'''Test utilities

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import socket
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

    except asyncio.CancelledError:
        print('Cancelling redis-server')

    finally:
        proc.terminate()


async def getSupportedCommands(client):
    command = await client.send('COMMAND')
    commands = set()
    for item in command:
        commands.add(item[0].decode())

    return commands


async def isCommandSupported(client, cmd):
    commands = await getSupportedCommands(client)
    return cmd in commands


def findFreePort(
    interface='127.0.0.1', socket_family=socket.AF_INET, socket_type=socket.SOCK_STREAM
):
    """
    Ask the platform to allocate a free port on the specified interface, then
    release the socket and return the address which was allocated.

    Copied from ``twisted.internet.test.connectionmixins.findFreePort``.

    :param bytes interface: The local address to try to bind the port on.
    :param int socket_family: The socket family of port.
    :param int socket_type: The socket type of the port.

    :return: A two-tuple of address and port, like that returned by
        ``socket.getsockname``.
    """
    address = socket.getaddrinfo(interface, 0)[0][4]
    probe = socket.socket(socket_family, socket_type)
    try:
        probe.bind(address)
        return probe.getsockname()
    finally:
        probe.close()
