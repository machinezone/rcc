# Resharding

![picture](pie.jpg)

## Using rcc to reshard a redis cluster using keyspace notification

[rcc](https://github.com/machinezone/rcc/) comes with 2 important tools, one for analyzing the keys access accross nodes, built on top of [redis keyspace notifications](https://redis.io/topics/notifications) (which in turns runs on top of redis PubSub). The instrumentation is done over a period of time to sample the key access patterns. A 'weights' file is created as part of this tool. That file is saved in the current working directory by default. It is a very simple csv file that show how often a key is accessed.

```
$ head weights.csv
_pubsub::foo,50
_pubsub::bar,53
_pubsub::baz,7
_pubsub::buz,19
_pubsub::blah,940
_pubsub::blooh,20
_pubsub::xxx,552
_pubsub::yyy,571
_pubsub::zzz,92
_pubsub::foo,5035
```

The second tool is used to reshard a cluster, and migrate slots to node using the bin-packing algorithm. To feed this algorithm, weights are required.

### Generating redis cluster traffic.

We use the `cobra publish` in batch mode command to send data to [cobra](https://github.com/machinezone/rcc/), which internally send lots of XADD commands to our redis cluster.

* Cobra server started with: `cobra run -r redis://localhost:11000`
* Cobra publishers: cobra publish --batch

The redis cluster is started with: `rcc make-cluster` ; rcc has a convenience sub-command to generate config file for cluster (by default 3 masters and 3 replicas), and finally initialize the cluster.

### Keyspace access analysis before resharding

```
rcc keyspace -u redis://localhost:11000 --timeout 10
...
== Nodes ==
# each ∎ represents a count of 105. total 15515
127.0.0.1:11000 [  6789] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
127.0.0.1:11002 [  4983] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
127.0.0.1:11001 [  3743] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
```

### Resharding

```
$ rcc reshard -u redis://localhost:11000
file descriptors ulimit: 1024
resharding can be hungry, bump it with ulimit -n if needed
== f3fa13802f339abb98ccb377e8a1a4eb957be987 / 127.0.0.1:11000 ==
migrated 0 slots
Waiting for cluster view to be consistent...
.== 8c67b776ab52ad756777866dcb8425cc866c71a3 / 127.0.0.1:11001 ==
migrating 1 keys
migrating 1 keys
migrating 1 keys
migrating 1 keys
migrating 1 keys
migrating 1 keys
migrating 1 keys
migrating 1 keys
migrating 1 keys
migrating 1 keys
migrated 10 slots
Waiting for cluster view to be consistent...
............== d50246e7e3914639759add181c71a2e3c879ed2f / 127.0.0.1:11002 ==
migrating 1 keys
migrating 1 keys
migrating 1 keys
migrating 1 keys
migrating 1 keys
migrating 1 keys
migrating 1 keys
migrating 1 keys
migrating 1 keys
migrating 1 keys
migrating 1 keys
migrated 11 slots
Waiting for cluster view to be consistent...
.....total migrated slots: 11
```

It roughtly looks like we took slots away from the first node, and gave them to the other two redis instances.

### Keyspace access analysis after resharding

```
rcc keyspace -u redis://localhost:11000 --timeout 10
...
== Nodes ==
# each ∎ represents a count of 79. total 15114
127.0.0.1:11002 [  5087] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
127.0.0.1:11000 [  5040] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
127.0.0.1:11001 [  4987] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
```

## Larger Cobra cluster

* The cluster has 10 masters and 10 replicas.
* We sample about 5,000,000 received commands (this takes around a minute). This use the new --count option of the *keyspace* command.

### Using application level sharding

Cobra uses consistent hashing to compute a shard/node id. The distribution of load is not very good on production data.

```
# each ∎ represents a count of 15417. total 5003266
 172.25.241.24:6379 [940378] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
172.24.239.218:6379 [879581] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
 172.24.244.78:6379 [690303] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
 172.24.86.253:6379 [627516] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
  172.24.56.49:6379 [431098] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
172.28.138.193:6379 [343696] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
 172.29.62.140:6379 [340555] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
172.26.145.223:6379 [277856] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
172.25.184.203:6379 [258128] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
172.31.104.188:6379 [214155] ∎∎∎∎∎∎∎∎∎∎∎∎∎
```

Mean     | Median   | Stddev  | Stddev/Mean
-------- | -------- | ------- | -------------
500326.6 | 387397.0 | 265549  | 0.530

The standard deviation is very high. Some nodes do way more work than others.

### Using redis-cluster, before resharding

```
# each ∎ represents a count of 13921. total 5000873
  172.26.42.94:6379 [849140] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
  172.27.86.24:6379 [796878] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
 172.27.36.226:6379 [759250] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
  172.26.25.36:6379 [718014] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
  172.24.34.11:6379 [409835] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
172.24.244.119:6379 [391286] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
172.25.145.138:6379 [386700] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
 172.26.32.220:6379 [348391] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
 172.25.225.42:6379 [341379] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
```

Mean     | Median   | Stddev  | Stddev/Mean
-------- | -------- | ------- | -------------
555652   | 409835   | 217322  | 0.391

The standard deviation decreased from 265500 to 217322, the ratio between the standard deviation and the mean is smaller.

### After the binpacking resharding

```
# each ∎ represents a count of 10615. total 5004030
 172.27.36.226:6379 [647515] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
  172.26.25.36:6379 [581910] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
172.24.244.119:6379 [566576] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
  172.27.86.24:6379 [562850] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
  172.24.34.11:6379 [560954] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
 172.25.225.42:6379 [551802] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
  172.26.42.94:6379 [536849] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
172.25.145.138:6379 [499993] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
 172.26.32.220:6379 [495581] ∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎∎
```

Mean     | Median   | Stddev  | Stddev/Mean
-------- | -------- | ------- | -------------
556003   | 560954   | 45278   | 0.081

Visually we can see that the distribution is very well balanced. The Stddev/Mean ratio decreased by a factor of 6.5 (0.530 / 0.81).
