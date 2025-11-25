# Cloud-Agnostic Data Handling on Community imlementation (CI) environment

This README describes the **cloud-agnostic data handling** used in Community imlementation (CI) pipelines for RAFS-DDMS services.  
Unlike CSP-specific implementations (e.g., `AzureBlobStorage`), all data operations in CI use the **core services** `dataset` and `storage`.

## Core Services Overview

- **`dataset`** – abstraction layer for managing structured data across environments  
- **`storage`** – generic storage service for handling blobs and files, independent of any cloud provider  
- **`partition`, `schema`, `entitlements`** – supporting services used for dataset management and access control  

These services allow CI pipelines to remain **cloud-agnostic** and portable.

## Environment Variables

CI variables are divided into **pipeline-injected** and **default values**.

### 1. Pipeline-injected variables

These [values](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/devops/core-plus/pipeline/override-stages.yml?ref_type=heads#:~:text=helm%20upgrade%20%24CIMPL_SERVICE,set%20rosa%3Dtrue) are **automatically set during the `cimpl-deploy` job**

> ⚠️ These values are set by the Helm pipeline and **should not be modified manually**.

### 2. Default values (from `values.yaml`)

These [values](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/blob/main/devops/core-plus/deploy/values.yaml) remain defaults unless overridden by the pipeline:
