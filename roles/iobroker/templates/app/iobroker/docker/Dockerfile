FROM buanet/iobroker:latest-v7
LABEL maintainer="Alexander Groß <agross@therightstuff.de>" \
      local=true

RUN apt-get update \
    && apt-get upgrade \
               --yes \
    && apt-get install \
               --yes \
               android-tools-adb \
               cifs-utils \
               iputils-ping \
               vim \
    && rm -rf /var/lib/apt/lists/* \
    && iobroker upgrade self
