# Handling a failover

## Problem

If a redis master dies and gets restarted by kubernete (or OpenShift), Redis Cluster will have a slave/replica take over, and keep the cluster running. However once this is done one need to get a new redis node to become a slave/replica of the newly elected master node. With the default settings, kubernete will create a new pod, running in cluster mode but unknown to the rest of the cluster yet.

Once a machine has been rebooted and its old ip and node id disappear, the cluster will treat it as a failed instance. However rcc was not detecting it, and all the basic rcc sub-commands were hanging, as they were trying to connect to a dead ip. The first change to improve this was to add more verbosity when connecting.

The rcc code was updated to properly detect nodes that were in fail node when parsing the CLUSTER NODES response, and skip them. A companion change was made to display the number of replica for each master, so that we know which master needs to be replicated.

## Solution

This is how I create a temporary container to operate our cluster.

```
kubectl run rcc --rm -i --tty --limits cpu=1000m,memory=1024Mi --image ${DOCKER_REPO}/rcc:0.9.116 -- zsh
```

Listing all the nodes in the cluster:

```
~$ rcc cluster-nodes -u redis://172.25.184.208:6379 --hide_slots
d5e0a2987b9438b349450982b392d76f3781cf91 172.25.145.131:6379 master #replicas 1
1aba1453889d04119cc4b24d70ced2e3508c123f 172.25.184.208:6379 master #replicas 1
7dc543bac7b96c0bc7533c35b0c7eac0274f2e0a 172.25.241.48:6379 master #replicas 1
0d27e89197064a1f734ca39abe360dea21c52147 172.26.163.65:6379 master #replicas 1
74a640e695a0b48c1dc1b42826f69bb634c33cbd 172.26.165.191:6379 master #replicas 1
d305402271cef50e5982fd3510b7bead4ac952cc 172.26.199.115:6379 master #replicas 1
45301cb2b3ffc3f661398eb1799b0b79077b5ef6 172.26.42.159:6379 master #replicas 1
7c0179723d8747a7396cbf3d5003f88d4d1f8fcc 172.27.178.66:6379 master #replicas 1
9760a389011e4ca332f30e03a2e000b3fe00be10 172.27.240.171:6379 slave
3d0c99018c2df217f7b03e65a90063c91bef6e67 172.27.36.237:6379 master #replicas 0
98f9145d666040e9a15ba75820bd0e5afb89bb5d 172.28.206.215:6379 slave
7b4c6c0da2e9a37a0de26af2f01a8de2e3b45557 172.28.217.161:6379 slave
8b48630b4494f68acb62feb2f80e460b9ea01d08 172.30.147.239:6379 slave
e22392893cc584bbc6e9c42ca616136c5260c40c 172.30.215.25:6379 slave
8b0dccdb4d2b683e721b48610696c23e7076982e 172.30.47.107:6379 slave
7c30d9921bbc4f1d09dd6ed4c79c3744b44411a8 172.30.99.157:6379 slave
43d9eae701179954aef517f784a0aef91f14fd81 172.31.231.162:6379 slave
```

Here we see that *172.27.36.237:6379* has 0 replicas, and needs one. Now we need to identify which pod is running the new redis instance which has not joined the cluster yet. We will use the *endpoints* sub-command of rcc to figure this out. That command expects that there is a default service named redis-cluster which run your cluster. That setup will be described separately. If you use another name there is an option to specify it. This is really just a tiny wrapper on top of kubernete.

