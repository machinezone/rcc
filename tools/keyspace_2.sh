#!/bin/sh

redis-cli -c -p 11000 set foo bar
redis-cli -c -p 11000 set foo bar
redis-cli -c -p 11000 get foo

redis-cli -c -p 11000 set bar baz
redis-cli -c -p 11000 set bar baz
