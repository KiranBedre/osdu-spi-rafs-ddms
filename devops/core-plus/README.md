# RAFS-DDMS in Community Implementation (CI) environment

This README describes the **core-plus deployment** of RAFS-DDMS services. This setup is fully cloud-agnostic.  
It is designed for **CI/CD pipelines** and Kubernetes deployments where CSP-specific solutions are not required.

## Container Image

CI/CD pipelines automatically build and push the `cimpl-rafs-ddms` image to **GitLab Container Registry**.  
Helm charts reference this image for deployments.

## Redis Configuration

RAFS DDMS uses Redis for caching and indexing. The Redis configuration for CI deployments is defined in [`devops/core-plus/deploy/values.yaml`](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/devops/core-plus/deploy/values.yaml?ref_type=heads).

## Core Services Configuration

RAFS-DDMS uses **core services** for data handling:

- **dataset** – structured data management  
- **storage** – generic blob/file storage  
- **partition, schema, entitlements** – supporting services  

### Environment Variables

The following environment variables are configured in `values.yaml`:

<details>
<summary><strong>Show environment variables</strong></summary>

```yaml
data:
# Configmaps
  openapiPrefix: "/api/rafs-ddms"
  storageHost: "http://storage"
  searchHost: "http://search"
  partitionHost: "http://partition"
  datasetHost: "http://dataset"
  schemaHost: "http://schema"
  entitlementsHost: "http://entitlements"
  RAFS_USE_BLOB_STORAGE: "False"
  # Redis connection
  cacheEnable: "True"
  cacheBackend: "app.core.helpers.cache.backends.redis_cache.RedisCacheBackend"
  enableApiV1: "True"
  # Update 'redisRafsDdmsHost' var if you want to use external Redis
  redisRafsDdmsHost: ""
  redisRafsDdmsDatabase: "13"
  redisRafsDdmsSsl: "False"
  redisRafsDdmsPort: "6379"
  redisIndexEnable: "True"
  redisRafsDdmsstorageclass: "" # by default for ROSA/OpenShift will be used gp3-csi storage class
  redisRafsDdmsstorage: 1Gi
  # Deployments
  requestsCpu: "50m"
  requestsMemory: "350Mi"
  limitsCpu: "2"
  limitsMemory: "3G"
  redisRequestsCpu: "5m"
  redisRequestsMemory: "50Mi"
  imagePullPolicy: "IfNotPresent"
  serviceAccountName: "rafs-ddms"
  # Cronjob configuration
  cronjobEnabled: true
  cronJobSchedule: "*/5 * * * *"
  cronJobRequestsCpu: "64m"
  cronJobRequestsMemory: "64Mi"
  cronJobLimitsCpu: "100m"
  cronJobLimitsMemory: "128Mi"
  # OAuth configuration for cronjob (to be set in pipeline)
  oauthTokenUrl: "https://keycloak.dev1.osdu-cimpl.opengroup.org/realms/osdu/protocol/openid-connect/token"
  oauthScope: "openid profile offline_access email"
conf:
  configmap: "rafs-ddms-config"
  appName: "rafs-ddms"
  rafsDdmsRedisSecretName: "rafs-ddms-redis-secret"
  cronJobSecretName: "rafs-ddms-cronjob-secret"
  replicas: 1

istio:
  redisProxyCPU: "50m"
  redisProxyMemory: "100Mi"
```

</details>

### CI/CD-Injected Values

During helm upgrade in CI/CD, some values are automatically injected from the pipeline (job cimpl-deploy):

  <details> <summary><strong>Show CI-injected values</strong></summary>

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

## Internal Redis Deployment

- Service Name: redis-rafs-service
- Image: rafs/redis-stack-server:7.4.0-rc2
- Port: 6379
- Authentication: Password-protected (from CI secrets)
- Storage: EmptyDir (ephemeral)
- Resources:
  - Requests: 5m CPU, 50Mi memory
  - Limits: 2 CPU, 5Gi memory

To use an external Redis instance, update REDIS_HOSTNAME and ensure it is accessible from Kubernetes.

## Helm Deployment

Deployment is performed via Helm from CI:

```bash
helm upgrade $CIMPL_SERVICE-deploy oci://$CI_REGISTRY_IMAGE/cimpl-helm/$CIMPL_HELM_PACKAGE_NAME
      --version $CIMPL_HELM_PACKAGE_VERSION-$CIMPL_HELM_TAG
      --install
      --create-namespace
      --namespace=$CIMPL_HELM_NAMESPACE
      --wait
      --history-max=3
      --set global.onPremEnabled=true
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
      --set rosa=true
```

## Cronjobs

- Enabled by default (cronjobEnabled: true)
- Schedule, CPU/memory requests, and limits configured via values.yaml or CI pipeline variables
- OAuth credentials injected by the pipeline (cronJobClientId, cronJobClientSecret)

## QA / Postman Collections

For testing you can use next Postman collections:

