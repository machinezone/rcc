# General

[![PyPI version](https://badge.fury.io/py/rcc.svg)](https://badge.fury.io/py/rcc)
![Build status](https://github.com/machinezone/rcc/workflows/unittest/badge.svg)
[![PyPI Python Versions](https://img.shields.io/pypi/pyversions/rcc.svg)](https://img.shields.io/pypi/pyversions/rcc)
[![License](https://img.shields.io/pypi/l/rcc.svg)](https://img.shields.io/pypi/l/rcc)
[![Wheel](https://img.shields.io/pypi/wheel/rcc.svg)](https://img.shields.io/pypi/wheel/rcc)

A Redis Cluster Client

## Rationale

The main asyncio redis library does not support redis cluster at this point. There is another library named aredis which has cluster support, but which has some small bugs for which pull requests existed, that were not merged until recently. Getting a redis client to work is not terribly hard, thanks to the design of redis, so I started this project and got it to work in a limited amount of time.

## Tools

Several tools come with this package, as subcommands of the main cli. The 2 significant ones are:

* *keyspace* / will turn on redis keyspace notifications and tell you what your _hot_ keys are.
* *reshard* / will help reshard your cluster in an optimal way based on your usage. This will consume the output of the analyze-keyspace command. This is documented in great details [here](https://machinezone.github.io/rcc/binpacking/) and [there](https://machinezone.github.io/rcc/resharding/).

Interested? Go read the [docs](https://machinezone.github.io/rcc/)


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
