'''Utility to know which version

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''
import os


def getRedisServerMajorVersion():
    cmd = f'redis-server --version'
    output = os.popen(cmd).read()
    for token in output.split():
        if token.startswith('v='):
            version = token.split('=')[1]
            major, _, _ = version.partition('.')
            return int(major)

    raise ValueError('Cannot compute redis-server version')
