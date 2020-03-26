'''Resharding tool

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.

There is a cluster-tool python project at https://github.com/projecteru/redis-trib.py
Which contains a migrate slot tool. It has different dependencies so we do not use it

cmd = '/Users/bsergeant/sandbox/venv/bin/redis-trib.py migrate'
cmd += ' --src-addr ' + f'{sourceNode.ip}:{sourceNode.port}'
cmd += ' --dst-addr ' + f'{destinationNode.ip}:{destinationNode.port}'
cmd += ' '            + f'{slot}'
print(cmd)
ret = os.system(cmd)
return ret == 0
'''

import asyncio
import collections
import csv
import logging
import os
import sys
import time

from rcc.client import RedisClient
from rcc.hash_slot import getHashSlot
from rcc.binpack import to_constant_bin_number
from rcc.cluster.info import getSlotsToNodesMapping, clusterCheck


def makeClientfromNode(node, redisPassword):
    url = f'redis://{node.ip}:{node.port}'
    return RedisClient(url, redisPassword)


async def migrateSlot(
    masterClients, redisPassword, slot, sourceNode, destinationNode, dry=False
):
    '''Migrate a slot to a node'''
    logging.info(
        f'migrate from {sourceNode.node_id} to {destinationNode.node_id} slot [{slot}]'
    )

    if dry:
        src = f'redis://{sourceNode.ip}:{sourceNode.port}'
        dst = f'redis://{destinationNode.ip}:{destinationNode.port}'

        passwordOption = ''
        if redisPassword:
            passwordOption = f'--password {redisPassword}'

        print(f'rcc migrate --src-addr {src} --dst-addr {dst} {slot} {passwordOption}')
        return True

    sourceClient = makeClientfromNode(sourceNode, redisPassword)
    destinationClient = makeClientfromNode(destinationNode, redisPassword)

    # 1. Set the destination node slot to importing state using CLUSTER SETSLOT
    #    <slot> IMPORTING <source-node-id>.
    try:
        await destinationClient.send(
            'CLUSTER', 'SETSLOT', slot, 'IMPORTING', sourceNode.node_id
        )
    except Exception as e:
        logging.error(f'error with SETSLOT IMPORTING command: {e}')
        return False

    # 2. Set the source node slot to migrating state using CLUSTER SETSLOT
    #    <slot> MIGRATING <destination-node-id>.
    try:
        await sourceClient.send(
            'CLUSTER', 'SETSLOT', slot, 'MIGRATING', destinationNode.node_id
        )
    except Exception as e:
        logging.error(f'error with SETSLOT MIGRATING command: {e}')
        return False

    # 3. Get keys from the source node with CLUSTER GETKEYSINSLOT command and
    #    move them into the destination node using the MIGRATE command.
    while True:

        # Migrate 100 keys at a time
        batchSize = 100
        keys = await sourceClient.send('CLUSTER', 'GETKEYSINSLOT', slot, batchSize)

        if len(keys) == 0:
            break

        print('migrating', len(keys), 'keys')
        host = destinationNode.ip
        port = destinationNode.port
        db = 0
        timeout = 5000  # 5 seconds timeout
        try:
            args = ['MIGRATE', host, port, "", db, timeout]

            if redisPassword:
                args.append('AUTH')
                args.append(redisPassword)

            args.append("KEYS")
            for key in keys:
                args.append(key)

            await sourceClient.send(*args)
        except Exception as e:
            logging.error(f'error with MIGRATE command: {e}')
            return False

    # 4. Use CLUSTER SETSLOT <slot> NODE <destination-node-id> in the source or
    #    destination.
    # set the slot owner for every node in the cluster
    for client in masterClients:
        try:
            await client.send(
                'CLUSTER', 'SETSLOT', slot, 'NODE', destinationNode.node_id
            )
        except Exception as e:
            logging.error(f'error with SETSLOT NODE command: {e}')
            return False

    return True


