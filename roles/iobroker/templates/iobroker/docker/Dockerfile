FROM buanet/iobroker:latest-v9

# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get upgrade \
               --yes \
    && apt-get install \
               --yes \
               --no-install-recommends \
               android-tools-adb \
               iputils-ping \
               vim \
    && rm -rf /var/lib/apt/lists/* \
    && iobroker upgrade self
