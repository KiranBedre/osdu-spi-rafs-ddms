# RAFS-DDMS on Community Implementation (CI) Environment

This README describes the **core-plus deployment** of RAFS-DDMS services in a **CI/CD-driven Kubernetes environment**.  
The deployment is designed to be fully **parameterized**, optimized for **CI/CD pipelines**, and easily maintainable across multiple environments.  

While the setup is **cloud-agnostic** and works on standard Kubernetes clusters, it is also compatible with **OpenShift**, with minor platform-specific adjustments (such as StorageClass and security settings).  
This allows teams to deploy RAFS-DDMS consistently across both vanilla Kubernetes and OpenShift-based infrastructures without modifying the core Helm charts.

[[_TOC_]]

## Container Image

CI/CD pipelines automatically build and push the `cimpl-rafs-ddms` image to the **GitLab Container Registry**.  
Helm charts reference this image for deployments.

---

## Core Services Configuration

RAFS-DDMS relies on **core services**:

- **dataset** – structured data management  
- **storage** – generic blob/file storage  
- **partition, schema, entitlements** – supporting services  

### Environment Variables

Environment variables are defined in [values.yaml](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/devops/core-plus/deploy/values.yaml?ref_type=heads) and injected via the pipeline:

<details>
<summary><strong>Show environment variables</strong></summary>

```yaml
data:
  # --------------------
  # Environment configuration (to be set in pipeline by job "cimpl-deploy")
  # --------------------
  logLevel: ""
  bucketPrefix: ""
  groupId: ""
  sharedTenantName: ""
  bucketName: ""
  # Configmap 
    ## Hosts
  openapiPrefix: "/api/rafs-ddms"
  storageHost: "http://storage"
  searchHost: "http://search"
  partitionHost: "http://partition"
  datasetHost: "http://dataset"
  schemaHost: "http://schema"
  entitlementsHost: "http://entitlements"
    # Features
  RAFS_USE_BLOB_STORAGE: "False"
  enableApiV1: "True"
```

</details>

## Redis Configuration

Redis is used for caching and indexing. CI deployments configure Redis via [values.yaml](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/devops/core-plus/deploy/values.yaml?ref_type=heads):

<details> <summary><strong>Show Redis variables</strong></summary>

```yaml
data:
  # --------------------
  # Redis Configuration
  # --------------------
  redisRafsDdmsHost: "" # Update var if you want to use external Redis
  redisRafsDdmsPort: "6379"
  redisRafsDdmsDatabase: "13"
  redisRafsDdmsSsl: "False"
  redisIndexEnable: "True"
  redisRafsDdmsstorageclass: "" # by default for ROSA/OpenShift will be used gp3-csi storage class
  redisRafsDdmsstorage: 1Gi
  
  cacheEnable: "True"
  cacheBackend: "app.core.helpers.cache.backends.redis_cache.RedisCacheBackend"
```

</details>

## Deployment

### Helm Deployment

Deployments are managed via the [cimpl-deploy](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/devops/core-plus/override-stages.yml?ref_type=heads) job of the CI pipeline:

<details> <summary><strong>Show cimpl-deploy job</strong></summary>

```yaml
helm upgrade $CIMPL_SERVICE-deploy oci://$CI_REGISTRY_IMAGE/cimpl-helm/$CIMPL_HELM_PACKAGE_NAME \
  --version $CIMPL_HELM_PACKAGE_VERSION-$CIMPL_HELM_TAG \
  --install \
  --create-namespace \
  --namespace=$CIMPL_HELM_NAMESPACE \
  --wait \
  --history-max=3 \
  --set global.onPremEnabled=true \
  --set global.domain=$CIMPL_DOMAIN \
  --set global.dataPartitionId=osdu \
  --set global.RAFS_URI=$CIMPL_TENANT.$CIMPL_DOMAIN \
  --set data.serviceAccountName=$CIMPL_SERVICE \
  --set data.cronJobClientId=$TEST_EPAM_OPENID_PROVIDER_CLIENT_ID \
  --set data.cronJobClientSecret=$CIMPL_TEST_EPAM_OPENID_PROVIDER_CLIENT_SECRET \
  --set data.logLevel=INFO \
  --set data.bucketPrefix="refi" \
  --set data.groupId=$GROUP_ID \
  --set data.sharedTenantName=$CIMPL_TENANT \
  --set data.googleCloudProject=$CIMPL_PROJECT \
  --set data.bucketName=$CIMPL_POLICY_BUCKET \
  --set data.subscriberPrivateKeyId=$CIMPL_SUBSCRIBER_PRIVATE_KEY_ID \
  --set rosa=true
```

</details>

### Internal Redis Deployment

- Service Name: redis-rafs-service
- Image: rafs/redis-stack-server:7.4.0-rc2
- Port: 6379
- Authentication: password from CI secrets
- Storage: EmptyDir (ephemeral)
- Resources:
  - Requests: 5m CPU, 50Mi memory
  - Limits: 2 CPU, 5Gi memory

To use an external Redis instance, update REDIS_HOSTNAME in [values.yaml](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/devops/core-plus/deploy/values.yaml?ref_type=heads) and ensure accessibility from Kubernetes.

### CI/CD-Injected Values

Some values are injected automatically during the helm upgrade:

<details> <summary><strong>Show CI/CD-injected values</strong></summary>

```yaml
--set global.domain=$CIMPL_DOMAIN
--set global.dataPartitionId=osdu
--set global.RAFS_URI=$CIMPL_TENANT.$CIMPL_DOMAIN
--set data.serviceAccountName=$CIMPL_SERVICE
--set data.cronJobClientId=$TEST_EPAM_OPENID_PROVIDER_CLIENT_ID
--set data.cronJobClientSecret=$CIMPL_TEST_EPAM_OPENID_PROVIDER_CLIENT_SECRET
--set data.logLevel=INFO
--set data.bucketPrefix="refi"
--set data.groupId=$GROUP_ID
--set data.sharedTenantName=$CIMPL_TENANT
--set data.googleCloudProject=$CIMPL_PROJECT
--set data.bucketName=$CIMPL_POLICY_BUCKET
--set data.subscriberPrivateKeyId=$CIMPL_SUBSCRIBER_PRIVATE_KEY_ID
```

</details>

This ensures that deployments are fully parameterized and environment-specific, without hardcoding values in values.yaml.

## OpenTelemetry Integration

