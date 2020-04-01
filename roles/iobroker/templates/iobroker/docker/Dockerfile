FROM buanet/iobroker
LABEL maintainer="Alexander Groß <agross@therightstuff.de>"

RUN apt-get update \
    && apt-get install \
               --yes \
               cifs-utils \
               vim \
    && rm -rf /var/lib/apt/lists/*
