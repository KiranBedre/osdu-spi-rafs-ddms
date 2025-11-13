# Rock and Fluid Sample (RAFS) DDMS

## Introduction

Rock and Fluid Sample Domain Data Management Services (RAFS DDMS) Open Subsurface Data Universe (OSDU) is a microservices-based project that comprises OSDU software ecosystem, written in Python that provides an API for Rock and Fluid Sample related data.

For business context, videos, slides, OSDU schemas, and FAQs about the RAFS DDMS see [this separate Member Gitlab wiki](https://gitlab.opengroup.org/osdu/subcommittees/data-def/projects/RAFSDDMSDEV/home/-/wikis/home).

[[_TOC_]]

## Project structure

    app
    ├── api              - web related stuff.
    │   ├── dependencies - dependencies for routes definition.
    │   ├── errors       - definition of error handlers.
    │   └── routes       - web routes.
    ├── core             - application configuration, startup events, logging.
    ├── db               - db related stuff.
    ├── models           - pydantic models for this application.
    │   ├── domain       - main models that are related to the rock and fluid samples domain
    │   └── schemas      - schemas for using in web routes (request, responses bodies).
    ├── resources        - any useful blob/file or constants
    ├── services         - logic that is not just crud related.
    └── main.py          - FastAPI application creation and configuration.

## Project Tutorial

Instructions and payload examples are presented on [the tutorial page](./docs/tutorial/readme.md).

## API Specs

Compiled REST API documentation is presented in the [openapi.json](./docs/spec/openapi.json) file.

## DDMS Footprint

The DDMS Footprint lists of the OSDU `group-type--EntityType` and `content types` handled by the DDMS.

RAFS DDMS Footpring is presented in the [file](./docs/rafs_ddms_footprint_v0.28.json).

## OSDU Well Known Schemas Disclaimer

Note regarding OSDU Well Known Schema interaction: Currently (April 2023), OSDU Data Definitions "Fluid Samples" and "Samples & Petrophysics" Project teams are re-working the data model for both rock and fluid samples in a way that there will be a unified way to handle both. That means that today there are no FluidSample, FluidSampleAnalysis, or FluidSampleAcquisition schemas published by OSDU Data Definitions, which can be used by the DDMS. Similarly, it is likely that RockSample, RockSampleAnalysis, and Coring schemas will be changed by the Forum or even be deprecated and replaced in the near future. In light of this: 1) With regard to PVT, the RAFS DDMS currently uses custom WPC and Master schemas 2) With regard to RCA, the DDMS does have relationship to the existing rock-related schemas mentioned above. In both cases, the DDMS will need to be updated when the revised OSDU Data Definitions data model is published. 

**NB**: Before the custom schemas are marked as the official well-known schemas, the next custom schemas must be registered during the deployment of the service.

[RAFS DDMS custom schemas](./deployments/README.md).

## Content Schemas

You can find more information about content schemas [here](app/models/data_schemas/README.md).

## Project Startup
### Configuration

The settings module can read environment variables as long as they are declared as fields of the
Settings class (see app/core/settings/base.py).

Or they can be provided in a .env or prod.env files

#### Python Version
RAFS DDMS runs in **Python 3.11**.  <br/>
> **NOTE:** The pip install will not currently work on Windows.  Requires a Linux machine (or Container).

#### Local settings

Add an .env with:

```
APP_ENV="dev"
OPENAPI_PREFIX="/api/os-rafs-ddms"  # optional
CLOUD_PROVIDER="azure"
API_BASE_URL="osdu_endpoint"
SERVICE_HOST_DATASET="${API_BASE_URL}/api/dataset/v1"
SERVICE_HOST_STORAGE="${API_BASE_URL}/api/storage/v2"
# Optionally add any other env var (BUILD_DATE, etc.)
```

#### Cache settings

> NOTE: Redis Cache it is a NFR, it is used to improve resiliency and performance.

It is needed to add the following variables to .env to set up cache layer:

```
CACHE_ENABLE=True
CACHE_BACKEND="app.core.helpers.cache.backends.redis_cache.RedisCacheBackend"
```

The `CACHE_ENABLE` variable can enable or disable cache for all app.
Besides, to disable caching in a request just use "Cache-Control" in a request header as "no-store" or "no-cache".

