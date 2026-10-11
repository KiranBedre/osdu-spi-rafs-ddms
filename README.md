# OSDU Rock and Fluid Sample DDMS for Azure

[![Release](https://img.shields.io/github/v/release/Azure/osdu-spi-rafs-ddms)](https://github.com/Azure/osdu-spi-rafs-ddms/releases)
[![Validate](https://github.com/Azure/osdu-spi-rafs-ddms/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/Azure/osdu-spi-rafs-ddms/actions/workflows/validate.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

> [!NOTE]
> Application source comes from the
> [OSDU community RAFS project](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services).
> Its [OpenAPI specification](docs/api/community/v2/openapi.yaml) describes the
> service contract.

Rock and Fluid Sample DDMS stores and retrieves rock samples, fluid samples,
sample analyses, and their associated datasets through OSDU services.

## At a glance

| | |
|---|---|
| API base path | `/api/rafs-ddms` |
| Swagger UI | `/api/rafs-ddms/docs` |
| Health | `/api/rafs-ddms/healthz` |
| Readiness | `/api/rafs-ddms/readiness` |
| Depends on | Storage, Dataset, Schema, Search, Entitlements, Partition, and Legal |
| Runtime | Python 3.11, FastAPI, port 8080 |
| Deployed by | [OSDU SPI Stack](https://github.com/Azure/osdu-spi-stack) (`software/stacks/osdu/services/rafs.yaml`) |

## Repository layout

[CONTRIBUTING.md](CONTRIBUTING.md) explains where each kind of change belongs.

| Path | Owner | Contents |
|---|---|---|
| `app/`, `client/`, `tests/` | OSDU upstream | Application, clients, unit tests, and integration tests |
| `devops/`, `deployments/` | OSDU upstream | Community deployment assets retained for source parity |
| `.spi/service.yaml`, `.spi/ci/` | This repository | SPI build, image, and acceptance contract |
| `.github/`, `build/` | SPI template | Shared repository automation and acceptance image |

The repository uses SPI's `passthrough` synchronization mode because the
community repository already contains the Azure implementation. The
`fork_upstream` branch mirrors community `main`; `fork_integration` stages
upstream updates before they reach this repository's `main`.

## Build

Python 3.11 is required. CI installs runtime and test requirements under the
runtime constraints, then runs the repository-owned build script:

```bash
python -m pip install -r requirements.txt
python -m pip install -c requirements.txt -r requirements-tests.in
python -m pip install pre-commit==4.3.0
.spi/ci/build.sh
```

The build runs the pre-commit policy on changed Python files and runs the unit
tests. Live integration tests and the Redis integration tests are deliberately
excluded from this lane.

## Configuration on SPI Stack

SPI Stack runs RAFS with workload identity and internal OSDU service URLs.
Important settings include:

| Variable | SPI value or source | Purpose |
|---|---|---|
| `CLOUD_PROVIDER` | `azure` | Select the Azure provider |
| `OPENAPI_PREFIX` | `/api/rafs-ddms` | Public route and OpenAPI prefix |
| `SERVICE_HOST_*` | Internal OSDU services | Storage, Dataset, Schema, Search, Entitlements, and Partition clients |
| `CACHE_ENABLE` | `true` when Redis Stack is deployed | Enable response caching |
| `REDIS_INDEX_ENABLE` | `true` when Redis Stack is deployed | Enable the derived RAFS search index |
| `USE_BLOB_STORAGE` | `false` initially | Keep data access through OSDU Dataset and Storage |

No credentials are stored in this repository. Azure access uses workload
identity; acceptance receives a short-lived bearer token at run time.

## Test

| Suite | Where | Runs in CI | Run it yourself |
|---|---|---|---|
| Unit | `tests/test_*` except `test_cache_integration` | Pull requests | `.spi/ci/build.sh` |
| Acceptance | `tests/integration/tests` | Pull requests against SPI Stack | `spi test rafs --source .` |
| Redis integration | `tests/test_cache_integration` | Not in the build lane | Run against a configured Redis instance |

Acceptance calls the deployed service through the gateway. The bindings in
`.spi/service.yaml` provide the gateway, partition, legal domain, cloud
provider, and bearer token.

Against an environment you are connected to:

```bash
spi test rafs
spi test rafs --source .
```

To call the API by hand:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  -H "data-partition-id: $PARTITION" \
  "$GATEWAY/api/rafs-ddms/healthz"
```

## Deploy

For a pull request from this repository that changes code, CI publishes the
service image and its acceptance image to GHCR. The Deploy and Test lane
borrows an SPI Stack environment, runs the candidate image, proves it with the
integration suite, and restores the environment's image.

To try a build by hand on a connected environment, pin it by digest and release
the pin when done:

```bash
spi service pin rafs --image ghcr.io/azure/osdu-spi-rafs-ddms@sha256:<digest>
spi service reset rafs
```

## License

Copyright © Microsoft Corporation

Licensed under the [Apache License 2.0](LICENSE).
