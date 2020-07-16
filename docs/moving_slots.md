# Moving Slots

The `cluster-move-slots` is a new command which emulates what `redis-cli reshard` does. It moves slots around your cluster, and is very explicit:

* source node
* target node
* number of slots to move around, starting from the smallest one available.

# Demo

```
(venv) tests$
(venv) tests$ rcc cluster-nodes
adc231aa9f86bf1fdfe3d9260bd19b3e5d157623 127.0.0.1:11000 master 0-5460
8c093d2dabea7fd8d0ec178e66d84bbe7158969f 127.0.0.1:11001 master 5461-10922
a85ceda7c10710090fd398a7d0760cc9f2ba3b12 127.0.0.1:11002 master 10923-16383
80c1b8c0a3ff2ee02f40897f5c8a1c3f8bef3cd2 127.0.0.1:11003 slave
a2a0840a6de743f03c01cc80f9d87d7b6b655468 127.0.0.1:11004 slave
589fda2811149875e1f087d6eae09cee6e77b6d2 127.0.0.1:11005 slave
(venv) tests$
(venv) tests$ rcc cluster-move-slots --help
Usage: rcc cluster-move-slots [OPTIONS]

  Move cluster slots from a source node to target one

Options:
  -u, --redis-url TEXT
  -a, --password TEXT
  --user TEXT
  --port INTEGER
  --dry
  --cluster_from TEXT
  --cluster_to TEXT
  --slots INTEGER
  --timeout INTEGER     Max time to wait for consistency check
  --help                Show this message and exit.
(venv) tests$ rcc cluster-move-slots --cluster-from adc231aa9f86bf1fdfe3d9260bd19b3e5d157623 --cluster-to 8c093d2dabea7fd8d0ec178e66d84bbe7158969f --slots 500
Migrating 500 hash slots  [####################################]  100%
(venv) tests$
(venv) tests$ rcc cluster-nodes
adc231aa9f86bf1fdfe3d9260bd19b3e5d157623 127.0.0.1:11000 master 500-5460
8c093d2dabea7fd8d0ec178e66d84bbe7158969f 127.0.0.1:11001 master 0-499 5461-10922
a85ceda7c10710090fd398a7d0760cc9f2ba3b12 127.0.0.1:11002 master 10923-16383
80c1b8c0a3ff2ee02f40897f5c8a1c3f8bef3cd2 127.0.0.1:11003 slave
a2a0840a6de743f03c01cc80f9d87d7b6b655468 127.0.0.1:11004 slave
589fda2811149875e1f087d6eae09cee6e77b6d2 127.0.0.1:11005 slave
```

Now we will move those slots back to the first node.

```
(venv) tests$
(venv) tests$ rcc cluster-move-slots --cluster-from 8c093d2dabea7fd8d0ec178e66d84bbe7158969f --cluster-to adc231aa9f86bf1fdfe3d9260bd19b3e5d157623 --slots 500
Migrating 500 hash slots  [####################################]  100%
(venv) tests$
(venv) tests$
(venv) tests$
(venv) tests$
(venv) tests$ rcc cluster-nodes
adc231aa9f86bf1fdfe3d9260bd19b3e5d157623 127.0.0.1:11000 master 0-5460
8c093d2dabea7fd8d0ec178e66d84bbe7158969f 127.0.0.1:11001 master 5461-10922
a85ceda7c10710090fd398a7d0760cc9f2ba3b12 127.0.0.1:11002 master 10923-16383
80c1b8c0a3ff2ee02f40897f5c8a1c3f8bef3cd2 127.0.0.1:11003 slave
a2a0840a6de743f03c01cc80f9d87d7b6b655468 127.0.0.1:11004 slave
589fda2811149875e1f087d6eae09cee6e77b6d2 127.0.0.1:11005 slave
```
