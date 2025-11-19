# RAFS DDMS Cronjob for CIMPL

Python-based cronjob that triggers the RAFS DDMS Service Account indexer endpoint.

## Purpose

Periodically calls the RAFS indexer API endpoint to trigger reindexing of service account data.

## Quick Start

```shell
docker run -it --rm \
  --env OAUTH_TOKEN_URL=https://keycloak.dev1.osdu-cimpl.opengroup.org/realms/osdu/protocol/openid-connect/token \
  --env CLIENT_ID=<your-client-id> \
  --env CLIENT_SECRET=<your-client-secret> \
  --env OAUTH_SCOPE="<client-id>/.default openid profile" \
  --env RAFS_URI=https://opendes.dev1.osdu-cimpl.opengroup.org \
  --env DATA_PARTITION_ID=opendes \
  <registry>/cimpl-rafs-ddms-cronjob:latest
```

## Build

```shell
docker build -t cimpl-rafs-ddms-cronjob:latest .
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OAUTH_TOKEN_URL` | Yes | - | OAuth token endpoint URL |
| `CLIENT_ID` | Yes | - | OAuth client ID |
| `CLIENT_SECRET` | Yes | - | OAuth client secret |
| `OAUTH_SCOPE` | Yes | - | OAuth scope (e.g., "client-id/.default openid profile") |
| `RAFS_URI` | Yes | - | RAFS base URI (e.g., https://tenant.domain.com) |
| `DATA_PARTITION_ID` | No | "opendes" | Data partition identifier |

## What It Does

1. Validates all required environment variables
2. Obtains OAuth access token using client credentials flow
3. Calls `GET /api/rafs-ddms/dev/trigger-sa-indexer` with bearer token
4. Retries up to 5 times with 4-second delays on failure
5. Expects HTTP 200 response
6. Exits with code 0 on success, 1 on failure

## Development

Local testing:

```shell
export OAUTH_TOKEN_URL=https://keycloak.dev1.osdu-cimpl.opengroup.org/realms/osdu/protocol/openid-connect/token
export CLIENT_ID=your-client-id
export CLIENT_SECRET=your-client-secret
export OAUTH_SCOPE="your-client-id/.default openid profile"
export RAFS_URI=https://opendes.dev1.osdu-cimpl.opengroup.org
export DATA_PARTITION_ID=opendes

python main.py
```

## Migration from Go (Azure)

This Python implementation replaces the previous Go-based cronjob that used Azure Key Vault. Key changes:

- **Removed**: Azure SDK dependencies, Key Vault integration
- **Added**: Direct environment variable configuration
- **Maintained**: Same retry logic (5 attempts, 4s delay), same API endpoint, same functionality
- **Benefits**: Simpler deployment, language consistency with main service, faster implementation
