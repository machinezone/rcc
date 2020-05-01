'''Repeatitly print cluster info

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''
import asyncio
import logging

import click

from rcc.cluster.info import printRedisClusterInfoCoro


@click.command()
@click.option('--redis_urls', '-r', default='redis://localhost:11000')
@click.option('--password', '-a')
@click.option('--user')
@click.option('--role')
def cluster_nodes(redis_urls, password, user, role):
    '''Monitor redis metrics'''

    try:
        asyncio.get_event_loop().run_until_complete(
            printRedisClusterInfoCoro(redis_urls, password, user, role)
        )
    except Exception as e:
        logging.error(f'cluster_nodes error: {e}')
