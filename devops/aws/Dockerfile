# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# docker build -t rafsdistroless -f Dockerfile .
# https://gealber.com/recipe-distroless-container-fastapi
ARG python_version=3.11
ARG amazonlinux_image=public.ecr.aws/amazonlinux/amazonlinux:2023
FROM ${amazonlinux_image} AS build-env
ARG pip_version=25.2

# CVE remediation: pull patched OS packages (curl/expat) from the current AL2023 snapshot
RUN dnf -y upgrade curl-minimal libcurl-minimal expat
RUN dnf update libxml2

RUN dnf update python-setuptools --releasever 2023.7.20250609

RUN dnf -y install python3.11 python3.11-pip

ADD requirements.txt /app/requirements.txt

RUN python3.11 -m venv "/app/venv/" --system-site-packages
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV /app/venv/
ENV PATH="/app/venv/bin:${PATH}"

RUN /app/venv/bin/python3 -m pip install --upgrade pip==${pip_version} \
      && /app/venv/bin/python3 -m pip install --no-cache-dir -I -r /app/requirements.txt \
      && /app/venv/bin/python3 -m pip install --no-cache-dir setuptools==78.1.1 --upgrade \
      && /app/venv/bin/python3 -m pip install --no-cache-dir -I uvicorn[standard]==0.23.2

COPY ./app /app/
WORKDIR /app

RUN cp -v /app/venv/bin/uvicorn .

FROM ${amazonlinux_image}
ARG python_version

# CVE remediation: pull patched OS packages (curl/expat) from the current AL2023 snapshot
RUN dnf -y upgrade curl-minimal libcurl-minimal expat
RUN dnf update libxml2
RUN dnf -y install shadow-utils
RUN dnf -y install python3.11
RUN dnf update python-setuptools --releasever 2023.7.20250609

RUN groupadd --system appusers && useradd --system appuser && usermod -a -G appusers appuser

COPY --from=build-env --chown=appuser:appusers /app /app/
COPY --from=build-env --chown=appuser:appusers /app/ /app/app

WORKDIR /app
ENV VIRTUAL_ENV /app/venv/
ENV PATH="/app/venv/bin:${PATH}"

ARG build_date
ARG commit_id
ARG commit_branch
ARG commit_message
ARG release_version
ENV BUILD_DATE $build_date
ENV COMMIT_ID $commit_id
ENV COMMIT_BRANCH $commit_branch
ENV COMMIT_MESSAGE=$commit_message
ENV RELEASE_VERSION=$release_version

RUN /app/app/venv/bin/python3 -m pip install setuptools==78.1.1 --upgrade

WORKDIR /app
EXPOSE 8080

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "8", "--loop", "uvloop"]