```
$ rcc endpoints --full --service redis-cluster
ip              name
--------------  ---------------------
172.25.145.131  redis-cluster-6-wmqn7
172.25.184.208  redis-cluster-6-jp2mr
172.25.241.48   redis-cluster-6-2pmb9
172.26.163.65   redis-cluster-6-5zd27
172.26.165.191  redis-cluster-6-k47kj
172.26.199.115  redis-cluster-6-blsvd
172.26.42.159   redis-cluster-6-sxb9n
172.27.178.66   redis-cluster-6-sl76p
172.27.240.171  redis-cluster-6-h6q97
172.27.36.237   redis-cluster-6-8tz6g
172.28.206.215  redis-cluster-6-p675h
172.28.217.161  redis-cluster-6-457cq
172.30.147.239  redis-cluster-6-s8g84
172.30.215.25   redis-cluster-6-7rm4m
172.30.47.107   redis-cluster-6-tmctq
172.30.99.157   redis-cluster-6-cccx2
172.31.182.46   redis-cluster-6-7s2gd  <-- the new node, not found in CLUSTER NODES
172.31.231.162  redis-cluster-6-vctz6
```

We need to eye-ball which redis instance is not part of the CLUSTER NODES response yet. In our case it is *172.31.182.46*, so we will have to remote connect to *redis-cluster-6-7s2gd* to configure the new node. This will be a 2 steps process for adding a new slave/replica.

```
oc rsh redis-cluster-6-7s2gd
# redis-cli
127.0.0.1:6379> CLUSTER NODES
4205c956cbb67e5155931c5dfa9377d903899226 :6379@16379 myself,master - 0 0 0 connected
```

The machine only know about itself at this point. We can have it join the cluster with *CLUSTER MEET*, which is the first thing to do.

```
127.0.0.1:6379> CLUSTER MEET 172.27.36.237 6379
OK
127.0.0.1:6379> CLUSTER NODES
7c0179723d8747a7396cbf3d5003f88d4d1f8fcc 172.27.178.66:6379@16379 master - xxxx
... now all the nodes are returned here
```

The second and final step is to have that machine act as a slave of the _orphaned_ master, with the *CLUSTER REPLICATE* command.

```
127.0.0.1:6379> CLUSTER REPLICATE 3d0c99018c2df217f7b03e65a90063c91bef6e67
OK
```

Now we can display our cluster again with rcc, and notice that all master have a replica.

```
~$ rcc cluster-nodes -u redis://172.25.184.208:6379 --hide_slots
d5e0a2987b9438b349450982b392d76f3781cf91 172.25.145.131:6379 master #replicas 1
1aba1453889d04119cc4b24d70ced2e3508c123f 172.25.184.208:6379 master #replicas 1
7dc543bac7b96c0bc7533c35b0c7eac0274f2e0a 172.25.241.48:6379 master #replicas 1
0d27e89197064a1f734ca39abe360dea21c52147 172.26.163.65:6379 master #replicas 1
74a640e695a0b48c1dc1b42826f69bb634c33cbd 172.26.165.191:6379 master #replicas 1
d305402271cef50e5982fd3510b7bead4ac952cc 172.26.199.115:6379 master #replicas 1
45301cb2b3ffc3f661398eb1799b0b79077b5ef6 172.26.42.159:6379 master #replicas 1
7c0179723d8747a7396cbf3d5003f88d4d1f8fcc 172.27.178.66:6379 master #replicas 1
9760a389011e4ca332f30e03a2e000b3fe00be10 172.27.240.171:6379 slave
3d0c99018c2df217f7b03e65a90063c91bef6e67 172.27.36.237:6379 master #replicas 1
98f9145d666040e9a15ba75820bd0e5afb89bb5d 172.28.206.215:6379 slave
7b4c6c0da2e9a37a0de26af2f01a8de2e3b45557 172.28.217.161:6379 slave
8b48630b4494f68acb62feb2f80e460b9ea01d08 172.30.147.239:6379 slave
e22392893cc584bbc6e9c42ca616136c5260c40c 172.30.215.25:6379 slave
8b0dccdb4d2b683e721b48610696c23e7076982e 172.30.47.107:6379 slave
7c30d9921bbc4f1d09dd6ed4c79c3744b44411a8 172.30.99.157:6379 slave
4205c956cbb67e5155931c5dfa9377d903899226 172.31.182.46:6379 slave
43d9eae701179954aef517f784a0aef91f14fd81 172.31.231.162:6379 slave
```

What is missing at this point, is a rcc command to help the cluster to forget about the old failed node.
