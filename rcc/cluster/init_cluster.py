'''Help create a temp cluster

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import json
import os
import sys
import time
import logging

import click

from rcc.cluster.create import ClusterCreateArgs, makeCreateCmd, createCluster
from rcc.cluster.info import clusterCheck, printRedisClusterInfoCoro
from rcc.client import RedisClient


async def findFreePorts(count):
    ports = []

    for port in range(5000, 50000):
        writer = None
        try:
            _, writer = await asyncio.open_connection('localhost', port)
            # if we can connect it's not good
        except Exception:
            ports.append(port)
            if len(ports) == count:
                return ports
        finally:
            if writer is not None:
                writer.close()

    raise ValueError('Cannot find a free port')


def makeServerConfig(
    root, clusterReadyFile, portRange, masterNodeCount, password, user, replicas
):
    # create config files
    nodeCount = masterNodeCount * (1 + replicas)
    for i in range(nodeCount):

        serverPath = os.path.join(root, f'server{i}.conf')
        with open(serverPath, 'w') as f:
            # Config file contains:
            # cluster-config-file nodes-1.conf
            # dbfilename dump1.rdb
            f.write(f'cluster-config-file nodes-{i}.conf' + '\n')
            f.write(f'dbfilename dump{i}.rdb' + '\n')

            if user:
                # Unclear whether I need a replica-user / I don't think so
                f.write('user default off nopass ~* +@all' + '\n')
                f.write(f'user {user} on >{password} ~* +@all' + '\n')
                f.write(f'masteruser {user}' + '\n')
                f.write(f'masterauth {password}' + '\n')
            elif password:
                f.write(f'requirepass {password}' + '\n')
                f.write(f'masterauth {password}' + '\n')

    ips = ' '.join([f'127.0.0.1:{port}' for port in portRange])

    # Create a Procfile
    # server1: redis-server server1.conf --protected-mode no ...
    # server2: redis-server server2.conf --protected-mode no ...
    # proxy: ...

    # Environment file to set the root folder
    envPath = os.path.join(root, f'.env')
    with open(envPath, 'w') as f:
        f.write(f'ROOT={root}')

    procfile = os.path.join(root, 'Procfile')
    with open(procfile, 'w') as f:
        for i, port in enumerate(portRange):
            f.write(f'server{i}: redis-server server{i}.conf ')
            f.write(f'--protected-mode no --cluster-enabled yes --port {port}\n')

    # Print cluster init command
    host = 'localhost'
    port = portRange[0]
    args = ClusterCreateArgs(masterNodeCount, host, port, password, user, ips, replicas)
    return args


async def runServer(root, serverIdx, port):
    try:
        cmd = (
            f'redis-server server{serverIdx}.conf '
            + f'--protected-mode no --cluster-enabled yes --port {port}\n'
        )

        proc = await asyncio.create_subprocess_shell(cmd, cwd=root)
        stdout, stderr = await proc.communicate()

    except asyncio.CancelledError:
        print(f'Cancelling server running on port {port}')
        proc.terminate()


async def initCluster(cmd):
    proc = await asyncio.create_subprocess_shell(cmd)
    stdout, stderr = await proc.communicate()


async def checkOpenedPort(portRange, timeout: int):
    # start by making sure that all ports are free.
    # There is still room for data race but it's better than nothing
    start = time.time()

    for port in portRange:
        while True:
            sys.stderr.write('.')
            sys.stderr.flush()

            if time.time() - start > timeout:
                sys.stderr.write('\n')
                raise ValueError(f'Timeout trying to check opened ports {portRange}')

            writer = None
            try:
                _, writer = await asyncio.open_connection('localhost', port)
                # if we can connect it's not good, wait a bit, or
                # we could straight out error out
                await asyncio.sleep(0.1)
            except Exception:
                break
            finally:
                if writer is not None:
                    writer.close()

    sys.stderr.write('\n')


# FIXME: cobra could use this version
async def waitForAllConnectionsToBeReady(url, password, user, timeout: int):
    start = time.time()

    while True:
        sys.stderr.write('.')
        sys.stderr.flush()

        try:
            redis = RedisClient(url, password, user)
            await redis.connect()
            await redis.send('PING')
            redis.close()
            break
        except Exception as e:
            if time.time() - start > timeout:
                sys.stderr.write('\n')
                raise

            logging.warning(e)

            waitTime = 0.1
            await asyncio.sleep(waitTime)

    sys.stderr.write('\n')


async def runNewCluster(
    root,
    clusterReadyFile,
    startPort,
    size,
    password,
    user,
    replicas=1,
    manual=False,
    init=True,
):
    start = time.time()
    size = int(size)

    nodesCount = (1 + replicas) * size
    if startPort == 0:
        portRange = await findFreePorts(nodesCount)
    else:
        portRange = [port for port in range(startPort, startPort + nodesCount)]

    click.secho(f'1/6 Creating server config for range {portRange}', bold=True)

    createArgs = makeServerConfig(
        root, clusterReadyFile, portRange, size, password, user, replicas
    )

    click.secho('2/6 Check that ports are opened', bold=True)
    await checkOpenedPort(portRange, timeout=10)

    try:
        click.secho(f'3/6 Configuring and running', bold=True)

        tasks = []
        for i, port in enumerate(portRange):
            task = asyncio.ensure_future(runServer(root, i, port))
            tasks.append(task)

        # This might help with timing issues on CI ... see below
        await asyncio.sleep(0.5)

        #
        # ... waitForAllConnectionsToBeReady returns too early the last
        # instance running on port 5005 is checked after we start creating
        # the cluster ... ??
        #
        # 2020-07-17T00:23:16.2221860Z 4/6 Wait for the cluster nodes to be running
        # 2020-07-17T00:23:16.5892240Z Checking redis://localhost:5000 ....
        # 2020-07-17T00:23:16.5920290Z Checking redis://localhost:5001 .
        # 2020-07-17T00:23:16.5948040Z Checking redis://localhost:5002 .
        # 2020-07-17T00:23:16.5971910Z Checking redis://localhost:5003 .
        # 2020-07-17T00:23:16.6003960Z Checking redis://localhost:5004 .
        # 2020-07-17T00:23:16.6034590Z 5/6 Create the cluster
        # 2020-07-17T00:23:16.6036360Z Performing hash slots allocation on 3 nodes...
        # 2020-07-17T00:23:16.6656430Z Master[0] -> Slotes 0 - 5460
        # 2020-07-17T00:23:16.6657070Z Master[1] -> Slotes 5461 - 10921
        # 2020-07-17T00:23:16.6657540Z Master[2] -> Slotes 10922 - 16383
        # 2020-07-17T00:23:16.6657670Z >>> Assign a different config epoch to each node
        # 2020-07-17T00:23:16.7187930Z Sending CLUSTER MEET messages to join the cluster
        # 2020-07-17T00:23:17.8346500Z Checking redis://localhost:5005 .
        #

        # Check that all connections are ready
        click.secho(f'4/6 Wait for the cluster nodes to be running', bold=True)
        urls = [f'redis://localhost:{port}' for port in portRange]
        for url in urls:
            sys.stderr.write(f'Checking {url} ')
            await waitForAllConnectionsToBeReady(url, password, user, timeout=5)

        if init:
            # Initialize the cluster (master/slave assignments, etc...)
            click.secho(f'5/6 Create the cluster', bold=True)
            if manual:
                # Do it ourself
                await createCluster(createArgs)
            else:
                # Use redis-cli
                createCmd = makeCreateCmd(createArgs)
                await initCluster(createCmd)

            # We just initialized the cluster, wait until
            # it is 'consistent' and good to use
            click.secho(f'6/6 Wait for all cluster nodes to be consistent', bold=True)

            redisUrl = f'redis://localhost:{portRange[0]}'
            while True:
                try:
                    info = await clusterCheck(redisUrl, password, user)
                except Exception:
                    pass

                if info['success']:
                    if not info['all_balanced']:
                        logging.warning('The cluster is not balanced.')
                        logging.warning('Some master do not have a replica.')
                    break

                print('Waiting for cluster to be consistent...')
                await asyncio.sleep(1)

        print()
        await printRedisClusterInfoCoro(urls[0], password, user)
        print()

        secs = '%0.2f' % (time.time() - start)
        click.secho(f'Cluster ready in {secs} seconds !', fg='green')
        click.secho(f'Config files created in folder {root}', fg='cyan')

        # write into start port ... a bit ugly
        startPort = portRange[0]

        with open(clusterReadyFile, 'w') as f:
            f.write(json.dumps({'start_port': portRange[0]}))

        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        print('Cancelling cluster')

    finally:
        for task in tasks:
            task.cancel()
