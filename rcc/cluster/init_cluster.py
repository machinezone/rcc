'''Help create a temp cluster

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import os
import sys
import time
import logging
import distutils.spawn

import click

from rcc.cluster.create import ClusterCreateArgs, makeCreateCmd, createCluster
from rcc.cluster.info import clusterCheck
from rcc.client import RedisClient


def hasExecutable(program):
    return distutils.spawn.find_executable(program)


def makeServerConfig(
    root,
    readyPath,
    startPort=11000,
    masterNodeCount=3,
    password=None,
    user=None,
    replicas=1,
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

    ips = ' '.join(['127.0.0.1:' + str(startPort + i) for i in range(nodeCount)])

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
        for i in range(nodeCount):
            port = startPort + i
            f.write(f'server{i}: redis-server server{i}.conf ')
            f.write(f'--protected-mode no --cluster-enabled yes --port {port}\n')

        if not hasExecutable('redis-cluster-proxy'):
            logging.warning('****************************************')
            logging.warning('* redis-cluster-proxy is not available *')
            logging.warning('****************************************')
        else:
            #
            # Use a simple shell expression to only start the proxy
            # when the server is ready
            # $ while test ! -f /tmp/bar ; do sleep 1 ; echo waiting ; done ; echo READY
            # waiting
            # waiting
            # READY
            #
            # The 'ready file' will be created when the cluster is ready.
            #
            msg = 'waiting for cluster to be up to start proxy'
            filename = os.path.basename(readyPath)
            f.write('proxy: ')
            f.write(
                f'while test ! -f $ROOT/{filename}; do sleep 3; echo "{msg}"; done; '
            )

            auth = ''
            if password:
                auth += f'-a {password}'
                if user:
                    # Maybe redis-cluster-proxy should support a --user option instead
                    # of --auth-user to be consistent with redis-cli
                    auth += f' --auth-user {user}'

            f.write(f'redis-cluster-proxy {auth} --port {port+1} {ips}')

    # Print cluster init command
    host = 'localhost'
    port = startPort
    args = ClusterCreateArgs(masterNodeCount, host, port, password, user, ips, replicas)
    return args


async def runServer(root, startPort):
    try:
        honcho = os.path.join(os.path.dirname(sys.executable), 'honcho')
        proc = await asyncio.create_subprocess_shell(f'{honcho} start', cwd=root)
        stdout, stderr = await proc.communicate()

    except asyncio.CancelledError:
        print('Cancelling honcho')
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

            # FIXME there's probably a more portable thing that using nc ;
            #       the timeout option (-w 1) is not portable
            cmd = f'nc -vz -w 1 localhost {port} 2> /dev/null'
            ret = os.system(cmd)

            if ret == 0:
                # if we can connect it's not good, wait a bit, or
                # we could straight out error out
                await asyncio.sleep(0.1)
            else:
                break

    sys.stderr.write('\n')


# FIXME: cobra could use this version
async def waitForAllConnectionsToBeReady(urls, password, user, timeout: int):
    start = time.time()

    for url in urls:
        sys.stderr.write(f'Checking {url} ')

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
    root, startPort, size, password, user, replicas=1, manual=False
):
    size = int(size)

    # FIXME: port range does not deal with redis-cluster-proxy
    portRange = [port for port in range(startPort, startPort + (1 + replicas) * size)]
    click.secho(f'1/6 Creating server config for range {portRange}', bold=True)

    readyPath = os.path.join(root, 'redis_cluster_ready')
    createArgs = makeServerConfig(
        root, readyPath, startPort, size, password, user, replicas
    )

    click.secho('2/6 Check that ports are opened', bold=True)
    await checkOpenedPort(portRange, timeout=10)

    try:
        click.secho(f'3/6 Configuring and running', bold=True)
        task = asyncio.ensure_future(runServer(root, startPort))

        # Check that all connections are ready
        click.secho(f'4/6 Wait for the cluster nodes to be running', bold=True)
        urls = [f'redis://localhost:{port}' for port in portRange]
        await waitForAllConnectionsToBeReady(urls, password, user, timeout=5)

        # Initialize the cluster (master/slave assignments, etc...)
        click.secho(f'5/6 Create the cluster', bold=True)
        if manual:
            # Do it ourself
            await createCluster(createArgs)
        else:
            # Use redis-cli
            createCmd = makeCreateCmd(createArgs)
            await initCluster(createCmd)

        # We just initialized the cluster, wait until it is 'consistent' and good to use
        click.secho(f'6/6 Wait for all cluster nodes to be consistent', bold=True)

        redisUrl = f'redis://localhost:{startPort}'
        while True:
            ret = False
            try:
                ret = await clusterCheck(redisUrl, password, user)
            except Exception:
                pass

            if ret:
                break

            print('Waiting for cluster to be consistent...')
            await asyncio.sleep(1)

        click.secho('Cluster ready !', fg='green')
        click.secho(f'Config files created in folder {root}', fg='cyan')

        with open(readyPath, 'w') as f:
            f.write('cluster ready')

        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        print('Cancelling cluster')

    finally:
        task.cancel()