The `CACHE_BACKEND` variable is a path to your backend,
which is used to initialize FastAPICache like [here](https://github.com/long2ice/fastapi-cache#quick-start).

You can use already prepared backends like:
 * `app.core.helpers.cache.backends.redis_cache.RedisCacheBackend`
 * `app.core.helpers.cache.backends.inmemory_cache.InMemoryCacheBackend`

Also, you can customize and use your own one.
Customized backend is supposed to be based on [BaseCacheBackend class](/app/core/helpers/cache/backends/base_cache.py).

To set up custom backend you maybe need to add optional variables to .env. For example for RedisCacheBackend we use:
```
REDIS_HOSTNAME=xxxxxx.redis.cache.windows.net
REDIS_PASSWORD=<redis-key>
REDIS_DATABASE=13
REDIS_SSL=True
REDIS_PORT=6380
```

By default `ttl = 60` sec is used. It is possible to set another ttl through the `CACHE_DEFAULT_TTL` variable.
Also, it is possible to set ttl manually for a specific request directly at the place where @cache is used.

##### Deployment-Specific Redis Configuration

**Note:** Redis environment variables may be overridden in deployment configurations depending on your cloud provider:

**For local development/testing (Docker):**
```bash
REDIS_HOSTNAME=redis        # Docker service name
REDIS_PASSWORD=             # Empty for local Docker Redis
REDIS_PORT=6379
REDIS_DATABASE=0
REDIS_SSL=False
```

**For production deployments:**
- **Azure**: Redis hostname is configured via Helm values (default: `redis-rafs-service`) and password from Azure KeyVault. See [Azure deployment docs](./devops/azure/README.md).
- **Google Cloud**: Redis hostname defaults to `redis-rafs-ddms` if `redisRafsDdmsHost` is empty in Helm values, otherwise uses specified external Redis. Password from Kubernetes secrets. See [GC deployment docs](./devops/gc/deploy/README.md).

Deployment configurations take precedence over local `.env` settings.

##### Cache Logging

The Redis cache backend includes automatic logging at DEBUG level for cache operations:
- **Cache HIT**: When data is successfully retrieved from cache
- **Cache MISS**: When requested data is not found in cache
- **Cache SET**: When data is stored in cache

To view cache logs, ensure your logging level is set to DEBUG in `tests/integration/pytest.ini` or your application configuration. This provides visibility into cache utilization during both application runtime and integration tests.

### Run with Docker

Docker-compose it is meant to be used for local development/testing, not for production, be aware that docker-compose uses higher privileges for development and testing purposes, we wouldn't recommend to use the [docker-compose](./docker-compose.yml) file for production, only for developers to be able to add changes and test them in local as well as unit/integration tests to avoid having to install all the dependencies.
We are using a distroless image as the default production docker image for an improved security experience.

#### Docker Flavor Versions (docker-compose)

* [Distroless - Dockerfile](./Dockerfile) is the default image to run with [docker-compose](./docker-compose.yml).  It is a balanced, production ready dockerfile which can be used to deploy an application as well as to develop on your local machine. It is a lean dockerfile (which is a best approach for production systems due lack of unneeded binaries and libraries) and this approach will be ideal to address security CVEs and to have lean version of RAFS DDMS.
  * Distroless build around ~400MB, you can test it `docker-compose --profile distroless up distroless`
* [tests - Dockerfile_test](./Dockerfile.tests) Dockerfile definition which contains and install all dependencies needed for unit/integration tests.

#### Quickly run docker-compose

**WARNING** Docker-compose it is meant to be used for quick development/testing, not for production.

```shell
OSDU_ENDPOINT=https://<osdu>.<fqdn>
cat > .env <<EOF
SERVICE_NAME=rafs-ddms
OPENAPI_PREFIX=/api/rafs-ddms
CLOUD_PROVIDER=azure
SERVICE_HOST_STORAGE=${OSDU_ENDPOINT}/api/storage/v2
SERVICE_HOST_PARTITION=${OSDU_ENDPOINT}/api/partition/v1
SERVICE_HOST_DATASET=${OSDU_ENDPOINT}/api/dataset/v1
SERVICE_HOST_SCHEMA=${OSDU_ENDPOINT}/api/schema-service/v1
SERVICE_HOST_SEARCH=${OSDU_ENDPOINT}/api/search/v2
CACHE_ENABLE=False
EOF

docker-compose up

# Simple test
curl localhost:8080/api/rafs-ddms/info
```

#### Run with Dockerfile
```
export BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
export COMMIT_ID=$(git rev-parse HEAD)
export COMMIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
export COMMIT_MESSAGE=$(git log -1 --pretty=%B)

docker build -f "./Dockerfile" \
    --build-arg build_date="$BUILD_DATE" \
    --build-arg commit_id="$COMMIT_ID" \
    --build-arg commit_branch="$COMMIT_BRANCH" \
    --build-arg commit_message="$COMMIT_MESSAGE" . \
    -t rafs-ddms:latest

docker run rafs-ddms:latest
```

### Run with Uvicorn

```
uvicorn app.main:app --port LOCAL_PORT
```

To see the OpenAPI page, follow the link:

`http://127.0.0.1:<LOCAL_PORT>/<OPENAPI_PREFIX>/docs`

Use the `OPENAPI_PREFIX` value used for project settings.

## Testing

### Run Unit Tests

**WARNING:** It is recommended to use the [Dockerfile](./Dockerfile) image for production systems.  The [Dockerfile.tests](./Dockerfile.tests) image, contains extra dependencies needed for testing purposes and is not intended for production use.

Unit tests

```shell
docker-compose --profile tests run tests
docker-compose --profile tests run --rm tests flake8 / --config=/setup.cfg
docker-compose --profile tests run --rm tests flake8 /app --select T1
```

### Run Cache Integration Tests

Redis cache integration tests verify that the cache backend is functioning correctly with a real Redis connection. These tests are isolated from the main integration tests and only run when `CACHE_ENABLE=True` in your `.env` file.

**Local Docker Redis configuration for testing:**
```shell
# Add to .env for local Docker testing
CACHE_ENABLE=True
CACHE_BACKEND="app.core.helpers.cache.backends.redis_cache.RedisCacheBackend"
REDIS_HOSTNAME=redis
REDIS_PORT=6379
REDIS_DATABASE=0
REDIS_SSL=False
REDIS_PASSWORD=
```

**Run cache tests:**
```shell
docker-compose --profile tests up cache_tests
```

The cache tests verify:
- Redis backend initialization
- Cache set and get operations
- Cache miss behavior
- Cache expiration/TTL
- Cache value overwriting
- Cache hit/miss/set logging

All cache operations are logged at DEBUG level, providing visibility into cache utilization.

### Run Local Integration Tests

Using Docker [env substitution from shell](https://docs.docker.com/compose/environment-variables/set-environment-variables/#substitute-from-the-shell) capabilities.

```shell
# Start docker-compose 
docker-compose up rafs
# Export needed envs for testing
# Internal hostname in docker-compose (app)
# Alternatively you can choose to test in remote env
export DDMS_BASE_URL=http://rafs:8080
export ACCESS_TOKEN=<access_token>
export PARTITION=<partition>
export URL_PREFIX=api/rafs-ddms
export CLOUD_PROVIDER=<cloud-provider>
export DOMAIN=<domain>
# Run test
docker-compose build tests
docker-compose --profile tests run --rm integration

# (Optional) Cleanup
docker-compose down
```

### Local running
1. Install virtual env if needed
   ```
    python -m venv integration_env
    source integration_env/bin/activate
   ```
2. Install requests
    ```
    pip install -r requirements.txt
    pip install -r requirements-tests.in
    ````

3. 
- Run via Terminal:
    ```
    pytest -n auto tests/integration/tests --ddms-base-url {DDMS_BASE_URL} --url-prefix {URL_PREFIX} --partition {PARTITION} --bearer-token {TOKEN} --cloud-provider {CLOUD_PROVIDER} --domain {DOMAIN}
    ```
- Run/Debug via PyCharm:
  1. Open "Run/Debug Configurations" in the upper right corner.
  2. Click "Edit configuration templates..." in the bottom left corner of the opened window.
  3. Find and expand "Python tests", click "pytest"
  4. Choose "Working directory" as root directory of the project
  5. Fill "Additional Arguments" with -n auto  
     ```
     -n auto --ddms-base-url={DDMS_BASE_URL} --url-prefix={URL_PREFIX} --partition={PARTITION} --bearer-token={token} --domain={DOMAIN}     
     ```
  6. Apply and OK
  7. Use the green arrow next to the test name to run or debug it.

### Integration tests structure

    app
    ├── client
    │   ├── api_client.py               - Client module for making API requests.
    │   └── core                        - Core module containing endpoints and core functionalities.
    └── tests
        ├── integration
        │   ├── data                    - Test data used in integration tests.
        │   ├── helpers                 - Directory containing reusable functions for routine automation.
        │   ├── tests                   - Directory with integration tests.
        │   │   └── conftest.py         - Specific test fixtures shared across different types of tests.
        │   ├── conftest.py             - Main infrastructure fixtures.
        │   ├── config.py               - Configuration file with constants and data file paths.
        │   └── data_provider.py        - Data class to create the final data source for tests.
        ├── test_cache_integration      - Redis cache integration tests (isolated, requires CACHE_ENABLE=True).
        │   └── test_redis_cache.py     - Tests for Redis cache operations with real Redis connection.
        └── test_helpers
            └── cache
                └── test_redis_backend_mocked.py - Unit tests for Redis backend with mocks.


### Run Postman Tests

[The following collection](https://community.opengroup.org/osdu/qa/-/tree/main/Dev/48_CICD_Setup_RAFSDDMSAPI?ref_type=heads) can be used to test RAFS DDMS with Postman.

## Contribution

### Manage package dependencies

If new dependencies were added a new `requirements.txt` file must be generated by:

1. Add new dependencies to requirements.in
2. Run to generate a new requirements.txt file

```shell
pip install pip-tools 
pip-compile requirements.in
```

### Manage package dependencies - Tests

Testing dependencies are separated from the production dependencies.

1. Add new dependencies to `requirements-tests.in`
2. Run to generate a new requirements.txt file

```shell
pip install pip-tools 
pip-compile requirements.in requirements-tests.in -o requirements-tests.txt -v
pip install -r requirements-tests.txt
```

### Code Style Check
There is a list of linters and formatters which are used in this project for code style check.
Mostly it is [flake8](https://flake8.pycqa.org/en/latest/)
with [wemake-python-styleguide extension](https://wemake-python-styleguide.readthedocs.io/en/latest/index.html).

Full list of checkers can be found in [pre-commit config](.pre-commit-config.yaml) file. Configuration for
checkers is in [setup.cfg](setup.cfg) file.

#### Pre-commit Hooks Installation

Pre-commit hooks are supposed to be installed locally.

All requirements for development, tests and pre-commit checks can be installed to your python environment:

```shell
pip-compile requirements.in requirements-tests.in -o requirements-tests.txt -v
pip install -r requirements-tests.txt
```

pre-commit tool should be used inside this environment.

Steps after requirements installation:

```shell
pre-commit install
pre-commit install --hook-type commit-msg
```
Second step is needed for correct gitlint work.

#### Pre-commit Hooks Run
Command to run pre-commit manually for all files:

```shell
pre-commit run --all-files
```

In other cases, all checks run automatically on commit.

## Deployment

* [Main deployment page](./devops/)

### Azure

* [Azure Deployment Instructions - Standard DDMS](./devops/azure/)

### AWS
* AWS recommends the Terraform CLI for DDMS deployments
  * Instructions can be found in the deployment-ddms directory at the root level of the downloaded AWS artifact or in the [aws-terraform-deployment repository](https://community.opengroup.org/osdu/platform/deployment-and-operations/terraform-deployment-aws).
  * Make sure you have selected the branch corresponding to the current release.

### Google
* [Google Deployment Instructions](./devops/gc/deploy)


## Dedicated Blob Storage for Parquet Files

A change request is underway to transition from using the Dataset service for storing Parquet files to a **dedicated blob storage** (bucket or container). This change is being rolled out in phases, with implementation details varying by cloud service provider (CSP). 

Once the implementation is ready for a specific CSP, the feature can be enabled using the following environment variable:  
```bash
USE_BLOB_STORAGE=True
```

### Local Filesystem Support

In addition to the CSP implementations, a class called [`LocalFilesystemBlobStorage`](./app/providers/dependencies/blob_storage.py?ref_type=heads#L148) has been implemented for use with a local filesystem as an alternative to CSP storage. To enable this feature, set the following environment variable:  
```bash
LOCAL_DEV_MODE=True
```

This setup provides flexibility for development and testing environments where CSP integration is not required.

### Azure
* [Blob Storage Docs](./docs/providers/az/readme.md)

## License
Licensed under Apache License Version 2.0; details can be found in [LICENSE](./LICENSE).
