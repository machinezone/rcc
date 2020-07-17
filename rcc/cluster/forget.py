'''Forget a node from a cluster

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''
import logging

from rcc.client import RedisClient
from rcc.cluster.reshard import makeClientfromNode


async def clusterForgetNode(redisUrl, redisPassword, redisUser, nodeId):
    redisClient = RedisClient(redisUrl, redisPassword, redisUser)
    nodes = await redisClient.cluster_nodes()

    for node in nodes:
        if node.node_id == nodeId:
            continue

        client = makeClientfromNode(node, redisPassword, redisUser)

        try:
            await client.send('CLUSTER', 'FORGET', nodeId)
        except Exception as e:
            logging.warning(f'error with CLUSTER FORGET command: {e}')
            continue
