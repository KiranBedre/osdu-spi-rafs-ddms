# RAFS-DDMS DevOps Directory

This directory contains `cloud-specific` and `cloud-agnostic` DevOps assets used to build, deploy, test, and operate RAFS-DDMS across multiple platforms.
The structure is designed to keep each cloud provider isolated, easy to maintain, and aligned with a consistent deployment model.

The devops directory does not contain application logic — only deployment, CI/CD, platform integration, and operational tooling.
`No application logic lives here.`

[[_TOC_]]

## Directory Structure

```txt
devops/
├── aws/          # AWS CI/CD, buildspec, test runners
├── azure/        # Azure deployment, monitoring stack, QA tooling
├── core-plus/    # Cloud-agnostic Helm-based deployment (K8s/ROSA/OpenShift)
├── gc/           # Google Cloud deployment (HPA, spot, redis, VS)
└── osdu/         # OSDU-wide CI/CD overrides
```

## How to Navigate This Directory

- `Core-plus (core-plus/)`

  Contains the cloud-agnostic Helm chart. Use it as a reference or starting point for deployments that aim to be cloud-neutral.
  
  See [core-plus/README.md](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/devops/core-plus/README.md) for full instructions.
- `Cloud-specific folders (aws/, azure/, gc/)`

  Each contains provider-specific deployment artifacts, CI/CD logic, Dockerfiles, and QA tooling.
  
  Pick the folder that corresponds to the platform you are deploying to:
  - [aws/](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/tree/main/devops/aws)
  - [azure/README.md](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/devops/azure/README.md)
  - [gc/deploy/README.md](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/devops/gc/deploy/README.md)
- `OSDU-wide overrides (osdu/)`

  Contains global CI/CD overrides and configurations used for cross-platform consistency.
  
  See [osdu/override-stages.yml](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/devops/osdu/override-stages.yml) for details.

## What Belongs Here

The `/devops` directory should contain `only DevOps-related artifacts`, specifically:

✔ Cloud-specific CI/CD logic
  
- Buildspec files
- Override stages
- Provider-specific pipeline fragments

✔ Cloud-specific Dockerfiles

- Production runner images
- Test/QA runner images tied to CSP constraints

✔ Deployment artifacts

- Helm charts (core-plus, gc, azure)
- Values files and Kustomize fragments
- Internal support services (e.g., Redis) used strictly for deployment

✔ QA tooling that depends on the platform

- Postman collections + environments
- Newman pipeline definitions
- Test resources required for validation

✔ Monitoring implementation per CSP

- Prometheus/Grafana provisioning
- CSP-native exporters or monitoring images

## What Does NOT Belong Here

The following must `never` be placed inside `/devops`:

✘ Application code

- Business logic
- Service code
- Python/Go modules unrelated to deployment

✘ Cloud-agnostic service configuration

- These belong `inside the service repository` or in the Helm chart, not in the top-level `/devops`

✘ Product/user documentation

- `/devops` folder describes `how to deploy`, not `how the product works`

✘ Global CI/CD pipelines

- Global .gitlab-ci.yml belongs in the `rafs-ddms-services` root repository
- `Do not define full pipelines inside` /devops.
- Allowed in /devops:
  - Override stages (`override-stages.yml`)
  - Job fragments or modular CI/CD definitions (e.g., `cimpl-newman-test.gitlab-ci.yml`) included by the main pipeline for platform-specific or QA tasks.
