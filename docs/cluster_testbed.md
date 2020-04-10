# Cluster test bed

## Problem

It takes quite a few command to start a new cluster locally for testing. The redis source contains a simple shell script to help, but we go a little further.

## Solution

```
$ rcc make-cluster --help
Usage: rcc make-cluster [OPTIONS]

  Create, configure, initialize and run a redis cluster and a redis cluster
  proxy

Options:
  --size INTEGER
  --start_port INTEGER
  -a, --password TEXT
  --help                Show this message and exit.
```

`rcc make-cluster` will create a temp folder, a set of redis-server config files and initialize the cluster using the `redis-cli --cluster init` command. Then it will run all the servers thank to [honcho]([https://github.com/nickstenning/honcho), which is a simple python init.d like tool based on [Foreman](https://github.com/ddollar/foreman). Foreman is the original Ruby init.d like tool that reads a very simple text file called a Procfile, containing a list of label:commands separated by new lines.

```
$ cd /var/folders/qz/cb1zd5756hnd2tykv7z5sn_j8408d8/T/tmp03u8opux
$ cat Procfile
server0: redis-server server0.conf --protected-mode no --cluster-enabled yes --port 11000
server1: redis-server server1.conf --protected-mode no --cluster-enabled yes --port 11001
server2: redis-server server2.conf --protected-mode no --cluster-enabled yes --port 11002
server3: redis-server server3.conf --protected-mode no --cluster-enabled yes --port 11003
server4: redis-server server4.conf --protected-mode no --cluster-enabled yes --port 11004
server5: redis-server server5.conf --protected-mode no --cluster-enabled yes --port 11005
proxy: while test ! -f $ROOT/redis_cluster_ready ; do sleep 3 ; echo "waiting for cluster to be up to start proxy" ; done ; redis-cluster-proxy --port 11006 127.0.0.1:11000 127.0.0.1:11001 127.0.0.1:11002 127.0.0.1:11003 127.0.0.1:11004 127.0.0.1:11005
```

A Procfile is similzr to a Makefile. If you enter a folder with a Procfile and type `honcho` or `make`, all the referenced commands will be executed.

Each redis server gets a minimal config file generated, and is started in cluster mode. The default port assigned to the first instance is 11000, and that can be configured. The number of cluster in the node can also be configured.

```
$ cat server0.conf
cluster-config-file nodes-0.conf
dbfilename dump0.rdb
```

Once the command has terminated (takes about 10 seconds on my mac), you can run redis-cli to test it.

```
$ redis-cli -c -p 11000
127.0.0.1:11000> set foo bar
-> Redirected to slot [12182] located at 127.0.0.1:11002
OK
```

### redis-cluster-proxy

[Redis cluster proxy](https://github.com/RedisLabs/redis-cluster-proxy) is a proxy that let a redis client that is not cluster aware talk to a redis cluster regardless. The proxy handle all the cluster semantic transparently. This is extremely useful if you are trying to port an application which does not have a complete redis library. aioredis is an example of a widely used python library that does not support redis-cluster.

The last line in the Procfile starts a redis cluster proxy instance, and configures it to point to our redis cluster. By default it runs on port *11006*.

```
proxy: while test ! -f $ROOT/redis_cluster_ready ; do sleep 3 ; echo "waiting for cluster to be up to start proxy" ; done ; redis-cluster-proxy --port 11006 127.0.0.1:11000 127.0.0.1:11001 127.0.0.1:11002 127.0.0.1:11003 127.0.0.1:11004 127.0.0.1:11005
```

The odd line with the while expression is there to start the proxy only once the cluster has been setup. A simplified version of it is written below.

```
$ while test ! -f /tmp/bar ; do sleep 1 ; echo waiting ; done ; echo READY
waiting
waiting
(touch /tmp/bar in a different terminal)
READY
```

You can read/write to the cluster through the proxy using redis-cli at port 11006.

```
$ redis-cli -p 11006
127.0.0.1:11006> set foo bar
OK
```

The project is super active and reaching v1 soon, it is still in beta but we use it and it works great.

### Full startup log

```
(venv) rcc$ rcc make-cluster
1/6 Creating server config for range [11000, 11001, 11002, 11003, 11004, 11005]
2/6 Check that ports are opened
......
3/6 Configuring and running
4/6 Wait for the cluster nodes to be running
Checking redis://localhost:11000 .2020-04-09 19:12:00 WARNING Multiple exceptions: [Errno 61] Connect call failed ('::1', 11000, 0, 0), [Errno 61] Connect call failed ('127.0.0.1', 11000)
.2020-04-09 19:12:00 WARNING Multiple exceptions: [Errno 61] Connect call failed ('::1', 11000, 0, 0), [Errno 61] Connect call failed ('127.0.0.1', 11000)
.2020-04-09 19:12:00 WARNING Multiple exceptions: [Errno 61] Connect call failed ('::1', 11000, 0, 0), [Errno 61] Connect call failed ('127.0.0.1', 11000)
.2020-04-09 19:12:00 WARNING Multiple exceptions: [Errno 61] Connect call failed ('::1', 11000, 0, 0), [Errno 61] Connect call failed ('127.0.0.1', 11000)
.2020-04-09 19:12:00 WARNING Multiple exceptions: [Errno 61] Connect call failed ('::1', 11000, 0, 0), [Errno 61] Connect call failed ('127.0.0.1', 11000)
.2020-04-09 19:12:00 WARNING Multiple exceptions: [Errno 61] Connect call failed ('::1', 11000, 0, 0), [Errno 61] Connect call failed ('127.0.0.1', 11000)
.2020-04-09 19:12:01 WARNING Multiple exceptions: [Errno 61] Connect call failed ('::1', 11000, 0, 0), [Errno 61] Connect call failed ('127.0.0.1', 11000)
/Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/subprocess.py:844: RuntimeWarning: line buffering (buffering=1) isn't supported in binary mode, the default buffer size will be used
  self.stdout = io.open(c2pread, 'rb', bufsize)
19:12:01 system    | server2.1 started (pid=72704)
19:12:01 server2.1 | 72704:C 09 Apr 2020 19:12:01.130 # oO0OoO0OoO0Oo Redis is starting oO0OoO0OoO0Oo
19:12:01 server2.1 | 72704:C 09 Apr 2020 19:12:01.130 # Redis version=5.0.8, bits=64, commit=00000000, modified=0, pid=72704, just started
19:12:01 server2.1 | 72704:C 09 Apr 2020 19:12:01.130 # Configuration loaded
19:12:01 server2.1 | 72704:M 09 Apr 2020 19:12:01.131 * Increased maximum number of open files to 10032 (it was originally set to 1024).
19:12:01 server2.1 | 72704:M 09 Apr 2020 19:12:01.132 * No cluster configuration found, I'm 23b57926eec91d51dd946f74bd3200ef5ca1c5e0
19:12:01 server2.1 | 72704:M 09 Apr 2020 19:12:01.132 * Running mode=cluster, port=11002.
19:12:01 server2.1 | 72704:M 09 Apr 2020 19:12:01.132 # Server initialized
19:12:01 server2.1 | 72704:M 09 Apr 2020 19:12:01.132 * Ready to accept connections
.2020-04-09 19:12:01 WARNING Multiple exceptions: [Errno 61] Connect call failed ('::1', 11000, 0, 0), [Errno 61] Connect call failed ('127.0.0.1', 11000)
/Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/subprocess.py:844: RuntimeWarning: line buffering (buffering=1) isn't supported in binary mode, the default buffer size will be used
  self.stdout = io.open(c2pread, 'rb', bufsize)
/Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/subprocess.py:844: RuntimeWarning: line buffering (buffering=1) isn't supported in binary mode, the default buffer size will be used
  self.stdout = io.open(c2pread, 'rb', bufsize)
/Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/subprocess.py:844: RuntimeWarning: line buffering (buffering=1) isn't supported in binary mode, the default buffer size will be used
  self.stdout = io.open(c2pread, 'rb', bufsize)
/Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/subprocess.py:844: RuntimeWarning: line buffering (buffering=1) isn't supported in binary mode, the default buffer size will be used
  self.stdout = io.open(c2pread, 'rb', bufsize)
/Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/subprocess.py:844: RuntimeWarning: line buffering (buffering=1) isn't supported in binary mode, the default buffer size will be used
  self.stdout = io.open(c2pread, 'rb', bufsize)
/Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/subprocess.py:844: RuntimeWarning: line buffering (buffering=1) isn't supported in binary mode, the default buffer size will be used
  self.stdout = io.open(c2pread, 'rb', bufsize)
19:12:01 system    | proxy.1 started (pid=72705)
19:12:01 system    | server0.1 started (pid=72709)
19:12:01 system    | server5.1 started (pid=72707)
19:12:01 system    | server1.1 started (pid=72708)
19:12:01 system    | server3.1 started (pid=72706)
19:12:01 system    | server4.1 started (pid=72710)
19:12:01 server3.1 | 72706:C 09 Apr 2020 19:12:01.345 # oO0OoO0OoO0Oo Redis is starting oO0OoO0OoO0Oo
19:12:01 server3.1 | 72706:C 09 Apr 2020 19:12:01.345 # Redis version=5.0.8, bits=64, commit=00000000, modified=0, pid=72706, just started
19:12:01 server3.1 | 72706:C 09 Apr 2020 19:12:01.345 # Configuration loaded
19:12:01 server3.1 | 72706:M 09 Apr 2020 19:12:01.347 * Increased maximum number of open files to 10032 (it was originally set to 1024).
19:12:01 server5.1 | 72707:C 09 Apr 2020 19:12:01.347 # oO0OoO0OoO0Oo Redis is starting oO0OoO0OoO0Oo
19:12:01 server5.1 | 72707:C 09 Apr 2020 19:12:01.347 # Redis version=5.0.8, bits=64, commit=00000000, modified=0, pid=72707, just started
19:12:01 server5.1 | 72707:C 09 Apr 2020 19:12:01.347 # Configuration loaded
19:12:01 server0.1 | 72709:C 09 Apr 2020 19:12:01.347 # oO0OoO0OoO0Oo Redis is starting oO0OoO0OoO0Oo
19:12:01 server0.1 | 72709:C 09 Apr 2020 19:12:01.347 # Redis version=5.0.8, bits=64, commit=00000000, modified=0, pid=72709, just started
19:12:01 server0.1 | 72709:C 09 Apr 2020 19:12:01.347 # Configuration loaded
19:12:01 server3.1 | 72706:M 09 Apr 2020 19:12:01.348 * No cluster configuration found, I'm faf021cd1c2e7eeea1ed121dead0402b889bf41c
19:12:01 server3.1 | 72706:M 09 Apr 2020 19:12:01.349 * Running mode=cluster, port=11003.
19:12:01 server3.1 | 72706:M 09 Apr 2020 19:12:01.349 # Server initialized
19:12:01 server5.1 | 72707:M 09 Apr 2020 19:12:01.349 * Increased maximum number of open files to 10032 (it was originally set to 1024).
19:12:01 server5.1 | 72707:M 09 Apr 2020 19:12:01.350 * No cluster configuration found, I'm cd880f1392726db05f268ed9d5990ac9ff4d5cd2
19:12:01 server1.1 | 72708:C 09 Apr 2020 19:12:01.348 # oO0OoO0OoO0Oo Redis is starting oO0OoO0OoO0Oo
19:12:01 server1.1 | 72708:C 09 Apr 2020 19:12:01.348 # Redis version=5.0.8, bits=64, commit=00000000, modified=0, pid=72708, just started
19:12:01 server1.1 | 72708:C 09 Apr 2020 19:12:01.348 # Configuration loaded
19:12:01 server1.1 | 72708:M 09 Apr 2020 19:12:01.350 * Increased maximum number of open files to 10032 (it was originally set to 1024).
19:12:01 server5.1 | 72707:M 09 Apr 2020 19:12:01.351 * Running mode=cluster, port=11005.
19:12:01 server5.1 | 72707:M 09 Apr 2020 19:12:01.351 # Server initialized
19:12:01 server3.1 | 72706:M 09 Apr 2020 19:12:01.349 * Ready to accept connections
19:12:01 server0.1 | 72709:M 09 Apr 2020 19:12:01.349 * Increased maximum number of open files to 10032 (it was originally set to 1024).
19:12:01 server1.1 | 72708:M 09 Apr 2020 19:12:01.351 * No cluster configuration found, I'm 6940667737386545f0fd396b4d7d0b100f4fdfaf
19:12:01 server5.1 | 72707:M 09 Apr 2020 19:12:01.352 * Ready to accept connections
19:12:01 server0.1 | 72709:M 09 Apr 2020 19:12:01.351 * No cluster configuration found, I'm c66e96d1dce3d857f8a007c4727fe807c537a143
19:12:01 server1.1 | 72708:M 09 Apr 2020 19:12:01.353 * Running mode=cluster, port=11001.
19:12:01 server0.1 | 72709:M 09 Apr 2020 19:12:01.352 * Running mode=cluster, port=11000.
19:12:01 server1.1 | 72708:M 09 Apr 2020 19:12:01.353 # Server initialized
19:12:01 server0.1 | 72709:M 09 Apr 2020 19:12:01.352 # Server initialized
19:12:01 server0.1 | 72709:M 09 Apr 2020 19:12:01.352 * Ready to accept connections
19:12:01 server1.1 | 72708:M 09 Apr 2020 19:12:01.353 * Ready to accept connections
19:12:01 server4.1 | 72710:C 09 Apr 2020 19:12:01.348 # oO0OoO0OoO0Oo Redis is starting oO0OoO0OoO0Oo
19:12:01 server4.1 | 72710:C 09 Apr 2020 19:12:01.348 # Redis version=5.0.8, bits=64, commit=00000000, modified=0, pid=72710, just started
19:12:01 server4.1 | 72710:C 09 Apr 2020 19:12:01.348 # Configuration loaded
19:12:01 server4.1 | 72710:M 09 Apr 2020 19:12:01.350 * Increased maximum number of open files to 10032 (it was originally set to 1024).
19:12:01 server4.1 | 72710:M 09 Apr 2020 19:12:01.352 * No cluster configuration found, I'm 00d6302ad615c460222e147b31c97a361412261c
19:12:01 server4.1 | 72710:M 09 Apr 2020 19:12:01.353 * Running mode=cluster, port=11004.
19:12:01 server4.1 | 72710:M 09 Apr 2020 19:12:01.353 # Server initialized
19:12:01 server4.1 | 72710:M 09 Apr 2020 19:12:01.353 * Ready to accept connections
.
Checking redis://localhost:11001 .
Checking redis://localhost:11002 .
5/6 Initialize the cluster
>>> Performing hash slots allocation on 6 nodes...
Master[0] -> Slots 0 - 5460
Master[1] -> Slots 5461 - 10922
Master[2] -> Slots 10923 - 16383
Adding replica 127.0.0.1:11004 to 127.0.0.1:11000
Adding replica 127.0.0.1:11005 to 127.0.0.1:11001
Adding replica 127.0.0.1:11003 to 127.0.0.1:11002
>>> Trying to optimize slaves allocation for anti-affinity
[WARNING] Some slaves are in the same host as their master
M: c66e96d1dce3d857f8a007c4727fe807c537a143 127.0.0.1:11000
   slots:[0-5460] (5461 slots) master
M: 6940667737386545f0fd396b4d7d0b100f4fdfaf 127.0.0.1:11001
   slots:[5461-10922] (5462 slots) master
M: 23b57926eec91d51dd946f74bd3200ef5ca1c5e0 127.0.0.1:11002
   slots:[10923-16383] (5461 slots) master
S: faf021cd1c2e7eeea1ed121dead0402b889bf41c 127.0.0.1:11003
   replicates 23b57926eec91d51dd946f74bd3200ef5ca1c5e0
S: 00d6302ad615c460222e147b31c97a361412261c 127.0.0.1:11004
   replicates c66e96d1dce3d857f8a007c4727fe807c537a143
S: cd880f1392726db05f268ed9d5990ac9ff4d5cd2 127.0.0.1:11005
   replicates 6940667737386545f0fd396b4d7d0b100f4fdfaf
Can I set the above configuration? (type 'yes' to accept): >>> Nodes configuration updated
>>> Assign a different config epoch to each node
19:12:01 server0.1 | 72709:M 09 Apr 2020 19:12:01.446 # configEpoch set to 1 via CLUSTER SET-CONFIG-EPOCH
19:12:01 server1.1 | 72708:M 09 Apr 2020 19:12:01.447 # configEpoch set to 2 via CLUSTER SET-CONFIG-EPOCH
19:12:01 server2.1 | 72704:M 09 Apr 2020 19:12:01.447 # configEpoch set to 3 via CLUSTER SET-CONFIG-EPOCH
19:12:01 server3.1 | 72706:M 09 Apr 2020 19:12:01.447 # configEpoch set to 4 via CLUSTER SET-CONFIG-EPOCH
19:12:01 server4.1 | 72710:M 09 Apr 2020 19:12:01.447 # configEpoch set to 5 via CLUSTER SET-CONFIG-EPOCH
>>> Sending CLUSTER MEET messages to join the cluster
19:12:01 server5.1 | 72707:M 09 Apr 2020 19:12:01.448 # configEpoch set to 6 via CLUSTER SET-CONFIG-EPOCH
19:12:01 server0.1 | 72709:M 09 Apr 2020 19:12:01.451 # IP address for this node updated to 127.0.0.1
19:12:01 server3.1 | 72706:M 09 Apr 2020 19:12:01.453 # IP address for this node updated to 127.0.0.1
19:12:01 server5.1 | 72707:M 09 Apr 2020 19:12:01.554 # IP address for this node updated to 127.0.0.1
19:12:01 server2.1 | 72704:M 09 Apr 2020 19:12:01.554 # IP address for this node updated to 127.0.0.1
19:12:01 server1.1 | 72708:M 09 Apr 2020 19:12:01.554 # IP address for this node updated to 127.0.0.1
19:12:01 server4.1 | 72710:M 09 Apr 2020 19:12:01.554 # IP address for this node updated to 127.0.0.1
Waiting for the cluster to join
.19:12:03 server1.1 | 72708:M 09 Apr 2020 19:12:03.391 # Cluster state changed: ok
19:12:03 server0.1 | 72709:M 09 Apr 2020 19:12:03.391 # Cluster state changed: ok
.19:12:04 server5.1 | 72707:M 09 Apr 2020 19:12:04.310 # Cluster state changed: ok
19:12:04 proxy.1   | waiting for cluster to be up to start proxy
.19:12:05 server4.1 | 72710:M 09 Apr 2020 19:12:05.329 # Cluster state changed: ok
19:12:05 server2.1 | 72704:M 09 Apr 2020 19:12:05.337 # Cluster state changed: ok
..19:12:07 proxy.1   | waiting for cluster to be up to start proxy
..19:12:09 server3.1 | 72706:M 09 Apr 2020 19:12:09.208 # Cluster state changed: ok

19:12:09 server3.1 | 72706:S 09 Apr 2020 19:12:09.486 * Before turning into a replica, using my master parameters to synthesize a cached master: I may be able to synchronize with the new master with just a partial transfer.
19:12:09 server4.1 | 72710:S 09 Apr 2020 19:12:09.487 * Before turning into a replica, using my master parameters to synthesize a cached master: I may be able to synchronize with the new master with just a partial transfer.
19:12:09 server5.1 | 72707:S 09 Apr 2020 19:12:09.487 * Before turning into a replica, using my master parameters to synthesize a cached master: I may be able to synchronize with the new master with just a partial transfer.
>>> Performing Cluster Check (using node 127.0.0.1:11000)
M: c66e96d1dce3d857f8a007c4727fe807c537a143 127.0.0.1:11000
   slots:[0-5460] (5461 slots) master
   1 additional replica(s)
S: cd880f1392726db05f268ed9d5990ac9ff4d5cd2 127.0.0.1:11005
   slots: (0 slots) slave
   replicates 6940667737386545f0fd396b4d7d0b100f4fdfaf
M: 23b57926eec91d51dd946f74bd3200ef5ca1c5e0 127.0.0.1:11002
   slots:[10923-16383] (5461 slots) master
   1 additional replica(s)
S: 00d6302ad615c460222e147b31c97a361412261c 127.0.0.1:11004
   slots: (0 slots) slave
   replicates c66e96d1dce3d857f8a007c4727fe807c537a143
M: 6940667737386545f0fd396b4d7d0b100f4fdfaf 127.0.0.1:11001
   slots:[5461-10922] (5462 slots) master
   1 additional replica(s)
S: faf021cd1c2e7eeea1ed121dead0402b889bf41c 127.0.0.1:11003
   slots: (0 slots) slave
   replicates 23b57926eec91d51dd946f74bd3200ef5ca1c5e0
[OK] All nodes agree about slots configuration.
>>> Check for open slots...
>>> Check slots coverage...
[OK] All 16384 slots covered.
6/6 Wait for all cluster nodes to be consistent
19:12:09 server3.1 | 72706:S 09 Apr 2020 19:12:09.511 * Connecting to MASTER 127.0.0.1:11002
19:12:09 server3.1 | 72706:S 09 Apr 2020 19:12:09.511 * MASTER <-> REPLICA sync started
19:12:09 server3.1 | 72706:S 09 Apr 2020 19:12:09.511 * Non blocking connect for SYNC fired the event.
19:12:09 server3.1 | 72706:S 09 Apr 2020 19:12:09.511 * Master replied to PING, replication can continue...
19:12:09 server3.1 | 72706:S 09 Apr 2020 19:12:09.512 * Trying a partial resynchronization (request 4df041657f7f8594ec0a302c0c41118dc08777f0:1).
19:12:09 server2.1 | 72704:M 09 Apr 2020 19:12:09.512 * Replica 127.0.0.1:11003 asks for synchronization
19:12:09 server2.1 | 72704:M 09 Apr 2020 19:12:09.512 * Partial resynchronization not accepted: Replication ID mismatch (Replica asked for '4df041657f7f8594ec0a302c0c41118dc08777f0', my replication IDs are 'b3a87de48fc894761c5380d18f2c81437d35235f' and '0000000000000000000000000000000000000000')
19:12:09 server2.1 | 72704:M 09 Apr 2020 19:12:09.512 * Starting BGSAVE for SYNC with target: disk
19:12:09 server2.1 | 72704:M 09 Apr 2020 19:12:09.512 * Background saving started by pid 72722
19:12:09 server3.1 | 72706:S 09 Apr 2020 19:12:09.512 * Full resync from master: b78b16d46be8d42cc78c1c4b3e7d4ec445c30d03:0
19:12:09 server3.1 | 72706:S 09 Apr 2020 19:12:09.512 * Discarding previously cached master state.
19:12:09 server2.1 | 72722:C 09 Apr 2020 19:12:09.513 * DB saved on disk
19:12:09 server4.1 | 72710:S 09 Apr 2020 19:12:09.523 * Connecting to MASTER 127.0.0.1:11000
19:12:09 server5.1 | 72707:S 09 Apr 2020 19:12:09.523 * Connecting to MASTER 127.0.0.1:11001
19:12:09 server4.1 | 72710:S 09 Apr 2020 19:12:09.523 * MASTER <-> REPLICA sync started
19:12:09 server5.1 | 72707:S 09 Apr 2020 19:12:09.523 * MASTER <-> REPLICA sync started
19:12:09 server4.1 | 72710:S 09 Apr 2020 19:12:09.523 * Non blocking connect for SYNC fired the event.
19:12:09 server5.1 | 72707:S 09 Apr 2020 19:12:09.523 * Non blocking connect for SYNC fired the event.
19:12:09 server4.1 | 72710:S 09 Apr 2020 19:12:09.523 * Master replied to PING, replication can continue...
19:12:09 server5.1 | 72707:S 09 Apr 2020 19:12:09.523 * Master replied to PING, replication can continue...
19:12:09 server4.1 | 72710:S 09 Apr 2020 19:12:09.523 * Trying a partial resynchronization (request a1362164e84c8a176cee42ed71880e416362a279:1).
19:12:09 server0.1 | 72709:M 09 Apr 2020 19:12:09.523 * Replica 127.0.0.1:11004 asks for synchronization
19:12:09 server1.1 | 72708:M 09 Apr 2020 19:12:09.523 * Replica 127.0.0.1:11005 asks for synchronization
19:12:09 server5.1 | 72707:S 09 Apr 2020 19:12:09.523 * Trying a partial resynchronization (request 5a35ba14e6e6fe123985315c665ffbeacea69c2d:1).
19:12:09 server0.1 | 72709:M 09 Apr 2020 19:12:09.523 * Partial resynchronization not accepted: Replication ID mismatch (Replica asked for 'a1362164e84c8a176cee42ed71880e416362a279', my replication IDs are 'b826b09ebf81696089a7fed8debe307c07d03755' and '0000000000000000000000000000000000000000')
19:12:09 server1.1 | 72708:M 09 Apr 2020 19:12:09.523 * Partial resynchronization not accepted: Replication ID mismatch (Replica asked for '5a35ba14e6e6fe123985315c665ffbeacea69c2d', my replication IDs are '5f1b4ac6e693247d2ac267ae9af32d0a53902532' and '0000000000000000000000000000000000000000')
19:12:09 server0.1 | 72709:M 09 Apr 2020 19:12:09.523 * Starting BGSAVE for SYNC with target: disk
19:12:09 server1.1 | 72708:M 09 Apr 2020 19:12:09.523 * Starting BGSAVE for SYNC with target: disk
19:12:09 server0.1 | 72709:M 09 Apr 2020 19:12:09.524 * Background saving started by pid 72723
19:12:09 server5.1 | 72707:S 09 Apr 2020 19:12:09.524 * Full resync from master: 50025f2dcd1f778f36018a32ad70817d5143a5c6:0
19:12:09 server1.1 | 72708:M 09 Apr 2020 19:12:09.524 * Background saving started by pid 72724
19:12:09 server4.1 | 72710:S 09 Apr 2020 19:12:09.524 * Full resync from master: 07446ccb851df269a57777a77388c4a724e4e48e:0
19:12:09 server5.1 | 72707:S 09 Apr 2020 19:12:09.524 * Discarding previously cached master state.
19:12:09 server4.1 | 72710:S 09 Apr 2020 19:12:09.524 * Discarding previously cached master state.
19:12:09 server1.1 | 72724:C 09 Apr 2020 19:12:09.525 * DB saved on disk
19:12:09 server0.1 | 72723:C 09 Apr 2020 19:12:09.525 * DB saved on disk
Waiting for cluster to be consistent...
19:12:09 server2.1 | 72704:M 09 Apr 2020 19:12:09.615 * Background saving terminated with success
19:12:09 server2.1 | 72704:M 09 Apr 2020 19:12:09.616 * Synchronization with replica 127.0.0.1:11003 succeeded
19:12:09 server3.1 | 72706:S 09 Apr 2020 19:12:09.616 * MASTER <-> REPLICA sync: receiving 175 bytes from master
19:12:09 server3.1 | 72706:S 09 Apr 2020 19:12:09.616 * MASTER <-> REPLICA sync: Flushing old data
19:12:09 server3.1 | 72706:S 09 Apr 2020 19:12:09.616 * MASTER <-> REPLICA sync: Loading DB in memory
19:12:09 server3.1 | 72706:S 09 Apr 2020 19:12:09.616 * MASTER <-> REPLICA sync: Finished with success
19:12:09 server0.1 | 72709:M 09 Apr 2020 19:12:09.620 * Background saving terminated with success
19:12:09 server4.1 | 72710:S 09 Apr 2020 19:12:09.620 * MASTER <-> REPLICA sync: receiving 175 bytes from master
19:12:09 server0.1 | 72709:M 09 Apr 2020 19:12:09.620 * Synchronization with replica 127.0.0.1:11004 succeeded
19:12:09 server4.1 | 72710:S 09 Apr 2020 19:12:09.620 * MASTER <-> REPLICA sync: Flushing old data
19:12:09 server4.1 | 72710:S 09 Apr 2020 19:12:09.620 * MASTER <-> REPLICA sync: Loading DB in memory
19:12:09 server4.1 | 72710:S 09 Apr 2020 19:12:09.621 * MASTER <-> REPLICA sync: Finished with success
19:12:09 server1.1 | 72708:M 09 Apr 2020 19:12:09.623 * Background saving terminated with success
19:12:09 server1.1 | 72708:M 09 Apr 2020 19:12:09.623 * Synchronization with replica 127.0.0.1:11005 succeeded
19:12:09 server5.1 | 72707:S 09 Apr 2020 19:12:09.623 * MASTER <-> REPLICA sync: receiving 175 bytes from master
19:12:09 server5.1 | 72707:S 09 Apr 2020 19:12:09.623 * MASTER <-> REPLICA sync: Flushing old data
19:12:09 server5.1 | 72707:S 09 Apr 2020 19:12:09.623 * MASTER <-> REPLICA sync: Loading DB in memory
19:12:09 server5.1 | 72707:S 09 Apr 2020 19:12:09.624 * MASTER <-> REPLICA sync: Finished with success
19:12:10 proxy.1   | waiting for cluster to be up to start proxy
Waiting for cluster to be consistent...
Waiting for cluster to be consistent...
Waiting for cluster to be consistent...
19:12:13 proxy.1   | waiting for cluster to be up to start proxy
Waiting for cluster to be consistent...
Cluster ready !
Config files created in folder /var/folders/qz/cb1zd5756hnd2tykv7z5sn_j8408d8/T/tmpdlq0lavp
19:12:16 proxy.1   | waiting for cluster to be up to start proxy
19:12:16 proxy.1   | [2020-04-09 19:12:16.381/M] Redis Cluster Proxy v999.999.999 (unstable)
19:12:16 proxy.1   | [2020-04-09 19:12:16.381/M] Commit: (eb092d0b/0)
19:12:16 proxy.1   | [2020-04-09 19:12:16.381/M] Git Branch: unstable
19:12:16 proxy.1   | [2020-04-09 19:12:16.381/M] PID: 72735
19:12:16 proxy.1   | [2020-04-09 19:12:16.381/M] OS: Darwin 19.3.0 x86_64
19:12:16 proxy.1   | [2020-04-09 19:12:16.381/M] Bits: 64
19:12:16 proxy.1   | [2020-04-09 19:12:16.381/M] Log level: info
19:12:16 proxy.1   | [2020-04-09 19:12:16.381/M] Connections pool size: 10 (respawn 2 every 50ms if below 10)
19:12:16 proxy.1   | [2020-04-09 19:12:16.382/M] Listening on *:11006
19:12:16 proxy.1   | [2020-04-09 19:12:16.382/M] Starting 8 threads...
19:12:16 proxy.1   | [2020-04-09 19:12:16.382/M] Fetching cluster configuration...
19:12:16 proxy.1   | [2020-04-09 19:12:16.386/M] Cluster Address: 127.0.0.1:11000
19:12:16 proxy.1   | [2020-04-09 19:12:16.386/M] Cluster has 3 masters and 3 replica(s)
19:12:16 proxy.1   | [2020-04-09 19:12:16.386/M] Increased maximum number of open files to 10518 (it was originally set to 1024).
19:12:16 proxy.1   | [2020-04-09 19:12:16.427/M] All thread(s) started!
```
