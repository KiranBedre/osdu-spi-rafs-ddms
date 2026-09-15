## OSDU Well Known Schemas Disclaimer

Note regarding OSDU Well Known Schema interaction: Currently (January 2024), OSDU Data Definitions "Fluid Samples" and "Samples & Petrophysics" Project teams re-worked the data model for both rock and fluid samples in a way that there is a unified way to handle both.

Important Schemas to refer when using RAFSDDMS:

- [osdu:wks:master-data--GenericFacility:1.0.0](https://community.opengroup.org/osdu/platform/system/schema-service/-/blob/master/deployments/shared-schemas/osdu/master-data/GenericFacility.1.0.0.json?ref_type=heads)
- [osdu:wks:master-data--GenericSite:1.0.0](https://community.opengroup.org/osdu/platform/system/schema-service/-/blob/master/deployments/shared-schemas/osdu/master-data/GenericSite.1.0.0.json?ref_type=heads)
- [osdu:wks:master-data--Sample:2.0.0](https://community.opengroup.org/osdu/platform/system/schema-service/-/blob/master/deployments/shared-schemas/osdu/master-data/Sample.2.0.0.json?ref_type=heads)
- [osdu:wks:master-data--SampleAcquisitionJob:1.0.0](https://community.opengroup.org/osdu/platform/system/schema-service/-/blob/master/deployments/shared-schemas/osdu/master-data/SampleAcquisitionJob.1.0.0.json?ref_type=heads) 
- [osdu:wks:master-data--SampleChainOfCustodyEvent:1.0.0](https://community.opengroup.org/osdu/platform/system/schema-service/-/blob/master/deployments/shared-schemas/osdu/master-data/SampleChainOfCustodyEvent.1.0.0.json?ref_type=heads)
- [osdu:wks:master-data--SampleContainer:1.0.0](https://community.opengroup.org/osdu/platform/system/schema-service/-/blob/master/deployments/shared-schemas/osdu/master-data/SampleAcquisitionJob.1.0.0.json?ref_type=heads)
- [osdu:wks:work-product-component--SamplesAnalysesReport:1.0.0](https://community.opengroup.org/osdu/platform/system/schema-service/-/blob/master/deployments/shared-schemas/osdu/work-product-component/SamplesAnalysesReport.1.0.0.json?ref_type=heads)
- [osdu:wks:work-product-component--SamplesAnalysis:1.0.0](https://community.opengroup.org/osdu/platform/system/schema-service/-/blob/master/deployments/shared-schemas/osdu/work-product-component/SamplesAnalysis.1.0.0.json?ref_type=heads)

### Legacy schemas that will be removed once Api V1 is fully removed.
All [rafsddms WorkProductComponent schemas](./shared-schemas/rafsddms/work-product-component/) will be removed.

## Custom RAFS DDMS Schemas Usage

As of Jan 2024, the RAFS DDMS [content schemas](https://community.opengroup.org/osdu/platform/domain-data-mgmt-services/rock-and-fluid-sample/rafs-ddms-services/-/tree/main/app/models/data_schemas) may use reference data that is still not published in the OSDU forum, for both: schema definition and values.

### Schemas Registration

Before registering the schemas the next variables must be populated:

`{{rafsddms-schema-authority}}` - the custom schemas will have their own schema authority.

`{{schema-authority}}` - the schema authority that was used for the OSDU WKS schemas.

`{{SCHEMA_HOST}}` - the schema service, example: {{HOSTNAME}}/api/schema-service/v1.

We provide the schema definition for such reference data in the [reference-data](./shared-schemas/rafsddms/reference-data/) folder. The [Schemas Postman Collection](./rafsddms_schemas_mvp.postman_collection.json) can be used for the schemas registration.

### Reference Data Values Upload

Before uploading reference-data values the following variables must be populated ont the collection:

`WORKFLOW_URL` - the workflow url, example: {{HOSTNAME}}/api/workflow/v1

`NAMESPACE` - the data partition id
 
 `DATA_OWNERS_GROUP` and `DATA_VIEWERS_GROUP` for acl part of record

 `DATA_VIEWERS_GROUP` and `ISO_3166_ALPHA_2_CODE` for legal of record

The list of values can be found in [The Reference Values Postman Collection](./rafsddms_ref_data_manifests_mvp.postman_collection.json) and can be used to upload the reference-data values.

#### CIMPL dev1 CI bootstrap

Integration pytest discovers `reference-data--*` prerequisites from its positive JSON payloads and documented supplemental dependencies, checks their availability in Storage, and creates only missing records that have canonical definitions in the shared catalog. Existing records are preserved and never overwritten by the pytest preflight; prerequisite records and their persistent legal tag are not deleted during teardown. CI bootstrap jobs seed the same catalog ahead of CIMPL tests. Any dependencies that remain unavailable after bootstrap are reported together in a single preflight error instead of causing cascading 422 fixture failures.

On trusted/main CIMPL pipelines the job `cimpl-seed-reference-data` runs after `cimpl-deploy` and before `cimpl-test-python`. On `release/*` / tag prod pipelines: upstream `cimpl-prod-reset` → `cimpl-prod-deploy` → `cimpl-prod-seed-reference-data` → `cimpl-prod-test-python` / `cimpl-prod-acceptance-test-python`.

**Important:** `cimpl-prod-reset` (defined in upstream [`cimpl-global.yml`](https://community.opengroup.org/osdu/platform/ci-cd-pipelines/-/blob/release/0.30/cloud-providers/cimpl-global.yml)) clears the prod partition before deploy. Reference-data is **not** re-loaded from `osdu/qa` or `data-definitions` automatically — only via RAFS bootstrap jobs or Postman ingest steps in the main collection.

The external [`osdu/qa`](https://community.opengroup.org/osdu/qa) repository contains centrally scheduled QA collections whose results feed the PMC reports. The CIMPL jobs defined in this repository currently use the RAFS test assets under `devops/core-plus/qa/`; the RAFS collection should also be aligned with the central QA process.

Both jobs seed from one catalog, [`deployments/reference-data/rafs_integration_reference_data.json`](./reference-data/rafs_integration_reference_data.json). It holds every `reference-data--*` record the integration fixtures resolve, each already carrying `kind`, `acl`, `legal` and `data`, with `{{NAMESPACE}}`, `{{LEGAL_TAG}}`, `{{DATA_OWNERS_GROUP}}`, `{{DATA_VIEWERS_GROUP}}` and `{{ISO_3166_ALPHA_2_CODE}}` left as placeholders.

The job creates the Legal Tag through the Legal Service (treating `409` as success), renders the placeholders with `jq`, then loads the whole catalog in a single `PUT /api/storage/v2/records`. Storage is used rather than Workflow `Osdu_ingest` because the Workflow Service returns HTTP 500 on prod for these manifests, and because a synchronous Storage write is complete when the job exits — an accepted DAG run is not.

Before uploading, the rendered catalog is rejected unless it is a non-empty array of objects whose IDs are all unique `reference-data--*` values with `osdu:` kinds, and unless every placeholder resolved. A malformed or half-rendered catalog therefore fails the seed job instead of silently under-seeding the partition and surfacing later as unrelated 422 fixture errors.

Both seed jobs are blocking: if seeding fails, the integration jobs do not run.

Re-run locally against CIMPL (with credentials in the environment):

```bash
ACCESS_TOKEN=$(curl -s -X POST \
  "https://keycloak.dev1.osdu-cimpl.opengroup.org/realms/osdu/protocol/openid-connect/token" \
  -d grant_type=client_credentials \
  -d "client_id=${CIMPL_CLIENT_ID}" \
  -d "client_secret=${CIMPL_CLIENT_SECRET}" \
  -d scope=openid | jq -r .access_token)

jq --arg namespace osdu \
   --arg owners "data.default.owners@osdu.group" \
   --arg viewers "data.default.viewers@osdu.group" \
   --arg legalTag osdu-demo-legaltag \
   --arg country US \
   'def substitute($s; $r): split($s) | join($r);
    walk(if type == "string" then
      substitute("{{NAMESPACE}}"; $namespace)
      | substitute("{{DATA_OWNERS_GROUP}}"; $owners)
      | substitute("{{DATA_VIEWERS_GROUP}}"; $viewers)
      | substitute("{{LEGAL_TAG}}"; $legalTag)
      | substitute("{{ISO_3166_ALPHA_2_CODE}}"; $country)
    else . end)' \
   deployments/reference-data/rafs_integration_reference_data.json > /tmp/catalog.json

curl -X PUT "https://osdu.dev1.osdu-cimpl.opengroup.org/api/storage/v2/records" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "data-partition-id: osdu" \
  -H "Content-Type: application/json" \
  --data-binary @/tmp/catalog.json
```

To regenerate the catalog's ID list after fixtures change:

```bash
python scripts/list_integration_reference_gaps.py --all-fixture-ids
```

Ensure schemas for new types (for example `WellLogSamplingDomainType`) are registered via [The Schemas Postman Collection](./rafsddms_schemas_mvp.postman_collection.json) before value ingest if the partition does not already have them.

#### OSDU Reference Data
New reference-data has been added to OSDU since M21 and it's of particular relevance for the RAFS-DDMS, since it's utilized in the content schemas.

Schemas can be found for each type:
 - [SampleAnalysisFamily](https://community.opengroup.org/osdu/platform/system/schema-service/-/blob/master/deployments/shared-schemas/osdu/reference-data/SampleAnalysisFamily.1.0.0.json?ref_type=heads)
 - [SampleAnalysisSubFamily](https://community.opengroup.org/osdu/platform/system/schema-service/-/blob/master/deployments/shared-schemas/osdu/reference-data/SampleAnalysisSubFamily.1.0.0.json?ref_type=heads)
 - [SampleAnalysisType](https://community.opengroup.org/osdu/platform/system/schema-service/-/blob/master/deployments/shared-schemas/osdu/reference-data/SampleAnalysisType.1.0.0.json?ref_type=heads)
 - [SamplesAnalysisCategoryTag](https://community.opengroup.org/osdu/platform/system/schema-service/-/blob/master/deployments/shared-schemas/osdu/reference-data/SamplesAnalysisCategoryTag.1.0.0.json?ref_type=heads)

 And its corresponding reference values:
 - [SampleAnalysisFamily](https://community.opengroup.org/osdu/data/data-definitions/-/blob/master/ReferenceValues/Manifests/reference-data/OPEN/SampleAnalysisFamily.1.0.0.json?ref_type=heads)
 - [SampleAnalysisSubFamily](https://community.opengroup.org/osdu/data/data-definitions/-/blob/master/ReferenceValues/Manifests/reference-data/OPEN/SampleAnalysisSubFamily.1.0.0.json?ref_type=heads)
 - [SampleAnalysisType](https://community.opengroup.org/osdu/data/data-definitions/-/blob/master/ReferenceValues/Manifests/reference-data/OPEN/SampleAnalysisType.1.0.0.json?ref_type=heads)
 - [SamplesAnalysisCategoryTag](https://community.opengroup.org/osdu/data/data-definitions/-/blob/master/ReferenceValues/Manifests/reference-data/LOCAL/SamplesAnalysisCategoryTag.1.0.0.json?ref_type=heads)
