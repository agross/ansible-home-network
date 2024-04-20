# hadolint ignore=DL3007
FROM tecnativa/docker-socket-proxy:latest

RUN sed -i /usr/local/etc/haproxy/haproxy.cfg.template \
        -e 's/bind .*/bind 127.0.0.1:2375/'