- Release collection: [RAFSDDMS API CI-CD v1.0](https://community.opengroup.org/osdu/qa/-/blob/main/Dev/48_CICD_Setup_RAFSDDMSAPI/RAFSDDMS_API_CI-CD_v1.0.postman_collection.json?ref_type=heads)
- Development collection: [RAFS DDMS Development Collection](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/devops/azure/qa/Postman%20Collection/Collection/RAFS%20DDMS.postman_collection.json?ref_type=heads)

[RAFS DDMS Development Collection](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/devops/azure/qa/Postman%20Collection/Collection/RAFS%20DDMS.postman_collection.json?ref_type=heads) is used by default for development and testing purposes

## Notes

- CI/CD pipelines fully manage image builds, helm pacages variable injection, and deployments.
- CSP-specific implementations are **not used**.
- Most configuration should not be manually modified; use pipeline or values.yaml.

## Running Postman collection via Newman

The `cimpl-postman-test` job runs **only when the pipeline is triggered**, specifically when:

- The environment variable `CIMPL` is set to `"1"`

You can also trigger the pipeline manually:

### Manual pipeline execution

To manually start the pipeline, go to the [**CI/CD → Pipelines**](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/pipelines "CI/CD → Pipelines") then click on **New Pipeline** at the top right corner, and then you can launch the pipeline. No additional variables or files are required — the defaults are pre-configured.

### Output and Artifacts

Each job produces:

- 📄 `report-newman.html` – detailed HTML test report in htmlextra format
- 📝 `newman.log` – raw CLI output with full request/response trace

⚠️ If any request in the Postman collection fails, the job is explicitly marked as failed by parsing newman.log for known error patterns. This ensures that testing errors will never be ignored.

📎 Both artifacts (report-newman.html and newman.log) are archived and available for download from the GitLab  CI/CD → Jobs → [Specific Job] → Artifacts.

✅ For convenience, direct links to the artifacts are also echoed at the end of the GitLab job log

### Sensitive data protection

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

### Adding a new Postman collection to CI

To test a new collection:

- Save your Postman collection to:
./devops/azure/qa/Postman Collection/`NEW_COLLECTION_NAME.postman_collection.json`
- Add a new job in `cimpl-newman-test.gitlab-ci.yml`:

  <details> <summary><strong>Show NEW-cimpl-postman-test</strong></summary>

  ```yaml
  NEW-cimpl-postman-test:
    extends: .cimpl_newman_rafs_tests
    variables:
      #Leave as is
      ENVIRONMENT: "./devops/azure/qa/Postman Collection/Environment/OSDU_AZURE_GLAB.postman_environment.json"
      #Should be configured
      COLLECTION_JSON: "./devops/azure/qa/Postman Collection/Collection/NEW_COLLECTION_NAME.postman_collection.json"
      #Can be changed
      REPORT_HTML: "report-newman.html"
  ```

  </details>

- Commit and push your changes, then create a branch starting with `trusted-` – the pipeline will trigger automatically.

### Additional information

Some variables (CLIENT_ID, CLIENT_SECRET, and TENANT_ID) required to run the collection are defined as protected GitLab CI/CD variables and are not included in the Postman environment files for security reasons.

Currently, the following variables are configured in **Settings → CI/CD → Variables**:

- `TEST_EPAM_OPENID_PROVIDER_CLIENT_ID` (maps to `CLIENT_ID`)
- `CIMPL_TEST_EPAM_OPENID_PROVIDER_CLIENT_SECRET` (maps to `CLIENT_SECRET`)
- `CIMPL_TENANT` (maps to `TENANT_ID`)

### Run Postman collections locally using Newman `(without sensitive data protection)`

If you want to test the RAFS-DDMS service on an existing OSDU instance (e.g., CI environment) or any new deployment from your local machine without applying sensitive data masking, you can run Newman directly with the default template:

- By default, the following files are used as inputs for the test:

  ```bash
  # Path to the Postman collection and Postman environment files used for testing
  COLLECTION_JSON="./rafs-ddms-services/devops/azure/qa/Postman Collection/Collection/RAFS DDMS.postman_collection.json"
  ENVIRONMENT="./rafs-ddms-services/devops/azure/qa/Postman Collection/Environment/OSDU_AZURE_GLAB.postman_environment.json"
  ```

- Linux / macOS (bash)

  ```bash
  # Install required tools
  sudo apt update
  npm install -g newman newman-reporter-htmlextra

  # Clone test collections
  git clone https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services.git

  # Run tests locally
  COLLECTION_JSON="./rafs-ddms-services/devops/azure/qa/Postman Collection/Collection/RAFS DDMS.postman_collection.json"
  ENVIRONMENT="./rafs-ddms-services/devops/azure/qa/Postman Collection/Environment/OSDU_AZURE_GLAB.postman_environment.json"
  REPORT_HTML: "report-newman.html"
  newman run "$COLLECTION_JSON" \
      -e "$ENVIRONMENT" \
      --env-var "TENANT_ID=<your-tenant-id>" \
      --env-var "CLIENT_ID=<your-client-id>" \
      --env-var "CLIENT_SECRET=<your-client-secret>" \
      --env-var "HOSTNAME=osdu.dev1.osdu-cimpl.opengroup.org" \
      --env-var "Token_Fetch_URL=https://keycloak.dev1.osdu-cimpl.opengroup.org/realms/osdu/protocol/openid-connect/token" \
      --env-var "auth_url=https://accounts.google.com/o/oauth2/auth" \
      --env-var "cloud_platform=GCP" \
      --env-var "domain=.group" \
      --env-var "data-partition-id=osdu" \
      --env-var "Scope=openid profile offline_access email" \
      --reporters cli,htmlextra \
      --reporter-htmlextra-export "report-newman.html" \
      --reporter-htmlextra-title "RAFS DDMS API Tests" \
      --reporter-htmlextra-hideRequestBody "Refresh Token" \
      --insecure 2>&1 | tee newman.log

👉 The execution will produce two files in the current working directory:

- `report-newman.html` – full HTML test report (displaying all request/response data, including headers and key elements with sensitive data)
- `newman.log` – complete execution logs

⚠️ Security note. When running Newman locally without sensitive data protection:

- Bearer tokens, client_secret, and access_token values will be visible in the generated outputs.
- These files should never be shared, committed, or uploaded to any repository or artifact storage.
- Use this mode only in local experiments where you fully control the environment and outputs.
