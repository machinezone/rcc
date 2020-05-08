'''Tool to analyze the keyspace

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import click

from rcc.cluster.keyspace_analyzer import analyzeKeyspace, writeWeightsToCsv
from rcc.plot import asciiPlot

#
# rcc keyspace -u redis://localhost:11000 --timeout 3
#
# Insert keys with this command
# redis-cli -p 11000 flushdb ; rcc publish -p 11000 --batch --random_channel
#


@click.command()
@click.option(
    '--redis-urls', '-u', envvar='RCC_REDIS_URL', default='redis://localhost:30001'
)
@click.option('--password', '-a')
@click.option('--user')
@click.option('--timeout', '-t', default=5)
@click.option('--port', default=6379)
@click.option('--path', '-w', default='weights.csv')
@click.option('--count', '-c', default=-1)
@click.option('--monitor', '-m', is_flag=True)
@click.option('--max_keys', '-k', default=50)
def keyspace(redis_urls, port, password, user, timeout, path, count, monitor, max_keys):
    '''Analyze the redis keyspace'''

    keySpace = asyncio.get_event_loop().run_until_complete(
        analyzeKeyspace(
            redis_urls, password, user, timeout, count=count, monitor=monitor
        )
    )
    weights = keySpace.keys
    writeWeightsToCsv(weights, path)

    temp = [(weight, key) for key, weight in keySpace.keys.items()]
    temp.sort()
    temp.reverse()
    temp = temp[:max_keys]
    keys = {v: k for k, v in temp}

    print()
    asciiPlot(f'Top {max_keys} keys', keys)
    asciiPlot('Commands', keySpace.commands)
    asciiPlot('Nodes', keySpace.nodes)
