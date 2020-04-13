# General

[![PyPI version](https://badge.fury.io/py/rcc.svg)](https://badge.fury.io/py/rcc)
![Build status](https://github.com/machinezone/rcc/workflows/unittest/badge.svg)
[![PyPI Python Versions](https://img.shields.io/pypi/pyversions/rcc.svg)](https://img.shields.io/pypi/pyversions/rcc)
[![License](https://img.shields.io/pypi/l/rcc.svg)](https://img.shields.io/pypi/l/rcc)
[![Wheel](https://img.shields.io/pypi/wheel/rcc.svg)](https://img.shields.io/pypi/wheel/rcc)

A Redis Cluster Client with a cli line tools in the spirit of redis-trib.

## Installation

### UNIX one liner

```
/bin/sh -c `curl -fsSL https://raw.githubusercontent.com/machinezone/rcc/master/tools/install.sh`
```

You can see what the install script is doing first [here](https://github.com/machinezone/rcc/blob/master/tools/install.sh).

### For folks familiar with Python

```
# Create a virtualenv first, then
pip install rcc
```

## Rationale

rcc started as an attempt at writing an asyncio redis-cluster aware python client. It is now mostly used a redis cluster tool, built on a minimal but functional redis client library.

The main asyncio redis library, aioredis does not support redis cluster at this point. There is another library named aredis which has cluster support, but which has some small bugs for which pull requests existed, that were not merged until recently. Getting a redis client to work is not terribly hard, thanks to the design of redis, so I started this project and got it to work in a limited amount of time.

## Tools

Several tools come with this package, as subcommands of the main cli named `rcc`. Some documentation (wip) is available [here](https://machinezone.github.io/rcc/).

```
$ rcc
Usage: rcc [OPTIONS] COMMAND [ARGS]...

  _______   ____  ____
  \_  __ \_/ ___\/ ___\
   |  | \/\  \__\  \___
   |__|    \___  >___  >
               \/    \/

  rcc / Redis Cluster Client / cli

Options:
  --version      Show the version and exit.
  -v, --verbose
  --help         Show this message and exit.

Commands:
  cli            cli tool similar to redis-cli
  cluster-check  Make sure all nodes have the same view of the cluster
  cluster-info   Monitor redis metrics from the INFO command
  cluster-init   Print a cluster init command for redis url defined in a...
  cluster-nodes  Monitor redis metrics
  endpoints      Print endpoints associated with a redis cluster service
  keyspace       Analyze the keyspace
  make-cluster   Create, configure, initialize and run a redis cluster
  migrate        Migrate one slot from a node to another one
  publish        Publish (with XADD) to a channel
  reshard        Reshard a cluster using the binpacking technique
  sub            Subscribe (with PUBSUB) to a channel
  subscribe      Subscribe (with XREAD) to a channel
```

The 2 remarquable tools are:

### Keyspace analysis tool

The *keyspace* command will turn on redis keyspace notifications and tell you what your _hot_ keys are. It will output a csv file containing a list of keys accessed by commands, with a weight representing their access frequency. There are 2 ways to

The tool will display informations visually as well, such as the distribution of keys/commands amongst nodes. It is very helpful to know if your cluster provides good balancing, or whether you should reshard it.

```
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

### Cluster Resharing tool

The *reshard* command will reshard your cluster in an optimal way based on your usage. It consumes the output of the *keyspace* command. It is documented in great details [here](https://machinezone.github.io/rcc/binpacking/) and [there](https://machinezone.github.io/rcc/resharding/).

Here is how the previous cluster usage distribution looks after resharding for us.

*Disclaimer* - the default sharding strategy works very well, and if you have many machines and keys you might be just fine. But if you do not have that many keys, and some of them are accessed with a much higher frequency than other this tool might help you a lot. This is the case for us in our usage of [cobra](https://github.com/machinezone/cobra) at Machine Zone.

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

## Installation

If you are familiar with python or pip this should be easy.

```
cd $HOME # or anywhere you want
python3 -mvenv venv
source venv/bin/activate
pip install rcc
rcc
```

## Random

RCC is also the name of the [Redwood Childrens Center](http://redwoodchildrenscenter.com/). If you are looking for a great preschool in Redwood City, California, I highly recommend it.
