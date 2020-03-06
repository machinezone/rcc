'''Repeatitly print cluster info

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''
import asyncio
import logging

import click

from rcc.cluster.info import printRedisClusterInfoCoro


@click.command()
@click.option('--redis_urls', '-r', default='redis://localhost:11000')
@click.option('--role')
def cluster_nodes(redis_urls, role):
    '''Monitor redis metrics'''

    try:
        asyncio.run(printRedisClusterInfoCoro(redis_urls, role))
    except Exception as e:
        logging.error(f'cluster_nodes error: {e}')
