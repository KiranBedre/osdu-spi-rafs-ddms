# RAFS DDMS Postman Collection Run Guide

This guide explains how to run the RAFS DDMS Postman collection, with a dedicated section for Fluid Model (Black Oil and Compositional), including dependency records you must ingest first.

Collection file:
- [RAFS DDMS collection](../../devops/core-plus/qa/Postman%20Collection/Collection/RAFS%20DDMS.postman_collection.json)

Environment file:
- [OSDU CI environment](../../devops/core-plus/qa/Postman%20Collection/Environment/OSDU_CI.postman_environment.json)

## 1. Prerequisites

You need access to a deployed RAFS DDMS environment and supporting OSDU services:
- RAFS DDMS API host
- Identity provider/token endpoint
- Storage service
- Dataset service
- Schema service
- Search service
- Partition service
- Entitlements service

Required Postman variables (from environment and collection):
- RAFS_DDMS_HOST
- Token_Fetch_URL
- CLIENT_ID
- CLIENT_SECRET
- Scope
- data-partition-id
- authority
- domain
- LtagName

Recommended:
- Use a dedicated partition and legal tag for test runs.
- Run collection in sequence (do not parallelize requests that depend on previous IDs).

## 2. Import and Setup

1. Import the collection file:
   - RAFS DDMS.postman_collection.json
2. Import the environment file:
   - OSDU_CI.postman_environment.json
3. Select the imported environment in Postman.
4. Verify secrets and endpoints:
   - CLIENT_ID, CLIENT_SECRET, Token_Fetch_URL, RAFS_DDMS_HOST.
5. Save environment values.

## 3. Execution Order (High Level)

Run folders in this order:
1. Configure collection
2. v2
3. Clean Up

Inside Configure collection, run:
1. Auth / Refresh Token
2. Create related records / Legal Tag
3. Create related records / Reference data
4. Create related records / Master Data
5. Create related records / FluidModel - Prerequiste records

Important:
- Many v2 requests assume IDs and variables created by earlier requests (record IDs, versions, dataset IDs).
- If one setup request fails, downstream requests usually fail with 400/404.

## 4. Fluid Model: What Is Implemented

The API supports Fluid Model endpoints under:
- /v2/fluidmodel
- /v2/fluidmodel/fluidmodeltypes
- /v2/fluidmodel/{fluid_model_type}/data/schema
- /v2/fluidmodel/{fluid_model_type}/search
- /v2/fluidmodel/{fluid_model_type}/search/data
- /v2/fluidmodel/{record_id}/data/{fluid_model_type}
- /v2/fluidmodel/{record_id}/data/{fluid_model_type}/{dataset_id}

Currently used fluid_model_type values:
- blackoilfluidmodel
- compositionalfluidmodel

Collection coverage:
- Black Oil Fluid Model folder (full create/version/data/search/delete flow).
- Compositional Fluid Model folder (create/data/search flow).
- Get Fluid Model Types request in the Fluid Model folder root.

## 5. Fluid Model Dependencies

Fluid Model requests require these dependencies to exist first.

### 5.1 Mandatory Common Dependencies

- Legal tag in the active partition.
- Default ACL groups:
  - data.default.viewers@{partition}{domain}
  - data.default.owners@{partition}{domain}
- Master/reference records used by payload fields, including:
  - Workflow usage types
  - Unit of measure records used by Meta unit annotations

### 5.2 Black Oil Reference Data Dependencies

For Black Oil record/data requests, ensure these reference data IDs exist:
- reference-data--FluidModelType:BlackOil
- reference-data--FluidModelPropertyType:Density
- reference-data--FluidModelPropertyFormulationMethod:BlackOil.SimulatedLiberation
- reference-data--BlackOilFlashMechanismApplied:DifferentialLiberation
- reference-data--FluidModelSaturationType:BubblePoint

### 5.3 Compositional Reference Data Dependencies

