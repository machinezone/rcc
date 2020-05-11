'''Tools to help initialize a redis cluster on kubernete

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import logging
import tempfile

import click

from rcc.cluster.init_cluster import runNewCluster


#
# FIXME: need option to set the number of replicas
#
@click.command()
@click.option('--size', default=3, type=int)
@click.option('--replicas', default=1, type=int)
@click.option('--start_port', default=30001, type=int)
@click.option('--password', '-a')
@click.option('--user')
@click.option('--manual', '-m', is_flag=True)
def make_cluster(size, start_port, password, user, replicas, manual):
    '''Create, initialize and run a redis cluster
    and a redis cluster proxy'''
    root = tempfile.mkdtemp()

    try:
        asyncio.get_event_loop().run_until_complete(
            runNewCluster(root, start_port, size, password, user, replicas, manual)
        )
    except Exception as e:
        logging.error(f'cluster_nodes error: {e}')
