# -------------------------------
# Test Stage: run pytest
# -------------------------------
ARG python_version=3.11
FROM mcr.microsoft.com/devcontainers/python:${python_version}-bookworm as test-stage

ARG pip_version=25.2
ARG piptools_version=7.3.0

COPY requirements.txt /app/requirements.txt
RUN --mount=type=secret,id=pip_index_url,target=/run/secrets/pip_index_url \
    pip install --index-url $(cat /run/secrets/pip_index_url) --no-cache-dir -r /app/requirements.txt

ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=./

COPY requirements-tests.in ./
COPY requirements.in ./
RUN --mount=type=secret,id=pip_index_url,target=/run/secrets/pip_index_url \
    pip install --index-url $(cat /run/secrets/pip_index_url) --upgrade pip==${pip_version} && \
    pip install --index-url $(cat /run/secrets/pip_index_url) pip-tools==${piptools_version} && \
    pip-compile --index-url $(cat /run/secrets/pip_index_url) requirements.in requirements-tests.in -o requirements-tests.txt -v && \
    pip install --index-url $(cat /run/secrets/pip_index_url) -r requirements-tests.txt

COPY ./app /app
COPY ./tests /tests
COPY ./client /client

WORKDIR ./tests

RUN python -m pytest -p no:cacheprovider --ignore=integration

# -------------------------------
# Build Stage: Build the application
# -------------------------------

ARG python_version=3.11

FROM mcr.microsoft.com/devcontainers/python:${python_version}-bookworm AS build-env

ARG pip_version=25.2
ARG setuptools_version=70.0.0
ARG uvicorn_version=0.23.2

# Update package list and upgrade vulnerable packages
# CVE-2026-28390: openssl DoS - upgrade libssl3t64
RUN apt-get update \
    && apt-get upgrade -y libssl3t64 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

# Upgrade pip and setuptools with pinned versions; install requirements
RUN --mount=type=secret,id=pip_index_url,target=/run/secrets/pip_index_url \
    pip install --index-url $(cat /run/secrets/pip_index_url) pip==${pip_version} setuptools==${setuptools_version} && \
    pip install --index-url $(cat /run/secrets/pip_index_url) --no-cache-dir -r /app/requirements.txt && \
    pip install --index-url $(cat /run/secrets/pip_index_url) --no-cache-dir uvicorn[standard]==${uvicorn_version}

COPY ./app /app/
WORKDIR /

RUN --mount=type=secret,id=pip_index_url,target=/run/secrets/pip_index_url pip install --index-url $(cat /run/secrets/pip_index_url) --no-cache-dir uvicorn[standard]==0.23.2
RUN cp -v $(which uvicorn) .

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4", "--loop", "uvloop"]
