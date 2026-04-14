# Build the application from source
ARG golang_version=1.25
FROM golang:${golang_version}-alpine AS build-env

# CVE-2026-28390: openssl DoS (NULL ptr in CMS) - upgrade libcrypto3/libssl3
# CVE-2026-40200: musl libc arbitrary code execution - upgrade musl/musl-utils
RUN apk update && apk add --no-cache --upgrade zlib libcrypto3 libssl3 musl musl-utils

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY *.go ./
RUN CGO_ENABLED=0 GOOS=linux go build -o /rafs-cronjob

# Deploy the application binary into a secure image
FROM golang:${golang_version}-alpine AS release-env

# CVE-2026-28390: openssl DoS (NULL ptr in CMS) - upgrade libcrypto3/libssl3
# CVE-2026-40200: musl libc arbitrary code execution - upgrade musl/musl-utils
RUN apk update && apk add --no-cache --upgrade zlib libcrypto3 libssl3 musl musl-utils

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
RUN addgroup -g $USER_GID $USERNAME \
    && adduser -D --disabled-password --no-create-home -u $USER_UID -G $USERNAME --shell /sbin/nologin $USERNAME

RUN rm -R /bin/ash \
    && rm -R /bin/sh

COPY --from=build-env --chown=${USERNAME}:${USERNAME} /rafs-cronjob /rafs-cronjob

USER $USERNAME

ENTRYPOINT ["/rafs-cronjob"]