async def waitForClusterViewToBeConsistent(redisUrls, redisPassword, timeout):
    print('Waiting for cluster view to be consistent...')
    start = time.time()

    # give us 'timeout' seconds max for all nodes to agree

    while True:
        sys.stderr.write('.')
        sys.stderr.flush()

        ok = await clusterCheck(redisUrls, redisPassword)
        if ok:
            break

        if time.time() - start > timeout:
            logging.error(f'timeout exceeded')
            return False
        else:
            waitTime = 0.5
            await asyncio.sleep(waitTime)

    return True


async def runClusterCheck(port):
    cmd = f'redis-cli --cluster check localhost:{port}'

    proc = await asyncio.create_subprocess_shell(cmd)
    stdout, stderr = await proc.communicate()


async def binPackingReshardCoroutine(
    redisUrls, redisPassword, weights, timeout, dry=False, nodeId=None
):
    redisClient = RedisClient(redisUrls, redisPassword)
    nodes = await redisClient.cluster_nodes()

    # There will be as many bins as there are master nodes
    masterNodes = [node for node in nodes if node.role == 'master']
    masterClients = [makeClientfromNode(node, redisPassword) for node in masterNodes]
    binCount = len(masterNodes)

    # Multiple keys could hash to the same hash-slot (collisions), so
    # we need to feed to binpacking a list of [slot: weight], not
    # a list of [key: weight]
    hashSlotWeights = collections.defaultdict(int)
    for key, weight in weights.items():
        slot = getHashSlot(key)
        hashSlotWeights[slot] += weight

    # Run the bin packing algorithm
    bins = to_constant_bin_number(hashSlotWeights, binCount)

    # A list of list of slots to migrate, for each node
    allSlots = []

    for b in bins:
        # b is a dictionary of [name, weight] / name is the hash slot.
        # we want to sort by hash slot to make this process deterministic
        binSlots = [slot for slot in b.keys()]
        binSlots.sort()
        allSlots.append(binSlots)

    # We need to know where each slots lives
    slotToNodes = await getSlotsToNodesMapping(redisUrls, redisPassword)

    totalMigratedSlots = 0

    for binSlots, node in zip(allSlots, masterNodes):

        print(f'== {node.node_id} / {node.ip}:{node.port} ==')
        migratedSlots = 0

        if nodeId is not None and node.node_id != nodeId:
            continue

        for slot in binSlots:
            sourceNode = slotToNodes[slot]
            logging.debug(f'{slot} owned by {sourceNode.node_id}')

        # Migrate each slot
        for slot in binSlots:
            # recompute the slots to node mapping after each node migration
            slotToNodes = await getSlotsToNodesMapping(redisUrls, redisPassword)

            sourceNode = slotToNodes[slot]
            if sourceNode.node_id != node.node_id:

                ret = await migrateSlot(
                    masterClients, redisPassword, slot, sourceNode, node, dry
                )
                if not ret:
                    return False

                migratedSlots += 1

        print(f'migrated {migratedSlots} slots')
        totalMigratedSlots += migratedSlots

        #
        # This section is key.
        # We periodically make sure that all nodes in the cluster agree on their view
        # of the cluster, mostly on how slots are allocated
        #
        # Without this wait, if we try to keep on moving other slots
        # the cluster will become broken,
        # and commands such as redis-cli --cluste check will report it as inconsistent
        #
        # note that existing redis cli command do not migrate to multiple nodes at once
        # while this script does
        #
        consistent = await waitForClusterViewToBeConsistent(
            redisUrls, redisPassword, timeout
        )
        if not consistent:
            return False

    print(f'total migrated slots: {migratedSlots}')
    return True


def binPackingReshard(redisUrls, redisPassword, path, timeout, dry=False, nodeId=None):
    if not os.path.exists(path):
        logging.error(f'{path} does not exists')
        return False

    with open(path) as csvfile:
        reader = csv.reader(csvfile)

        weights = {}
        try:
            for row in reader:
                key = row[0]
                weight = row[1]
                weights[key] = int(weight)

        except csv.Error as ex:
            logging.error(
                'error parsing csv file {}, line {}: {}'.format(
                    path, reader.line_num, ex
                )
            )
            return False

    return asyncio.run(
        binPackingReshardCoroutine(
            redisUrls, redisPassword, weights, timeout, dry, nodeId
        )
    )
