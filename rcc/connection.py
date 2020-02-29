'''Connection class / deals with the underlying socket / TCP transport

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import logging
import sys
import asyncio
import io
import uuid
import collections
import socket
from urllib.parse import urlparse

import hiredis


class Connection(object):
    def __init__(self, url, password, verbose=False):
        netloc = urlparse(url).netloc
        host, _, port = netloc.partition(':')
        if port:
            self.port = int(port)
        else:
            self.port = 6379

        self.host = host

        self.password = password
        self.verbose = verbose

        self._reader = hiredis.Reader()

        self.reader = None
        self.writer = None

        self.connectionId = uuid.uuid4().hex[:8]
        self.logPrefix = f'[{self.host}:{self.port}:{self.connectionId}]'

        self.read_size = 4 * 1024

        self.waiters = collections.deque()

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)

        # disable nagle algorithm
        sock = self.writer.transport.get_extra_info('socket')
        if sock is not None:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        if self.password:
            # FIXME: need AUTH error checking
            await self.auth(self.password)

        self.task = asyncio.create_task(self.readResponseTask())

    def close(self):
        try:
            if self.writer.can_write_eof():
                self.writer.write_eof()

            # ugly null check prevent errors when cancelling something with Ctrl-C
            if self.writer is not None:
                self.writer.close()
        except Exception:
            pass

        self.reader = None
        self.writer = None

        self.task.cancel()

    def connected(self):
        return self.writer is not None and self.reader is not None

    async def readResponseTask(self):
        # breakpoint()
        while True:
            response = await self.readResponse()

            # FIXME / we should do the convertion here
            waiter = self.waiters.popleft()
            waiter.set_result(response)

    async def readResponse(self):
        '''
        # hiredis.ReplyError
        '''

        response = self._reader.gets()
        while response is False:
            try:
                buf = await self.reader.read(self.read_size)
            except asyncio.CancelledError:
                raise
            except Exception:
                e = sys.exc_info()[1]
                raise ConnectionError(
                    "Error {} while reading from stream: {}".format(type(e), e.args)
                )

            if not buf:
                raise ConnectionError("Socket closed on remote end")

            self._reader.feed(buf)
            response = self._reader.gets()

        return response

    def writeString(self, buf, data):
        buf.write(b'$%d\r\n' % len(data))

        if not isinstance(data, bytes):
            buf.write(data.encode())
        else:
            buf.write(data)

        buf.write(b'\r\n')

    async def send(self, cmd, key=None, *args):
        '''key will be used by redis cluster'''

        if not self.connected():
            await self.connect()

        buf = io.BytesIO()

        if len(args) == 0:
            buf.write(cmd.encode() + b'\r\n')
        else:
            size = len(args) + 1
            s = f'*{size}\r\n'
            buf.write(s.encode())

            self.writeString(buf, cmd)
            for arg in args:
                # FIXME Are there other types to support ?
                if isinstance(arg, int):
                    self.writeString(buf, str(arg))
                else:
                    self.writeString(buf, arg)

            logging.debug(f'{self.logPrefix} {cmd} {args}')

        self.writer.write(buf.getbuffer())

        fut = asyncio.get_event_loop().create_future()
        self.waiters.append(fut)

        try:
            await self.writer.drain()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa
            self.close()
            raise

        return fut
