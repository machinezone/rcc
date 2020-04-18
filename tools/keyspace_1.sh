#!/bin/sh

redis-cli set foo bar
redis-cli set foo bar
redis-cli get foo

redis-cli set bar baz
redis-cli set bar baz
