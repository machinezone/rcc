'''Cluster info tools

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import asyncio
import collections
import hashlib
import logging

from rcc.client import RedisClient
from rcc.version import getRedisServerMajorVersion


async def getSlotsToNodesMapping(redisClient):
    nodes = await redisClient.cluster_nodes()

    masterNodes = [node for node in nodes if node.role == 'master']

    # We need to know where each slots lives
    slotToNodes = {}
    for node in masterNodes:
        for slot in node.slots:
            slotToNodes[slot] = node

    return slotToNodes


def getSlotsRange(slots):
    '''I failed the programming interview quizz but the function
       works like redis CLUSTER NODES
    '''

    if len(slots) == 0:
        return ''

    ranges = []

    equal = False
    firstSlot = slots[0]

    for i in range(1, len(slots)):

        if slots[i - 1] + 1 == slots[i]:
            # last entry
            if i == (len(slots) - 1):
                ranges.append((firstSlot, slots[i]))
            continue
        else:
            equal = False
            ranges.append((firstSlot, slots[i - 1]))
            firstSlot = slots[i]

        # last entry
        if i == (len(slots) - 1):
            if not equal:
                ranges.append((slots[i], slots[i]))
            else:
                ranges.append((firstSlot, slots[i]))

    res = []
    for r in ranges:
        if r[0] == r[1]:
            res.append(str(r[0]))
        else:
            res.append('{}-{}'.format(r[0], r[1]))

    return ' '.join(res)


async def printRedisClusterInfoCoro(
    redisUrl, redisPassword, redisUser, role=None, displaySlots=True
):
    redisClient = RedisClient(redisUrl, redisPassword, redisUser)
    nodes = await redisClient.cluster_nodes()

    # build slave/master table, and the set of master
    replicas = collections.defaultdict(list)
    masters = set()
    for node in nodes:
        if node.role == 'master':
            masters.add(node.node_id)
        elif node.role == 'slave':
            replicas[node.replicaof].append(node.node_id)

    for node in nodes:
        if role is not None and node.role != role:
            continue

        slotRange = getSlotsRange(node.slots)
        info = [node.node_id, node.ip + ':' + node.port, node.role]
        if node.role == 'master':
            replicaCount = len(replicas.get(node.node_id, []))
            slotCount = len(node.slots)

            if replicaCount > 1:
                info.append(f'{replicaCount} replicas')
            else:
                info.append(f'{replicaCount} replica')

            if slotCount > 1:
                info.append(f'{slotCount} slots')
            else:
                info.append(f'{slotCount} slot')

            if displaySlots:
                info.append(slotRange)
        elif node.role == 'slave':
            label = 'missing' if node.replicaof not in masters else ''
            info.append(f'replicates {node.replicaof} {label}')

        print(*info)


async def getClusterSignature(redisUrl, redisPassword, redisUser):
    redisClient = RedisClient(redisUrl, redisPassword, redisUser)
    nodes = await redisClient.cluster_nodes()

    roles = collections.defaultdict(int)
    allSlots = set()

    signature = ''
    for node in nodes:
        roles[node.role] += 1

        slotRange = getSlotsRange(node.slots)
        tokens = [node.node_id, node.ip + ':' + node.port, node.role, slotRange]
        signature += ' '.join(tokens) + '\n'

        for slot in node.slots:
            allSlots.add(slot)

    fullCoverage = len(allSlots) == 16384
    balanced = roles['master'] <= roles['slave']

    return signature, balanced, fullCoverage


async def getClusterUrls(redisUrl, redisPassword, redisUser):
    redisClient = RedisClient(redisUrl, redisPassword, redisUser)
    nodes = await redisClient.cluster_nodes()

    urls = []
    for node in nodes:
        url = f'redis://{node.ip}:{node.port}'
        urls.append(url)

    return urls


async def getClusterNodesCount(redisUrl, redisPassword, redisUser):
    redisClient = RedisClient(redisUrl, redisPassword, redisUser)
    nodes = await redisClient.cluster_nodes()
    return len(nodes)


async def clusterCheck(redisUrl, redisPassword, redisUser):
    '''
    Get all the nodes in the cluster
    Then ask each nodes its view of the cluster (mostly allocated slots)
    Compare each view and make sure they are consistent
    '''
    urls = await getClusterUrls(redisUrl, redisPassword, redisUser)

    signatures = set()

    allBalanced = True
    allCovered = True

    for url in urls:
        signature, balanced, fullCoverage = await getClusterSignature(
            url, redisPassword, redisUser
        )
        signatures.add(signature)

        allBalanced = allBalanced and balanced
        allCovered = allCovered and fullCoverage

        cksum = hashlib.md5(signature.encode('utf-8')).hexdigest()

        logging.info(f'node {url} cluster representation checksum {cksum} balanced {balanced} coverage {fullCoverage}')
        logging.debug('\n' + signature)

    logging.info(f'{len(signatures)} unique signatures')

    return {
        'success': len(signatures) == 1 and allCovered,
        'all_covered': allCovered,
        'all_balanced': allBalanced,
    }


async def runRedisCliClusterCheck(port, redisPassword, redisUser):
    serverVersion = getRedisServerMajorVersion()
    if serverVersion < 5:
        logging.warning('cluster check not supported in redis-cli')
        return

    auth = ''
    if redisPassword:
        auth += f'-a {redisPassword}'
        if redisUser:
            auth += f' --user {redisUser}'

    cmd = f'redis-cli {auth} --cluster check localhost:{port}'

    proc = await asyncio.create_subprocess_shell(cmd)
    stdout, stderr = await proc.communicate()
