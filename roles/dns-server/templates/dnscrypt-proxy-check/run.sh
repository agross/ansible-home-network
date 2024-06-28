#!/usr/bin/env sh

docker image build --tag dnscrypt-check . &&
  docker container run --rm -it dnscrypt-check
