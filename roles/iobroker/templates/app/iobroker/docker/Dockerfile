FROM buanet/iobroker:latest-v5
LABEL maintainer="Alexander Groß <agross@therightstuff.de>" \
      local=true

RUN apt-get update \
    && apt-get upgrade \
               --yes \
    && apt-get install \
               --yes \
               android-tools-adb \
               cifs-utils \
               vim \
    && rm -rf /var/lib/apt/lists/* \
    && iobroker upgrade self
