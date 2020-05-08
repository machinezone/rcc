'''Repeatitly print cluster info

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''
import asyncio
import logging

import click

from rcc.cluster.info import clusterCheck


async def checkCluster(redisUrl, redisPassword, redisUser):
    try:
        ok = await clusterCheck(redisUrl, redisPassword, redisUser)
    except Exception as e:
        logging.error(f'checkCluster error: {e}')
        return

    if ok:
        click.secho('cluster ok', fg='green')
    else:
        click.secho('cluster unhealthy. Re-run with -v', fg='red')


@click.command()
@click.option(
    '--redis-url', '-u', envvar='RCC_REDIS_URL', default='redis://localhost:30001'
)
@click.option('--password', '-a')
@click.option('--user')
def cluster_check(redis_url, password, user):
    '''Make sure all nodes have the same view of the cluster
    '''

    try:
        asyncio.get_event_loop().run_until_complete(
            checkCluster(redis_url, password, user)
        )
    except Exception as e:
        logging.error(f'cluster-check error: {e}')
