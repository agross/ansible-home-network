FROM python:3-alpine

# hadolint ignore=DL3013,DL3018
RUN apk add --no-cache git && \
    pip install --no-cache-dir --upgrade git+https://github.com/agross/populartimes

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./

EXPOSE 5000
ENTRYPOINT [ "flask" ]
CMD [ "run", "--host=0.0.0.0" ]
