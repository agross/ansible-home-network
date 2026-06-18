FROM nextcloud:33.0.5-apache

RUN apt-get update \
    \
    \
    && printf 'Installing Office preview support.\n' \
    && apt-get install --yes \
                       libreoffice-nogui \
    \
    \
    && printf 'Installing OCR support.\n' \
    && apt-get install --yes \
                       tesseract-ocr \
                       tesseract-ocr-deu \
                       tesseract-ocr-eng \
    \
    \
    && rm -rf /var/lib/apt/lists/*
