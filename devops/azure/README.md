# RAFSDDMS on Azure

[[_TOC_]]

## Build image

**WARN** It is recommended to use the [distroless](../../Dockerfile) image for production systems, which it is more secure and lighter than develop and test images.

```shell
az login
az acr build --registry <acr-name> --file ./Dockerfile -t rafsddms:latest .
```

## Redis Configuration

RAFS DDMS uses Redis for caching and indexing. The Redis configuration for Azure deployments is defined in `devops/azure/values.yaml`.

### Environment Variables

The following Redis environment variables are configured in the Helm values (see `devops/azure/values.yaml` lines 56-63):

```yaml
CACHE_ENABLE: "True"
CACHE_BACKEND: "app.core.helpers.cache.backends.redis_cache.RedisCacheBackend"
REDIS_HOSTNAME: redis-rafs-service  # Internal Kubernetes service name
REDIS_PASSWORD: redispass           # Default password (overridden by KeyVault)
REDIS_DATABASE: "13"
REDIS_SSL: "False"                  # Internal Redis doesn't use SSL
REDIS_PORT: "6379"
REDIS_INDEX_ENABLE: "True"
```

### Azure KeyVault Integration

For production deployments, Redis credentials are pulled from Azure KeyVault (see `devops/azure/values.yaml` lines 11-14):

```yaml
azure:
  keyvault:
    secrets:
    - key: redis-host      # KeyVault secret name
      obj: redis-hostname  # Maps to REDIS_HOSTNAME env var
    - key: redis-pass      # KeyVault secret name
      obj: redis-password  # Maps to REDIS_PASSWORD env var
```

**Note:** KeyVault secrets take precedence over hardcoded values in the configmap for production security.

### Internal Redis Deployment

An internal Redis instance is deployed alongside RAFS DDMS (see `devops/azure/values.yaml` lines 81-110):

- **Service Name**: `redis-rafs-service`
- **Image**: `rafs/redis-stack-server:7.4.0-rc2`
- **Port**: `6379`
- **Authentication**: Password-protected (from KeyVault secret `redis-pass`)
- **Storage**: EmptyDir volume (ephemeral)
- **Resources**:
  - Requests: 128m CPU, 4Gi memory
  - Limits: 300m CPU, 6Gi memory

**To use external Redis instead:** Update `REDIS_HOSTNAME` in your deployment values and ensure the external Redis is accessible from the AKS cluster.

## Installation

