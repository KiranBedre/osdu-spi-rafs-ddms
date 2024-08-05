# Deploy the Service Helm Chart

This guide provides instructions on deploying a Helm Chart on a [Kubernetes](https://kubernetes.io) cluster using the [Helm](https://helm.sh) package manager.

## Prerequisites

Tests for the code were performed on a **Kubernetes cluster** (v1.26.6) with **Istio** (1.13.3).
> It is possible to use other versions, but it hasn't been tested.

### Compatible Operating Systems

The code works on Debian-based Linux distributions (Debian 10 and Ubuntu 20.04) and Windows WSL2. Also, it may work (but it is not guaranteed) on Google Cloud Shell.

Other operating systems, including macOS, have not been verified and are currently unsupported.

### Required Packages

These packages are requisite for installation from a local computer:

- **Helm** (v3.9.3 or higher) [helm](https://helm.sh/docs/intro/install/)

- **Kubectl** (v1.26.0 or higher) [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl)

## Installation

Use any code editor to set variables in the **values.yaml** file. Some of the values are prefilled. However, you'll need to specify some values as well. Detailed information about these variables is provided below.

### Global Variables

| Name | Description | Type | Default |Required |
|------|-------------|------|---------|---------|
**global.domain** | your domain for an external endpoint, ex `example.com` | string | `-` | yes
**global.onPremEnabled** | whether on-prem is enabled | boolean | `false` | yes
**global.limitsEnabled** | whether CPU and memory limits are enabled | boolean | `true` | yes

### Configmap Variables

| Name | Description | Type | Default |Required |
|------|-------------|------|---------|---------|
**data.cloudProvider** | Cloud Provider | string | `gc` | yes
**data.openapiPrefix** | OpenAPI prefix | string | `/api/rafs-ddms` | yes
**data.storageHost** | Storage service host address | string | `http://storage` | yes
**data.searchHost** | Search service host address | string | `http://search` | yes
**data.partitionHost** | Partition service host address | string | `http://partition` | yes
**data.entitlementsHost** | Entitlements service host address | string | `http://entitlements` | yes
**data.datasetHost** | Dataset service host address | string | `http://dataset` | yes
**data.enableApiV1** | Deployment flag to enable api V1 | string | `True` | yes
**data.cacheEnable** | Enable or disable cache for the application | string | `True` | yes
**data.cacheBackend** | Path to your backend, which is used to initialize FastAPICache | string | `app.core.helpers.cache.backends.redis_cache.RedisCacheBackend` | yes
**data.redisRafsDdmsHost** | Redis instance host. If empty, Helm installs an internal Redis instance | string | `redis-rafs-ddms` | yes
**data.redisRafsDdmsDatabase** | Redis database number | string | `13` | yes
**data.redisRafsDdmsSsl** | Enable SSL for external Redis instance. For Redis inside k8s - should be `False` | string | `False` | yes
**data.redisRafsDdmsPort** | Redis instance port | string | `6379` | yes
**data.redisIndexEnable** | Enable redis index | bool | `True` | yes

### Deployment Variables

| Name | Description | Type | Default |Required |
|------|-------------|------|---------|---------|
**data.requestsCpu** | amount of requested CPU | string | `5m` | yes
**data.requestsMemory** | amount of requested memory| string | `350Mi` | yes
**data.limitsCpu** | CPU limit | string | `2` | only if `global.limitsEnabled` is true
**data.limitsMemory** | memory limit | string | `3G` | only if `global.limitsEnabled` is true
**data.redisRequestsCpu** | amount of requested CPU for Redis instance | string | `10m` | yes
**data.redisRequestsMemory** | amount of requested memory for Redis instance | string | `50Mi` | yes
**data.redisImage** | Redis instance image | string | `redis:7.2-alpine` | yes
**data.image** | Service image | string | - | yes
**data.imagePullPolicy** | when to pull image | string | `IfNotPresent` | yes
**data.serviceAccountName** | k8s service account name for the application | string | `rafs-ddms` | yes

### Config Variables

| Name | Description | Type | Default |Required |
|------|-------------|------|---------|---------|
**conf.appName** | Service name | string | `rafs-ddms` | yes
**conf.configmap** | configmap to be used | string | `rafs-ddms-config` | yes
**conf.rafsDdmsRedisSecretName** | rafs-ddms redis secret | string | `rafs-ddms-redis-secret` | yes
**conf.replicas** | Number of replicas for the application k8s deployment | string | `rafs-ddms` | yes

### Istio Variables

| Name | Description | Type | Default |Required |
|------|-------------|------|---------|---------|
**istio.redisProxyCPU** | CPU request for Envoy sidecars for Redis instance pod | string | `50m` | yes
**istio.redisProxyMemory** | memory request for Envoy sidecars for Redis instance pod | string | `100Mi` | yes

### Installing the Helm Chart

To install the Helm Chart, run the following command from within this directory:

```console
helm install gc-rafs-ddms-deploy .
```

## Uninstalling the Helm Chart

To uninstall the Helm deployment, execute the following command:

```console
helm uninstall gc-rafs-ddms-deploy
```

> Remember to delete all relevant Kubernetes secrets and/or PVCs after uninstalling the Service.
