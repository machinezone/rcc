'''Tool to analyze the keyspace

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import click

from rcc.cluster.keyspace_analyzer import analyzeKeyspace, writeWeightsToCsv
from rcc.plot import asciiPlot

#
# rcc analyze-keyspace --redis_urls redis://localhost:11000 --timeout 3
#
# Insert keys with this command
# redis-cli -p 11000 flushdb ; rcc publish -p 11000 --batch --random_channel
#


@click.command()
@click.option('--redis_urls', '-r', default='redis://localhost')
@click.option('--redis_password', '-a')
@click.option('--timeout', '-t', default=5)
@click.option('--port', default=6379)
@click.option('--path', '-w', default='weights.csv')
@click.option('--quiet', '-q', is_flag=True)
@click.option('--count', '-c', default=-1)
@click.option('--monitor', '-m', is_flag=True)
@click.option('--max_keys', '-k', default=50)
def keyspace(
    redis_urls, port, redis_password, timeout, path, quiet, count, monitor, max_keys
):
    '''Analyze the keyspace'''

    keySpace = asyncio.run(
        analyzeKeyspace(
            redis_urls,
            redis_password,
            timeout,
            progress=not quiet,
            count=count,
            monitor=monitor,
        )
    )
    weights = keySpace.keys
    writeWeightsToCsv(weights, path)

    temp = [(weight, key) for key, weight in keySpace.keys.items()]
    temp.sort()
    temp.reverse()
    temp = temp[:max_keys]
    keys = {v: k for k, v in temp}

    asciiPlot(f'Top {max_keys} keys', keys)
    asciiPlot('Commands', keySpace.commands)
    asciiPlot('Nodes', keySpace.nodes)
