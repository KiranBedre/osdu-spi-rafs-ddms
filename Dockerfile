# Using python 3.11 and Debian trixie to have latest security updates and be in current support lifecycle
ARG python_version=3.11
FROM python:${python_version}-trixie AS build-env

ARG pip_version=25.2
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip==${pip_version} setuptools \
      && pip install --no-cache-dir -r /app/requirements.txt

COPY ./app /app/
WORKDIR /app

# Only needed for production uvloop==0.18.0
RUN pip install --no-cache-dir uvicorn[standard]==0.23.2
RUN cp -v $(which uvicorn) .

# Using python 3.11 and Debian trixie slim to have latest security updates, lean version, and be in current support lifecycle
FROM python:${python_version}-slim-trixie AS runtime-env
ARG python_version
ARG user_id=nonroot

ARG build_date
ARG commit_id
ARG commit_branch
ARG commit_message
ARG release_version
ENV BUILD_DATE=$build_date
ENV COMMIT_ID=$commit_id
ENV COMMIT_BRANCH=$commit_branch
ENV COMMIT_MESSAGE=$commit_message
ENV RELEASE_VERSION=$release_version

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH=/usr/local/lib/python${python_version}/site-packages
ENV PYTHONUNBUFFERED=1

WORKDIR /app
EXPOSE 8080

# patch vulnerabilities
RUN pip install setuptools --upgrade

# Create non-root user and group
ARG USERNAME=${user_id}
ARG USER_UID=1000
ARG USER_GID=1000

# Create group and user without sudo privileges
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID --create-home --home-dir /home/$USERNAME --shell /usr/sbin/nologin $USERNAME

# disable ability to shell into image
RUN rm -R /bin/bash \
    && rm -R /bin/sh

WORKDIR /app

COPY --from=build-env /usr/local/lib/python${python_version}/site-packages /usr/local/lib/python${python_version}/site-packages
COPY --from=build-env --chown=${USERNAME}:${USERNAME} /app /app/app
COPY --from=build-env --chown=${USERNAME}:${USERNAME} /app/uvicorn /app/uvicorn

USER $USERNAME

ENTRYPOINT ["python", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4", "--loop", "uvloop"]