For Compositional record/data requests, ensure these reference data IDs exist:
- reference-data--FluidModelType:Compositional
- reference-data--FluidModelPropertyType:Density
- reference-data--FluidModelPropertyFormulationMethod:Compositional.PengRobinson (or another valid compositional formulation)
- reference-data--ViscosityModelType:* used in compositional rows
- reference-data--ReservoirComponentCompositionType:* used in phase/composition sections
- UnitOfMeasure records referenced by compositional Meta (examples below):
  - Euc
  - psi
  - degC
  - cP
  - g/mol
  - kg/m3
  - m3/mol
  - 1/psi
  - m
  - N/m
  - %

Notes:
- If your partition does not contain these records, ingest them first (for example using the reference-data setup requests/manifests in this repository).
- A valid compositional dataset payload should align with:
  - [compositional_fluid_model_orient_split.json](../../tests/test_api/test_routes/api_v2/compositional_fluid_model/compositional_fluid_model_orient_split.json)

### 5.4 Minimum Dependency Ingest Sequence (Exact Request Names)

Run this minimum checklist before executing Fluid Model requests.

In this QA collection (RAFS DDMS.postman_collection.json):
1. Configure collection / Auth / Refresh Token
2. Configure collection / Create related records / Legal Tag / 01 - Create Legal Tag
3. Configure collection / Create related records / Reference data / Ingest RefData UnitOfMeasure
4. Configure collection / Create related records / FluidModel - Prerequiste records / Create WPC PersistedCollection:DummyCollection
5. Configure collection / Create related records / FluidModel - Prerequiste records / Create WPC FluidModel:ParentModelID (required only if your payload sets ParentModelID)

If Fluid Model reference-data IDs are still missing in your partition, run these exact requests from deployments/rafsddms_ref_data_manifests_mvp.postman_collection.json:
1. Ingest RefData FluidModelType
2. Ingest RefData FluidModelPropertyType
3. Ingest RefData FluidModelPropertyFormulationMethod
4. Ingest RefData BlackOilFlashMechanismApplied
5. Ingest RefData FluidModelSaturationType
6. Ingest RefData UnitOfMeasure

For compositional payloads that include additional IDs (for example ViscosityModelType or ReservoirComponentCompositionType), ingest the matching reference-data manifests for those IDs in the same deployments collection before running Add data.

## 6. Running Fluid Model Folder

Run order inside Fluid Model:
1. Get Fluid Model Types
2. Black Oil Fluid Model flow
3. Compositional Fluid Model flow

For each flow, run in order:
1. Create record
2. Create new version (if included)
3. Get record/versions/concrete version
4. Get content schema
5. Add data
6. Get record data
7. Search/search data requests
8. Delete and deleted-record checks (if included)

Why this order matters:
- Data requests require record IDs created in step 1.
- Concrete version calls require versions produced in earlier steps.
- Search calls are meaningful after data is ingested.

## 7. Common Failure Modes and Fixes

401/403:
- Refresh token again.
- Verify Scope, CLIENT_ID/CLIENT_SECRET, and group entitlements.

404 on reference IDs:
- Missing reference data in partition.
- Ingest missing reference-data records before retrying.

400 validation errors on Add data:
- Payload does not match schema columns/types.
- Invalid reference-data IDs in payload.
- Missing required fields for selected content schema version.

404 on record/data endpoints:
- Record variable was not set due to earlier request failure.
- Re-run the corresponding Create request and verify test scripts set variables.

## 8. Tips for Reliable Runs

- Keep content schema version consistent in Accept headers.
- Use one clean run per partition/runner when debugging.
- If variables become stale, clear collection variables and re-run setup.
- Keep the Create related records section green before running Fluid Model requests.

## 9. References

Main collection:
- [RAFS DDMS collection](../../devops/core-plus/qa/Postman%20Collection/Collection/RAFS%20DDMS.postman_collection.json)

Environment:
- [OSDU CI environment](../../devops/core-plus/qa/Postman%20Collection/Environment/OSDU_CI.postman_environment.json)

Compositional payload reference:
- [compositional_fluid_model_orient_split.json](../../tests/test_api/test_routes/api_v2/compositional_fluid_model/compositional_fluid_model_orient_split.json)

Reference data manifests (for dependency seeding):
- [rafsddms_ref_data_manifests_mvp.postman_collection.json](../../deployments/rafsddms_ref_data_manifests_mvp.postman_collection.json)