Using [helm-charts-azure/standard-ddms](https://community.opengroup.org/osdu/platform/deployment-and-operations/helm-charts-azure/-/tree/master/osdu-ddms/standard-ddms) for simplicity.

### AKS Install Process

#### Chart Parameters

There are instance specific parameters within Helm chart:

| Parameter             | Description                                           |
| --------------------- | ----------------------------------------------------- |
| <azure_tenant>        | Azure Tenant of Compute RG                            |
| <azure_subscription>  | Azure Subscription of Compute RG                      |
| <azure_resourcegroup> | Name of Compute RG                                    |
| <azure_identity>      | Name of MSI that is used by Pods in AKS               |
| <azure_identity_id>   | ID of MSI                                             |
| <azure_keyvault>      | Name of KeyVault in Compute RG with platform secrets  |
| <azure_appid>         | ...                                                   |
| <azure_acr>           | Name of Azure Container Registry with Images to use   |
| <ingress_dns>         | DNS name associated with the Instance                 |

Following instruction show general process of using Standard Helm for deployment of particular services.

```bash
UNIQUE=<uniquename> # I.E glab

ingress_dns='...' # kubectl get ingress -n osdu-azure / kubectl get virtualservice -n istio-system
azure_acr='<acr.domain.name>' # The acr name I.E osdumvpcr{{company}}ajlhcr.azurecr.io
GROUP=$(az group list --query "[?contains(name, 'cr${UNIQUE}')].name" -otsv)
ENV_VAULT=$(az keyvault list --resource-group $GROUP --query [].name -otsv)
HELM_DDMS_VERSION=<1.18.0>  # It started with standard-ddms 1.18.0, however, it should be the last one

azure_tenant=$(az keyvault secret show --id https://${ENV_VAULT}.vault.azure.net/secrets/tenant-id --query value -otsv)
azure_subscription=$(az keyvault secret show --id https://${ENV_VAULT}.vault.azure.net/secrets/subscription-id --query value -otsv)
azure_resourcegroup=$(az keyvault secret show --id https://${ENV_VAULT}.vault.azure.net/secrets/base-name-cr --query value -otsv)-rg
azure_identity=$(az keyvault secret show --id https://${ENV_VAULT}.vault.azure.net/secrets/base-name-cr --query value -otsv)-osdu-identity
azure_identity_id=$(az keyvault secret show --id https://${ENV_VAULT}.vault.azure.net/secrets/osdu-identity-id --query value -otsv)

ddms='rafs'
namespace='ddms-rafs'
azure_keyvault=$ENV_VAULT

# Make sure you are on the correct subscription and connected to the right AKS.
az account set --subscription $azure_subscription
az aks get-credentials --resource-group $azure_resourcegroup --name <azure_kubernetese_service>
```

Rafdms has its own values file, dry run template

```bash
helm template "oci://msosdu.azurecr.io/helm/standard-ddms" --version ${HELM_DDMS_VERSION} -f devops/azure/values.yaml
```

Install the helm chart.

```bash
# Create K8S Namespace with configured Istio sidecar ingejction
kubectl create namespace $namespace && \
kubectl label namespace $namespace istio-injection=enabled

# Example of deployment for Wellbore DDMS
helm upgrade -i ${ddms}-services "oci://msosdu.azurecr.io/helm/standard-ddms" --version ${HELM_DDMS_VERSION} -n $namespace \
  -f devops/azure/values.yaml \
  --set azure.tenant=$azure_tenant \
  --set azure.subscription=$azure_subscription \
  --set azure.resourcegroup=$azure_resourcegroup \
  --set azure.identity=$azure_identity \
  --set azure.identity_id=$azure_identity_id \
  --set azure.keyvault.name=$azure_keyvault \
  --set azure.acr=$azure_acr \
  --set ingress.dns=$ingress_dns \
  --set configuration[0].container.image=rafsddms \
  --set configuration[0].container.tag=latest --debug
```

## Azure Container

A [Merge Request !973](https://community.opengroup.org/osdu/platform/deployment-and-operations/infra-azure-provisioning/-/merge_requests/973/diffs) has been merged into the **infra-azure-provisioning** repository. However, assurance is needed to confirm that the container `rafs-ddms` has been successfully created.

## Additional Notes for Azure

### Compatibility / Portability

- `Metrics`: Prometheus is implemented for Azure only; not mandatory for other CSPs.
- `AzureBlobHandler`: Handles uploads/downloads to Azure Storage using pre-signed URLs. Can be replaced by standard HTTP PUT/GET for other CSPs.
- `Redis`: Optional, standard Redis parameters; no CSP-specific customization required.

**NOTE: Distroless dockerfile compatibility** - RAFS project borned with the higher security standards, we developed distroless dockerfile definition, which uses the `msosdu` registry as public registry to get the distroless and python images, nonetheless, this public image it is not CSP's specific, only to avoid using external (and some times unavailable) registries such as `cgr.dev/chainguard/` or to prevent hitting the download limit from `docker.io`.

### Resiliency / Availability

- RAFS generate lots of requests to storage, schema and search services for schema and reference data validation.
  - If **policy service** it is enabled, it is recommended to increase the availability of the entitlements services as this is highly used by policy service as well as legal. We had noticed that by using entitlements separated service helps to aleviate the delay/load in policy service.
  - [Uviloop](https://www.uvicorn.org/#quickstart) it is intended to increase the performance and lower the pod resources consumption, however, we hadn't measure this yet.
- Integration tests can be executed in `auto` mode, nevertheless this will generate large ammount of async request to core services (mostly storage service). If storage backend it is not configured correctly it might fail randomly.
  - To overcome this in azure side, we increased the CosmosDB throughput (for storage and entitlements).
  - We needed to scale vertically storage service.
  - Needed to increase replicas at AGIC.
  - Improved the policy service docker image for azure.

### Monitoring Customization

- FastAPI Prometheus controller onboarded in Azure deployment, more information can be found on the [prometheus use-case implementation](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/tree/main/devops/azure/monitoring)
- Can configure metrics per CSP via [app/providers/helpers/metrics](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/app/providers/helpers/metric.py)

### Readiness Feature

`SERVICE_READINESS_URLS` defines dependent services for liveness/readiness checks.

Example:

```shell
SERVICE_READINESS_URLS="http://storage/api/storage/v2/liveness_check,http://schema/api/schema-service/v1/liveness_check"
```

**NOTE** This is an optional feature, omit setting up `SERVICE_READINESS_URLS` env var if don't need to use it at all.

### Security

- Leveraged authentication and authorization to the istio envoy CSP specific implementation.
- RAFS does not require any additional or privileged service accounts, it will proxy the access_token as it is to the proper OSDU core services.
- `[Optional]` Azure implementation disables auth in swagger endpoints.
- Distroless production ready docker image [Dockerfile](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/Dockerfile)
