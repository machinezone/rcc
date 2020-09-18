# Kubernete

Operating a [Redis Cluster](https://redis.io/topics/cluster-tutorial) on [Kubernete](https://kubernetes.io/) (or anywhere) is not trivial, and it can take a lot of trial and errors to end up with a good setup. Thanksfully the internet is full of guides which helped a lot.

Using a stateful set, as described in this [post](https://rancher.com/blog/2019/deploying-redis-cluster/) is the best and simplest option. To go the extra mile and have auto-scaling, using an Operator is a better option, with the caveat that debugging problems can be tricky as operators are a bit of black box.
