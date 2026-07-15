# Deploy the Service Helm Chart

This guide provides instructions on deploying a Helm Chart on a [Kubernetes](https://kubernetes.io) cluster using the [Helm](https://helm.sh) package manager.

## Prerequisites

Tests for the code were performed on a **Kubernetes cluster** (v1.26.6) with **Istio** (1.13.3).
> It is possible to use other versions, but it hasn't been tested.

### Compatible Operating Systems

The code works on Debian-based Linux distributions (Debian 10 and Ubuntu 20.04) and Windows WSL2.

Other operating systems, including macOS, have not been verified and are currently unsupported.

## Scope Clarification

This repository contains only RAFS components.

RAFS depends on several OSDU Core services (Search, Storage, Entitlements, Partition, IAM, etc.).
These services are expected to be available in the target environment.
Their deployment and configuration are outside the scope of this repository.

Local deployment of RAFS includes only RAFS-specific components.
Running a full OSDU Core stack locally is technically possible but is not supported or documented here.

### Required Packages

Install these tools on the machine from which deployment will be executed:

- **Helm** (v3.9.3 or higher) [helm](https://helm.sh/docs/intro/install/)

- **Kubectl** (v1.26.0 or higher) [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl)

## Installation

Use any code editor to set variables in the **values.yaml** file. Some of the values are prefilled. However, you'll need to specify some values as well. Detailed information about these variables is provided below.

### Global Variables

| Name | Description | Type | Default |Required |
|------|-------------|------|---------|---------|
| **global.domain** | your domain for an external endpoint, ex `example.com` | string | `-` | yes |
| **global.dataPartitionId** | Partition identifier for deployment | string | `-` | yes |
| **global.onPremEnabled** | whether on-prem is enabled | boolean | `false` | yes |
| **global.limitsEnabled** | whether CPU and memory limits are enabled | boolean | `true` | yes |
| **global.RAFS_URI** | Base RAFS service URI | string | `-` | yes |

### Application-Level Configuration (conf.*)

| Name | Description | Type | Default |Required |
|------|-------------|------|---------|---------|
| **conf.appName** | Service name | string | `rafs-ddms` | yes |
| **conf.replicas** | Number of replicas for the application k8s deployment | string | `1` | yes |
| **conf.configmap** | configmap to be used | string | `rafs-ddms-config` | yes |
| **conf.serviceAccountName** | Service account name | string | `rafs-ddms` | yes |
| **conf.rafsDdmsRedisSecretName** | rafs-ddms redis secret | string | `rafs-ddms-redis-secret` | yes |
| **conf.cronJobSecretName** | cronjob OAuth credentials secret | string | `rafs-ddms-cronjob-secret` | no |

### Data Section (data.*)

#### Images (set in CI job .cimpl_substitute_service_and_cronjob_images_in_helm)

| Name | Description | Type | Default |Required |
|------|-------------|------|---------|---------|
| **data.image** | Service image | string | `""` | yes |
| **data.redisImage** | Redis instance image | string | `""` | yes |
| **data.cronJobImage** | Cronjob image | string | `""` | only if cronjobEnabled=true |
| **data.imagePullPolicy** | when to pull image | string | `IfNotPresent` | yes |

#### Resource Requests / Limits

##### Application container

| Name | Description | Type | Default |Required |
|------|-------------|------|---------|---------|
| **data.requestsCpu** | amount of requested CPU | string | `5m` | yes |
| **data.requestsMemory** | amount of requested memory| string | `350Mi` | yes |
| **data.limitsCpu** | CPU limit | string | `2` | only if `global.limitsEnabled` is true |
| **data.limitsMemory** | memory limit | string | `3G` | only if `global.limitsEnabled` is true |

##### Redis instance

| Name | Description | Type | Default |Required |
|------|-------------|------|---------|---------|
| **data.redisRequestsCpu** | amount of requested CPU for Redis instance | string | `5m` | yes |
| **data.redisRequestsMemory** | amount of requested memory for Redis instance | string | `50Mi` | yes |

##### CronJob

| Name | Description | Type | Default |Required |
|------|-------------|------|---------|---------|
| **data.cronJobRequestsCpu** | CPU request for cronjob | string | `64m` | no |
| **data.cronJobRequestsMemory** | Memory request for cronjob | string | `64Mi` | no |
| **data.cronJobLimitsCpu** | CPU limit for cronjob | string | `100m` | no |
| **data.cronJobLimitsMemory** | Memory limit for cronjob | string | `128Mi` | no |

### Environment Configuration (set by CI job cimpl-deploy)

| Name | Description | Type | Default |Required |
|------|-------------|------|---------|---------|
| data.logLevel | Application log level | string | `""` | yes |
| data.bucketPrefix | Prefix for buckets | string | `""` | yes |
| data.groupId | Group identifier | string | `""` | yes |
| data.sharedTenantName | Shared tenant name | string | `""` | yes |
| data.bucketName | Storage bucket name | string | `""` | yes |

### Service & Host Configuration (ConfigMap)

| Name | Description | Type | Default |Required |
|------|-------------|------|---------|---------|
| **data.openapiPrefix** | OpenAPI prefix | string | `/api/rafs-ddms` | yes |
| **data.storageHost** | Storage service host | string | `http://storage` | yes |
| **data.searchHost** | Search service host | string | `http://search` | yes |
| **data.partitionHost** | Partition service host | string | `http://partition` | yes |
| **data.datasetHost** | Dataset service host | string | `http://dataset` | yes |
| **data.schemaHost** | Schema service host | string | `http://schema` | yes |
| **data.entitlementsHost** | Entitlements service host | string | `http://entitlements` | yes |
| **data.RAFS_USE_BLOB_STORAGE** | Schema service host | string | `http://dataset` | yes |
| **data.enableApiV1** | Deployment flag to enable api V1 | string | `True` | yes |

### Redis Configuration

| Name | Description | Type | Default |Required |
|------|-------------|------|---------|---------|
| **data.redisRafsDdmsHost** | Redis instance host. If empty, Helm installs an internal Redis instance | string | `""` | yes |
| **data.redisRafsDdmsPort** | Redis instance port | string | `6379` | yes |
| **data.redisRafsDdmsDatabase** | Redis database number | string | `13` | yes |
| **data.redisRafsDdmsSsl** | Enable SSL for external Redis instance. For Redis inside k8s - should be `False` | string | `False` | yes |
| **data.redisIndexEnable** | Enable redis index | bool | `True` | yes |
| **redisRafsDdmsstorageclass** | string | `""` | by default for ROSA/OpenShift will be used gp3-csi storage class |
| **data.cacheEnable** | Enable or disable cache for the application | string | `True` | yes |
| **data.cacheBackend** | Path to your backend, which is used to initialize FastAPICache | string | `app.core.helpers.cache.backends.redis_cache.RedisCacheBackend` | yes |

### CronJob Section

| Name | Description | Type | Default |Required |
|------|-------------|------|---------|---------|
| **cronjobEnabled** | Enable CronJob | bool | `True` | yes |
| **data.cronJobSchedule** | Cron schedule for indexer trigger | string | `0 2 * * *` | no |
| **data.oauthTokenUrl** | OAuth token endpoint URL | string | `https://keycloak.dev1.osdu-cimpl.opengroup.org/realms/osdu/protocol/openid-connect/token` | only if cronJobImage is set |
| **data.oauthScope** | OAuth scope | string | `openid profile offline_access email` | only if cronJobImage is set |

CronJob OAuth credentials are read from Kubernetes Secret `conf.cronJobSecretName` (`rafs-ddms-secret` by default),
which is created by infra-bootstrap. The client ID is fixed to dedicated Keycloak client `rafs-ddms`.

### Istio Variables

| Name | Description | Type | Default |Required |
|------|-------------|------|---------|---------|
| **istio.redisProxyCPU** | CPU request for Envoy sidecars for Redis instance pod | string | `50m` | yes |
| **istio.redisProxyMemory** | memory request for Envoy sidecars for Redis instance pod | string | `100Mi` | yes |

### Installing the Helm Chart

To install the Helm Chart, run the following command from within this directory:

```bash
helm install core-plus-rafs-ddms-deploy .
```

## Uninstalling the Helm Chart

To uninstall the Helm deployment, execute the following command:

```bash
helm uninstall core-plus-rafs-ddms-deploy
```

> Remember to delete all relevant Kubernetes secrets and/or PVCs after uninstalling the Service.
