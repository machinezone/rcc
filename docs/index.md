# General

[![PyPI version](https://badge.fury.io/py/rcc.svg)](https://badge.fury.io/py/rcc)
![Build status](https://github.com/machinezone/rcc/workflows/unittest/badge.svg)
[![PyPI Python Versions](https://img.shields.io/pypi/pyversions/rcc.svg)](https://img.shields.io/pypi/pyversions/rcc)
[![License](https://img.shields.io/pypi/l/rcc.svg)](https://img.shields.io/pypi/l/rcc)
[![Wheel](https://img.shields.io/pypi/wheel/rcc.svg)](https://img.shields.io/pypi/wheel/rcc)

A Redis Cluster Client
A Redis Cluster Client with a cli line tools in the spirit of redis-trib.

## Installation

### UNIX one liner

```
/bin/sh -c "`curl -fsSL https://raw.githubusercontent.com/machinezone/rcc/master/tools/install.sh`"
```

You can see what the install script is doing first [here](https://github.com/machinezone/rcc/blob/master/tools/install.sh).

### For folks familiar with Python

```
cd $HOME # or anywhere you want
python3 -mvenv venv
source venv/bin/activate
pip install rcc
rcc
```

## Rationale

rcc started as an attempt at writing an asyncio redis-cluster aware python client. It is now mostly used a redis cluster tool, built on a minimal but functional redis client library.

The main asyncio redis library, aioredis does not support redis cluster at this point. There is another library named aredis which has cluster support, but which has some small bugs for which pull requests existed, that were not merged until recently. Getting a redis client to work is not terribly hard, thanks to the design of redis, so I started this project and got it to work in a limited amount of time.

## Tools

Several tools come with this package, as subcommands of the main cli named `rcc`. Some documentation (wip) is available [here](https://machinezone.github.io/rcc/).

* keyspace / will turn on redis keyspace notifications and tell you what your _hot_ keys are.
* binpacking / will help reshard your cluster in an optimal way based on your usage. This will consume the output of the keyspace command

## Contributing

rcc is developed on [GitHub](https://github.com/machinezone/rcc). We'd love to hear about how you use it; opening up an issue on GitHub is ok for that. If things don't work as expected, please create an issue on GitHub, or even better a pull request if you know how to fix your problem.
