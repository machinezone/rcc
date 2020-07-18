'''Repeatitly print cluster info

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''
import asyncio
import logging
import traceback

import click

from rcc.cluster.info import clusterCheck


async def checkCluster(redisUrl, redisPassword, redisUser):
    try:
        info = await clusterCheck(redisUrl, redisPassword, redisUser)
    except Exception as e:
        logging.error(f'checkCluster error: {e}')
        return

    if not info['all_balanced']:
        logging.warning('The cluster is not balanced.')
        logging.warning('Some master do not have a replica.')

    if info['success']:
        click.secho('cluster ok', fg='green')
    else:
        click.secho('cluster unhealthy. Re-run with -v or -v -v.', fg='red')


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
        backtrace = traceback.format_exc()
        logging.debug(f'cluster_nodes traceback: {backtrace}')
        logging.error(f'cluster-check error: {e}')
