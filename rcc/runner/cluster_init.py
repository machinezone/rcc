'''Tools to help initialize a redis cluster on kubernete or locally

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''
import asyncio
import click
import json
import os
import logging
import traceback

from rcc.cluster.create import ClusterCreateArgs, createCluster


def getEndpointsIps(service):
    '''
    kubectl get endpoints -o json redis-cluster
    '''

    content = os.popen(f'kubectl get endpoints -o json {service}').read()
    data = json.loads(content)

    assert len(data['subsets']) == 1
    assert 'addresses' in data['subsets'][0]
    addresses = data['subsets'][0]['addresses']

    ips = []
    for address in addresses:
        ip = address.get('ip')
        ips.append(ip)

    return ips


def printRedisClusterInitCommand(service, port):
    cmd = 'redis-cli --cluster create '

    ips = getEndpointsIps(service)

    for ip in ips:
        cmd += f'{ip}:{port} '

    cmd += ' --cluster-replicas 1'

    print(cmd)


@click.command()
@click.option('--service', default='redis-cluster')
@click.option('--port', default=6379)
@click.option('--k8s', is_flag=True)
@click.option('--size', default=3, type=int)
@click.option('--replicas', default=1, type=int)
@click.option('--host', default='127.0.0.1')
@click.option('--start_port', '-p', default=30001, type=int)
@click.option('--password', '-a')
@click.option('--user')
@click.option('--ips')
def cluster_init(
    service, port, k8s, size, replicas, host, start_port, password, user, ips
):
    '''Print a cluster init command for redis url defined in a kubernete endpoints'''

    try:
        if k8s:
            printRedisClusterInitCommand(service, port)
        else:
            # new code
            masterNodeCount = size
            if ips is None:
                nodesCount = (1 + replicas) * size
                portRange = [
                    port for port in range(start_port, start_port + nodesCount)
                ]
                ips = ' '.join([f'{host}:{port}' for port in portRange])

            args = ClusterCreateArgs(
                masterNodeCount, host, port, password, user, ips, replicas
            )

            asyncio.get_event_loop().run_until_complete(createCluster(args))

    except Exception as e:
        backtrace = traceback.format_exc()
        logging.debug(f'traceback: {backtrace}')
        logging.error(f'cluster-init error: {e}')
