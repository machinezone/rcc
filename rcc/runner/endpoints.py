'''Tools to display endpoints associated with a redis cluster deploy

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import logging
import os
import json
import tempfile
import traceback

import click
import tabulate


def getEndpointsIps(service):
    '''
    kubectl get endpoints -o json redis-cluster
    '''

    with tempfile.NamedTemporaryFile() as f:
        path = f.name
        ret = os.system(f'kubectl get endpoints -o json {service} > {path}')
        if ret != 0:
            return []

        f.flush()
        content = f.read()

    try:
        data = json.loads(content)
    except Exception as e:
        logging.error(f'error parsing json {e}')
        return []

    assert len(data['subsets']) == 1
    assert 'addresses' in data['subsets'][0]
    addresses = data['subsets'][0]['addresses']

    ips = []
    for address in addresses:
        ip = address.get('ip')
        name = address.get('targetRef', {}).get('name')
        ips.append((ip, name))

    return ips


def printEndpoints(service, port, full):
    ips = getEndpointsIps(service)

    if full:
        rows = [['ip', 'name']]
        rows.extend(ips)
        print(tabulate.tabulate(rows, tablefmt="simple", headers="firstrow"))
    else:
        endpoints = []
        for ip, _ in ips:
            endpoints.append(f'redis://{ip}:{port}')

        print(';'.join(endpoints))


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
@click.option('--full', is_flag=True)
def endpoints(service, port, full):
    '''Print endpoints associated with a redis cluster service'''

    try:
        printEndpoints(service, port, full)
    except Exception as e:
        backtrace = traceback.format_exc()
        logging.debug(f'traceback: {backtrace}')
        logging.error(f'endpoints error: {e}')
