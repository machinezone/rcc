'''Error classes, from aio-redis

The MIT License (MIT)

Copyright (c) 2014-2017 Alexey Popravka

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

from typing import Optional, Sequence  # noqa

__all__ = [
    'RedisError',
    'ProtocolError',
    'ReplyError',
    'MaxClientsError',
    'AuthError',
    'PipelineError',
    'MultiExecError',
    'WatchVariableError',
    'ChannelClosedError',
    'ConnectionClosedError',
    'ConnectionForcedCloseError',
    'PoolClosedError',
    'MasterNotFoundError',
    'SlaveNotFoundError',
    'ReadOnlyError',
]


class RedisError(Exception):
    """Base exception class for aioredis exceptions."""


class ProtocolError(RedisError):
    """Raised when protocol error occurs."""


class ReplyError(RedisError):
    """Raised for redis error replies (-ERR)."""

    MATCH_REPLY = None  # type: Optional[Sequence[str]]

    def __new__(cls, msg, *args):
        for klass in cls.__subclasses__():
            if msg and klass.MATCH_REPLY and msg.startswith(klass.MATCH_REPLY):
                return klass(msg, *args)
        return super().__new__(cls, msg, *args)


class MaxClientsError(ReplyError):
    """Raised for redis server when the maximum number of client has been
    reached."""

    MATCH_REPLY = "ERR max number of clients reached"


class AuthError(ReplyError):
    """Raised when authentication errors occurs."""

    MATCH_REPLY = (
        "NOAUTH ",
        "ERR invalid password",
        "ERR Client sent AUTH, but no password is set",
    )


class BusyGroupError(ReplyError):
    """Raised if Consumer Group name already exists."""

    MATCH_REPLY = "BUSYGROUP Consumer Group name already exists"


class PipelineError(RedisError):
    """Raised if command within pipeline raised error."""

    def __init__(self, errors):
        super().__init__('{} errors:'.format(self.__class__.__name__), errors)


class MultiExecError(PipelineError):
    """Raised if command within MULTI/EXEC block caused error."""


class WatchVariableError(MultiExecError):
    """Raised if watched variable changed (EXEC returns None)."""


class ChannelClosedError(RedisError):
    """Raised when Pub/Sub channel is unsubscribed and messages queue is empty.
    """


class ReadOnlyError(RedisError):
    """Raised from slave when read-only mode is enabled"""


class MasterNotFoundError(RedisError):
    """Raised for sentinel master not found error."""


class SlaveNotFoundError(RedisError):
    """Raised for sentinel slave not found error."""


class MasterReplyError(RedisError):
    """Raised by sentinel client for master error replies."""


class SlaveReplyError(RedisError):
    """Raised by sentinel client for slave error replies."""


class ConnectionClosedError(RedisError):
    """Raised if connection to server was closed."""


class ConnectionForcedCloseError(ConnectionClosedError):
    """Raised if connection was closed with .close() method."""


class PoolClosedError(RedisError):
    """Raised if pool is closed."""
