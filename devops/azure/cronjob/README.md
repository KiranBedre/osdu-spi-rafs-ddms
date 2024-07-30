# Cronjob

## Quick start

```shell
docker run -it --rm --env AZURE_KEY_VAULT_URI=https://osdu-mvp-crglab-qh63-kv.vault.azure.net/ \
  --env RAFS_URI=https://osdu-glab.msft-osdu-test.org \
  --env AZURE_CLIENT_ID=<> \
  --env AZURE_CLIENT_SECRET=<> \
  --env AZURE_TENANT_ID=<> \
  osdumvpcrglabqh63cr.azurecr.io/rafs/cronjob:latest
```

## Build

```shell
docker build -t osdumvpcrglabqh63cr.azurecr.io/rafs/cronjob:latest .
```

## Development

```shell
az login
az account set -s MCI-ENERGY-OSDU-COLLAB02

export GOTMPDIR=${HOME}/.go/go-build
export GOPATH=${HOME}/.go

export AZURE_KEY_VAULT_URI=https://osdu-mvp-crglab-qh63-kv.vault.azure.net/
export RAFS_URI=https://osdu-glab.msft-osdu-test.org

go run main.go
```
