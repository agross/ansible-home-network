FROM buanet/iobroker:latest-v10

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get upgrade \
               --yes \
    && apt-get install \
               --yes \
               --no-install-recommends \
               android-tools-adb \
               dnsutils \
               iputils-ping \
               iproute2 \
               tcpdump \
               vim \
    && rm -rf /var/lib/apt/lists/* \
    && iobroker upgrade self
