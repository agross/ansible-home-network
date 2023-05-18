# hadolint ignore=DL3007
FROM tecnativa/docker-socket-proxy:latest

RUN sed -i /usr/local/etc/haproxy/haproxy.cfg \
        -e 's/bind :2375/bind 127.0.0.1:2375/'
