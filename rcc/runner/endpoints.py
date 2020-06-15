'''Tools to display endpoints associated with a redis cluster deploy

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import os
import json

import click
import tabulate


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

    printEndpoints(service, port, full)
