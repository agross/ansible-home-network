FROM alpine:edge

RUN apk add \
        --no-cache \
        bind-tools \
        bash \
        curl \
        dnscrypt-proxy

WORKDIR /data

COPY test.sh /usr/bin/

CMD [ "test.sh" ]
