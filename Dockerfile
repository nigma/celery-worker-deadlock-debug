FROM python:3.6

ENV PYTHONUNBUFFERED 1
ENV PIP_NO_CACHE_DIR off
ENV PIP_DISABLE_PIP_VERSION_CHECK on

RUN set -eux \
    && apt-get update && apt-get install -y --no-install-recommends strace lsof && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove

RUN mkdir -p /app /static
WORKDIR /app

COPY requirements.txt /app/

RUN set -eux \
    && pip3 install --no-cache-dir -U pip setuptools \
    && pip3 install --no-cache-dir --timeout 1000 -r requirements.txt

COPY . /app/

EXPOSE 5555
