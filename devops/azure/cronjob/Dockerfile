# Build the application from source
ARG golang_version=1.24
FROM golang:${golang_version}-trixie AS build-env

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY *.go ./
RUN CGO_ENABLED=0 GOOS=linux go build -o /rafs-cronjob

# Deploy the application binary into a secure image
FROM golang:${golang_version}-trixie AS release-env
ARG golang_version
ARG user_id=nonroot

ARG release_version
ENV RELEASE_VERSION=$release_version

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /

# Create non-root user and group
ARG USERNAME=${user_id}
ARG USER_UID=1000
ARG USER_GID=1000

# Create group and user without sudo privileges
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID --create-home --home-dir /home/$USERNAME --shell /usr/sbin/nologin $USERNAME

RUN rm -R /bin/bash \
    && rm -R /bin/sh

COPY --from=build-env --chown=${USERNAME}:${USERNAME} /rafs-cronjob /rafs-cronjob

USER $USERNAME

ENTRYPOINT ["/rafs-cronjob"]
