FROM nextcloud:32.0.5-apache

RUN apt-get update \
    \
    \
    && printf '%bInstalling Office preview support.%b\n' '\e[32;1m' '\e[0m' \
    && mkdir --parents \
             /usr/share/man/man1/ \
    && apt-get install --yes \
                       default-jre \
                       libreoffice \
    \
    \
    && printf '%bInstalling ImageMagick with SVG support.%b\n' '\e[32;1m' '\e[0m' \
    && apt-get install --yes \
                       imagemagick \
    # Enable reading PDFs. https://www.kb.cert.org/vuls/id/332928/ \
    # Not required for ImageMagick >= 7. \
    && ( sed -i '/disable ghostscript format types/,+6d' /etc/ImageMagick-6/policy.xml || true ) \
    \
    \
    && printf '%bInstalling OCR support.%b\n' '\e[32;1m' '\e[0m' \
    && apt-get install --yes \
                       tesseract-ocr \
                       tesseract-ocr-deu \
                       tesseract-ocr-eng \
    \
    \
    && rm -rf /var/lib/apt/lists/*
