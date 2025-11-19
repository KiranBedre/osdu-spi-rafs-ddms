# Build the application
FROM python:3.11-alpine AS release-env

ARG user_id=nonroot
ARG release_version
ENV RELEASE_VERSION=$release_version

ARG USERNAME=${user_id}
ARG USER_UID=1000
ARG USER_GID=1000

WORKDIR /app

# Create non-root user and group
RUN addgroup -g $USER_GID $USERNAME \
    && adduser -D --disabled-password --no-create-home -u $USER_UID -G $USERNAME --shell /sbin/nologin $USERNAME

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .

# Set ownership
RUN chown -R ${USERNAME}:${USERNAME} /app

# Remove shells for security
RUN rm -f /bin/ash /bin/sh

USER $USERNAME

ENTRYPOINT ["python", "/app/main.py"]