RAFS DDMS supports OpenTelemetry (OTEL) for distributed tracing, metrics, and log correlation. The integration is based on the [opentelemetry-distro](https://pypi.org/project/opentelemetry-distro/) package, which is included in the container image and can be activated via runtime arguments — analogous to the Java agent approach used in other OSDU services (e.g. `JAVA_TOOL_OPTIONS=-javaagent:...` for Java services).

This provides critical observability features:

* **Distributed tracing:** Traces the path of requests as they travel across different services.
* **Metrics:** Captures performance indicators and application-level metrics.
* **Logs:** Correlates logs with traces and other telemetry data.

Enabling the agent makes it significantly easier to monitor, debug, and manage the application in development and production environments.

### Environment Variables

| Variable | Example | Description | Required |
|---|---|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://127.0.0.1:4318` | OpenTelemetry collector endpoint | no |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` | OpenTelemetry collector protocol. Python uses `http/protobuf` (port 4318); `grpc` requires the `grpcio` C-extension which is not bundled. | no |
| `PYTHON_TOOL_OPTIONS` | `opentelemetry-instrument` | Extends runtime arguments to enable the OpenTelemetry agent. When set, the agent instruments the application automatically without code changes. | no |

### Activation

The agent is activated by setting the `PYTHON_TOOL_OPTIONS` environment variable to any non-empty value. When the variable is empty (default), the application starts without instrumentation.

#### Per-worker TracerProvider initialisation

Each uvicorn worker process creates its own `TracerProvider` and `OTLPSpanExporter` on startup.  This is intentional: after `os.fork()`, HTTP connection pools are shared between parent and child, which leads to silent export failures.  By creating a fresh exporter in every worker the problem is avoided.

The startup sequence in `app/core/events.py`:

| `restart_otel_span_processors()` result | Startup behaviour |
|---|---|
| `True` — export thread was restarted | Worker keeps the existing `TracerProvider`; no new init needed |
| `False` — no live thread found (fresh fork, no provider yet, or agent owns fork recovery) | `initialize_tracer()` creates a fresh per-worker `TracerProvider` and `OTLPSpanExporter` |

When `PYTHON_TOOL_OPTIONS` is set the `opentelemetry-instrument` agent instruments libraries (FastAPI, HTTPX) in the master process before fork.  Workers inherit the instrumentation patches but each worker calls `initialize_tracer()` to own its own export pipeline, so the agent's master-process provider is superseded per worker.

In Helm deployments (`values.yaml`):

```yaml
data:
  pythonToolOptions: "opentelemetry-instrument"
  otelExporterEndpoint: "http://otel-collector.observability.svc.cluster.local:4318"
  otelExporterProtocol: "http/protobuf"
```

For local testing with Docker:

```bash
docker run \
  -e PYTHON_TOOL_OPTIONS="opentelemetry-instrument" \
  -e OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318" \
  -e OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf" \
  rafs-ddms:latest
```

### CI/CD Pipeline Variables

OTEL is enabled via the `CIMPL_OTEL_PYTHON_TOOL_OPTIONS` CI variable defined in [override-stages.yml](./override-stages.yml):

```yaml
CIMPL_OTEL_PYTHON_TOOL_OPTIONS: opentelemetry-instrument
```

This value is passed to Helm during deployment:

```yaml
--set data.pythonToolOptions=$CIMPL_OTEL_PYTHON_TOOL_OPTIONS
--set data.otelExporterEndpoint=$CIMPL_OTEL_PYTHON_EXPORTER_ENDPOINT
--set data.otelExporterProtocol=$CIMPL_OTEL_PYTHON_EXPORTER_PROTOCOL
```

All three variables are defined locally in [override-stages.yml](./override-stages.yml) and hardcoded to use the HTTP/protobuf exporter on port 4318 (Python cannot use the gRPC exporter without adding `grpcio` as a C-extension dependency).

---

## Cronjobs

- Enabled by default (cronjobEnabled: true)
- Schedule, CPU/memory requests, and limits configurable via [values.yaml](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/devops/core-plus/deploy/values.yaml?ref_type=heads) or CI variables
- OAuth credentials injected by the pipeline (cronJobClientId, cronJobClientSecret)

## QA / Postman Collections / Postman Environment

Available collections:

- Release collection: [RAFSDDMS API CI-CD v1.0](https://community.opengroup.org/osdu/qa/-/blob/main/Dev/48_CICD_Setup_RAFSDDMSAPI/RAFSDDMS_API_CI-CD_v1.0.postman_collection.json?ref_type=heads)
- Development collection: [RAFS DDMS Development Collection](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/devops/core-plus/qa/Postman%20Collection/Collection/RAFS%20DDMS.postman_collection.json?ref_type=heads) (is used by default for development and testing purposes)

Import the Collection into Postman

- Download or copy the provided [Postman collection file](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/devops/core-plus/qa/Postman%20Collection/Collection/RAFS%20DDMS.postman_collection.json?ref_type=heads)

- Download Development and test Environment: [RAFS DDMS Environment file](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/devops/core-plus/qa/Postman%20Collection/Environment/OSDU_CI.postman_environment.json?ref_type=heads) (is used by default for development and testing purposes on Community implementation (CI) env)

- Open Postman and follow the official guide to import the collection: [Importing and Exporting Data in Postman](https://learning.postman.com/docs/getting-started/importing-and-exporting/importing-and-exporting-overview/)

Tests for Rock and Fluid are located inside the same collection, but are organized into separate folders.

### Location of Test Suites

The folders relevant for Rock & Fluid testing are:

- RAFS DDMS
  - v2
    - Simulation Rock Physics
    - Saturation Function Set

**Note:** Tests for the Fluid data type are still under development and will be added later.

### Folder Structure

Each new type contains two main subfolders:

- Positive - These tests demonstrate the expected behavior and can be used as a reference flow.
- Negative - Negative scenarios are split into folders per endpoint. Each folder contains tests validating error behavior

### How to Start Testing

Before running any positive or negative tests, you must initialize the collection.

- Set required variables
- Run the folder: Configure collection
This folder contains a request that prepares authentication and environment variables for the collection.

## Running Postman Collections via Newman

The `cimpl-postman-test` job runs **only when the pipeline is triggered**, specifically when:

- The environment variable `CIMPL` is set to `"1"`

### Manual Pipeline Execution

Trigger manually via [CI/CD → Pipelines → New Pipeline](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/pipelines "CI/CD → Pipelines"). Defaults are pre-configured

### Output and Artifacts

Each job produces:

- 📄 `report-newman.html` – detailed HTML test report in htmlextra format
- 📝 `newman.log` – raw CLI output with full request/response trace

⚠️ If any request in the Postman collection fails, the job is explicitly marked as failed by parsing newman.log for known error patterns. This ensures that testing errors will never be ignored.

📎 Both artifacts (report-newman.html and newman.log) are archived and available for download from the GitLab  CI/CD → Jobs → [Specific Job] → Artifacts.

✅ For convenience, direct links to the artifacts are also echoed at the end of the GitLab job log

### Sensitive Data Protection

To prevent accidental leaks of confidential information (such as Bearer tokens or client secrets) in reports:

- Custom Newman HTML template is generated at runtime.
- The Request Description section is removed, as it may contain sensitive data.
- The template is removed at the end of the job.
- Redaction of sensitive fields via htmlextra options:
  - --reporter-htmlextra-skipHeaders "Authorization"
  - --reporter-htmlextra-hideRequestBody "Refresh Token"
  - --reporter-htmlextra-hideResponseBody "Refresh Token"
- Automated post-scan of the report (report-newman.html) searches for known secret patterns (e.g., Bearer tokens, client_secret, access_token). If any matches are found, the job fails with a clear error message.
This ensures that even if a confidential value gets into the report, the pipeline will block its publication.

### Adding a New Postman Collection to CI

To use the new collection for testing:

- Save your Postman collection to:
./devops/core-plus/qa/Postman Collection/`NEW_COLLECTION_NAME.postman_collection.json`
- Add a new job in `cimpl-newman-test.gitlab-ci.yml`:

  <details> <summary><strong>Show NEW-cimpl-postman-test</strong></summary>

  ```yaml
  NEW-cimpl-postman-test:
    extends: .cimpl_newman_rafs_tests
    variables:
      # Leave as is
      ENVIRONMENT: "./devops/core-plus/qa/Postman Collection/Environment/OSDU_CI.postman_environment.json"
      # Collection name should be configured
      COLLECTION_JSON: "./devops/core-plus/qa/Postman Collection/Collection/NEW_COLLECTION_NAME.postman_collection.json"
      # Can be changed
      REPORT_HTML: "report-newman.html"
  ```

  </details>

  - Commit, push, and create a trusted-* branch to trigger the pipeline.

  ### Running Postman Collections Locally `(without sensitive data protection)`

If you want to test the RAFS-DDMS service on an existing OSDU instance (e.g., CI environment) or any new deployment from your local machine without applying sensitive data masking, you can run Newman directly with the default template:

- By default, the following files are used as inputs for the test:

  ```bash
  # Path to the Postman collection and Postman environment files used for testing
  COLLECTION_JSON="./rafs-ddms-services/devops/core-plus/qa/Postman Collection/Collection/RAFS DDMS.postman_collection.json" # change the path to the postman collection file if you want to test your own collection
  ENVIRONMENT="./rafs-ddms-services/devops/core-plus/qa/Postman Collection/Environment/OSDU_CI.postman_environment.json"
  ```

- Linux / macOS (bash)

  ```bash
  # Install required tools
  sudo apt update
  npm install -g newman newman-reporter-htmlextra

  # Clone rafs-ddms repo with test collections
  git clone https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services.git

  # Run tests locally
  COLLECTION_JSON="./rafs-ddms-services/devops/core-plus/qa/Postman Collection/Collection/RAFS DDMS.postman_collection.json"
  ENVIRONMENT="./rafs-ddms-services/devops/core-plus/qa/Postman Collection/Environment/OSDU_CI.postman_environment.json"
  newman run "$COLLECTION_JSON" \
      -e "$ENVIRONMENT" \
      --env-var "TENANT_ID=<your-tenant-id>" \
      --env-var "CLIENT_ID=<your-client-id>" \
      --env-var "CLIENT_SECRET=<your-client-secret>" \
      --reporters cli,htmlextra \
      --reporter-htmlextra-export "report-newman.html" \
      --reporter-htmlextra-title "RAFS DDMS API Tests" \
      --reporter-htmlextra-hideRequestBody "Refresh Token" \
      --insecure 2>&1 | tee newman.log

The execution will produce two files in the current working directory:

- `report-newman.html` – full HTML test report (displaying all request/response data, including headers and key elements with sensitive data)
- `newman.log` – complete execution logs

⚠️ Security note. When running Newman locally without sensitive data protection:

- Bearer tokens, client_secret, and access_token values will be visible in the generated outputs.
- These files should never be shared, committed, or uploaded to any repository or artifact storage.
- Use this mode only in local experiments where you fully control the environment and outputs.

## Notes

- CI/CD pipelines manage builds, Helm packaging, variable injection, and deployments
- CSP-specific implementations are not used
- Most configuration should be modified only via pipeline or values.yaml

## Additional information

Some variables (CLIENT_ID, CLIENT_SECRET, and TENANT_ID) required to run the collection are defined as protected GitLab CI/CD variables and are not included in the Postman environment files for security reasons.

Currently, the following variables are configured in **Settings → CI/CD → Variables**:

- `TEST_EPAM_OPENID_PROVIDER_CLIENT_ID` (maps to `CLIENT_ID`)
- `CIMPL_TEST_EPAM_OPENID_PROVIDER_CLIENT_SECRET` (maps to `CLIENT_SECRET`)
- `CIMPL_TENANT` (maps to `TENANT_ID`)
