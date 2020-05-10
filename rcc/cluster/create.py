'''Cluster creation (ADDSLOTS, MEET, etc...)

Copyright (c) 2020 Machine Zone, Inc. All rights reserved.
'''

import collections


ClusterCreateArgs = collections.namedtuple(
    'ClusterCreateArgs', ['host', 'port', 'password', 'user', 'ips', 'replicas']
)


def makeCreateCmd(args):
    # FIXME test hack when using redis-4
    # redisCli = '/usr/local/Cellar/redis/5.0.8/bin/redis-cli'

    auth = ''
    if args.password:
        auth += f'-a {args.password}'
        if args.user:
            auth += f' --user {args.user}'

    redisCli = 'redis-cli'
    cmd = f'echo yes | {redisCli} {auth} -h {args.host} -p {args.port} '
    cmd += f'--cluster create {args.ips} --cluster-replicas {args.replicas}'
    return cmd
