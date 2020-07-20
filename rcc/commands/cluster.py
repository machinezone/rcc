'''Cluster commands

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import collections
import hiredis


ClusterNode = collections.namedtuple(
    'ClusterNode',
    [
        'node_id',
        'address',
        'ip',
        'port',
        'role',
        'flags',
        'slots',
        'importing_slots',
        'migrating_slots',
        'replicaof',
    ],
)


class ClusterCommandsMixin:
    async def cluster_nodes(self, skipFailedNodes=True):
        response = await self.send('CLUSTER', 'NODES')

        # ERR This instance has cluster support disabled'
        responseType = type(response)
        if responseType == hiredis.ReplyError:
            return []

        response = response.decode()

        nodes = []
        for line in response.splitlines():
            tokens = line.split()
            node_id = tokens[0]

            address = tokens[1]
            url, _, _ = address.partition('@')
            ip, _, port = url.partition(':')

            role = tokens[2]
            flags = role

            if skipFailedNodes and 'fail' in flags:
                continue

            if 'master' in role:
                role = 'master'
            elif 'slave' in role:
                role = 'slave'
            else:
                # Skip 'handshake' role, or any non master or slave one
                continue

            slots = []
            migrating_slots = []
            importing_slots = []

            for token in tokens[8:]:
                if token.startswith('['):
                    if '->-' in token:
                        migrating_slots.append(token)
                    elif '-<-' in token:
                        importing_slots.append(token)
                    else:
                        assert False, 'invalid redis server or redis server bug'
                elif '-' in token:
                    start, _, end = token.partition('-')
                    start = int(start)
                    end = int(end)
                    for i in range(start, end + 1):
                        slots.append(i)
                else:
                    slots.append(int(token))

            replicaof = 'na'
            if role == 'slave':
                replicaof = tokens[3]

            nodes.append(
                ClusterNode(
                    node_id,
                    address,
                    ip,
                    port,
                    role,
                    flags,
                    slots,
                    importing_slots,
                    migrating_slots,
                    replicaof,
                )
            )

        nodes = [(node.role, f'{node.ip}:{node.port}', node) for node in nodes]
        nodes.sort()
        nodes = [item[2] for item in nodes]

        return nodes
