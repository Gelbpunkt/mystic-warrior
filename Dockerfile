FROM python:3.8.0rc1-alpine3.10

WORKDIR /bot
COPY requirements.txt .

RUN apk add --no-cache --virtual .deps gcc linux-headers musl-dev libffi-dev openssl-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del .deps

COPY . .
CMD python run.py
