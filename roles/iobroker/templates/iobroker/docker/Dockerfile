FROM buanet/iobroker
LABEL maintainer="Alexander Groß <agross@therightstuff.de>" \
      local=true

RUN apt-get update \
    && apt-get install \
               --yes \
               android-tools-adb \
               cifs-utils \
               vim \
    && rm -rf /var/lib/apt/lists/* \
    && iobroker upgrade self
