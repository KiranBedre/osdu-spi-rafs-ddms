# Using python 3.11 and Debian bookworm to have latest security updates and be in current support lifecycle
ARG python_version=3.11
FROM python:${python_version}-slim-bookworm AS build-env

# Must re-declare ARG after FROM to make it available in this stage
ARG python_version=3.11

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt \
    && pip install --no-cache-dir --upgrade "setuptools>=82.0.1" "wheel==0.46.3" \
    && pip install --no-cache-dir uvicorn[standard]==0.23.2

COPY ./app /app/
WORKDIR /app

RUN cp -v $(which uvicorn) .

# Python 3.11 on Debian trixie for runtime (patched system libs vs bookworm)
# Fixes: CVE-2023-45853 (zlib), CVE-2025-7458 (sqlite), CVE-2026-0861 (glibc), CVE-2026-29111 (systemd)
FROM python:${python_version}-slim-trixie AS runtime-env

# Must re-declare ARG after FROM to make it available in this stage
ARG python_version=3.11

# Apply OS security patches for packages with fixes available
# CVE-2026-28390: openssl/libssl3t64/openssl-provider-legacy DoS (NULL ptr in CMS)
RUN apt-get update \
    && apt-get upgrade -y openssl libssl3t64 openssl-provider-legacy \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Remove packages with no patched version available and not needed at runtime
# CVE-2025-69720: ncurses | CVE-2026-29111: libsystemd0/libudev1
RUN dpkg --force-all --purge ncurses-bin ncurses-base libncursesw6 libtinfo6 libsystemd0 libudev1 2>/dev/null || true \
    && rm -rf /usr/share/terminfo /var/lib/apt/lists/*

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

# Create non-root user and group
ARG USERNAME=${user_id}
ARG USER_UID=1000
ARG USER_GID=1000

# Create group and user without sudo privileges
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID --create-home --home-dir /home/$USERNAME --shell /usr/sbin/nologin $USERNAME


COPY --from=build-env /usr/local/lib/python${python_version}/site-packages /usr/local/lib/python${python_version}/site-packages
COPY --from=build-env --chown=${USERNAME}:${USERNAME} /app /app/app
COPY --from=build-env --chown=${USERNAME}:${USERNAME} /app/uvicorn /app/uvicorn

# Patch setuptools vendored deps AFTER COPY — Trivy scans runtime image layers
# CVE-2026-23949: setuptools vendors jaraco.context 5.3.0 (vulnerable < 6.1.0)
# CVE-2026-24049: setuptools vendors wheel 0.45.1 (vulnerable < 0.46.2)
RUN set -eux; \
    SP=/usr/local/lib/python${python_version}/site-packages; \
    \
    # jaraco.context: overwrite vendored code with patched standalone version
    cp -v $SP/jaraco/context/__init__.py $SP/setuptools/_vendor/jaraco/context.py; \
    # jaraco.context: overwrite vendored dist-info METADATA (Trivy reads version from here)
    JARACO_SRC=$(find $SP -maxdepth 1 -type d -name "jaraco*context*.dist-info" | head -1); \
    JARACO_DST=$(find $SP/setuptools -type d -name "jaraco*context*.dist-info" | head -1); \
    [ -n "$JARACO_SRC" ] && [ -n "$JARACO_DST" ] \
        && cp -v "$JARACO_SRC/METADATA" "$JARACO_DST/METADATA" \
        || (echo "ERROR: jaraco.context dist-info not found" && exit 1); \
    \
    # wheel: remove stale 0.45.1 dist-info from site-packages root
    rm -rf $SP/wheel-0.45.1.dist-info; \
    # wheel: overwrite vendored dist-info METADATA and code
    WHEEL_DST=$(find $SP/setuptools -type d -name "wheel*.dist-info" | head -1); \
    [ -n "$WHEEL_DST" ] && cp -v $SP/wheel-0.46.3.dist-info/METADATA "$WHEEL_DST/METADATA"; \
    WHEEL_CODE=$(find $SP/setuptools -type d -name "wheel" | head -1); \
    [ -n "$WHEEL_CODE" ] && cp -rv $SP/wheel/. "$WHEEL_CODE/"

USER $USERNAME


ENTRYPOINT ["python", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4", "--loop", "uvloop"]
