FROM redis/redis-stack-server:7.4.0-v8

# CVE-2025-68973: GnuPG information disclosure - upgrade gpgv (fix: 2.2.27-3ubuntu2.5)
RUN apt-get update \
    && apt-get upgrade -y gpgv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
