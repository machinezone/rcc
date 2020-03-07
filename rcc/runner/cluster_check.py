'''Repeatitly print cluster info

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''
import asyncio
import logging

import click

from rcc.cluster.info import clusterCheck


async def checkCluster(redisUrl, redisPassword):
    try:
        ok = await clusterCheck(redisUrl, redisPassword)
    except Exception as e:
        logging.error(f'checkCluster error: {e}')
        return

    if ok:
        click.secho('cluster ok', fg='green')
    else:
        click.secho('cluster unhealthy. Re-run with -v', fg='red')


@click.command()
@click.option('--redis_url', '-r', default='redis://localhost:11000')
@click.option('--password', '-a')
def cluster_check(redis_url, password):
    '''Make sure all nodes have the same view of the cluster
    '''

    asyncio.run(checkCluster(redis_url, password))
