# Search Scope Data Structure Reference

Quick reference for the exact data fields required in master-data and WPCs for scope filtering to work.

---

## Master-Data Records (Required Foundation)

All of these must exist before WPCs reference them.

### Basin

```json
{
  "id": "osdu:master-data--Basin:north-sea:",
  "type": "Record",
  "kind": "osdu:wks:master-data--Basin:1.0.0",
  "data": {
    "BasinName": "North Sea"
  }
}
```

**Used by:** All scope filters via `basin_id` parameter

---

### Field

```json
{
  "id": "osdu:master-data--Field:field-123:",
  "type": "Record",
  "kind": "osdu:wks:master-data--Field:1.0.0",
  "data": {
    "FieldName": "Kentish Knock South"
  }
}
```

**Used by:** All scope filters via `field_id` parameter

---

### Well

```json
{
  "id": "osdu:master-data--Well:well-456:",
  "type": "Record",
  "kind": "osdu:wks:master-data--Well:1.0.0",
  "data": {
    "WellName": "KKS-1",
    "BasinID": "osdu:master-data--Basin:north-sea:",
    "FieldID": "osdu:master-data--Field:field-123:"
  }
}
```

**Used by:** SamplesAnalysis scope filters via `well_id` parameter

---

### Wellbore

```json
{
  "id": "osdu:master-data--Wellbore:wellbore-789:",
  "type": "Record",
  "kind": "osdu:wks:master-data--Wellbore:1.0.0",
  "data": {
    "WellboreName": "KKS-1A",
    "WellID": "osdu:master-data--Well:well-456:",
    "BasinID": "osdu:master-data--Basin:north-sea:",
    "FieldID": "osdu:master-data--Field:field-123:"
  }
}
```

**Used by:**
- SamplesAnalysis scope filters via `wellbore_id` parameter
- DepthShift scope filters via `wellbore_id` parameter

---

### Sample (for SamplesAnalysis scoping)

```json
{
  "id": "osdu:master-data--Sample:sample-001:",
  "type": "Record",
  "kind": "osdu:wks:master-data--Sample:2.0.0",
  "data": {
    "WellID": "osdu:master-data--Well:well-456:",
    "WellboreID": "osdu:master-data--Wellbore:wellbore-789:",
    "BasinID": "osdu:master-data--Basin:north-sea:",
    "FieldID": "osdu:master-data--Field:field-123:"
  }
}
```

**Critical fields for scoping:**
- `WellID` — enables `well_id` filtering on SamplesAnalysis
- `WellboreID` — enables `wellbore_id` filtering on SamplesAnalysis
- `BasinID` — enables `basin_id` filtering on SamplesAnalysis
- `FieldID` — enables `field_id` filtering on SamplesAnalysis

---

## WPC Data Structures

### SamplesAnalysis

**Required fields for scoping:**

```json
{
  "data": {
    "SampleIDs": [
      "osdu:master-data--Sample:sample-001:"
    ],
    "SampleAcquisition": {
      "SampleAcquisitionDetail": {
        "WellboreID": "osdu:master-data--Wellbore:wellbore-789:"
      }
    }
  }
}
```

**Note:** Per RAFS convention, each WPC references a single Sample. While the schema allows multiple SampleIDs, standard RAFS ingestion is 1 content schema : 1 WPC : 1 Sample.

**Scope resolution:**
- `SampleIDs` → links to Sample master-data records
- Sample records contain `BasinID`, `FieldID`, `WellID`, `WellboreID`
- These fields enable two-hop filtering

**Supported scopes:**
- ✓ `basin_id` (via Sample.BasinID)
- ✓ `field_id` (via Sample.FieldID)
- ✓ `well_id` (via Sample.WellID)
- ✓ `wellbore_id` (via Sample.WellboreID or SampleAcquisition.SampleAcquisitionDetail.WellboreID)

---

### DepthShift

**Required fields for scoping:**

```json
{
  "data": {
    "WellboreID": "osdu:master-data--Wellbore:wellbore-789:",
    "GeoContexts": [
      {
        \"BasinID\": \"osdu:master-data--Basin:north-sea:\",
        \"FieldID\": \"osdu:master-data--Field:field-123:\"
      }
    ]
  }
}
```

**Scope resolution:**
- `WellboreID` → direct match on `wellbore_id` filter
- `GeoContexts[].BasinID` → matches `basin_id` filter
- `GeoContexts[].FieldID` → matches `field_id` filter

**Supported scopes:**
- ✓ `basin_id` (via data.GeoContexts[].BasinID)
- ✓ `field_id` (via data.GeoContexts[].FieldID)
- ✓ `wellbore_id` (via data.WellboreID)
- ✗ `well_id` (NOT supported - explicit error)

---

### SaturationFunctionSet

**Required fields for scoping:**

```json
{
  "data": {
    "GeoContexts": [
      {
        "BasinID": "osdu:master-data--Basin:north-sea:",
        "FieldID": "osdu:master-data--Field:field-123:"
      }
    ]
  }
}
```

**Scope resolution:**
- `GeoContexts[].BasinID` → matches `basin_id` filter
- `GeoContexts[].FieldID` → matches `field_id` filter

**Supported scopes:**
- ✓ `basin_id` (via data.GeoContexts[].BasinID)
- ✓ `field_id` (via data.GeoContexts[].FieldID)
- ✗ `well_id` (NOT supported - 400 error)
- ✗ `wellbore_id` (NOT supported - 400 error)

---

### ReservoirSimulationRockPhysicsModel

**Required fields for scoping:**

```json
{
  "data": {
    "GeoContexts": [
      {
        \"BasinID\": \"osdu:master-data--Basin:north-sea:\",
        \"FieldID\": \"osdu:master-data--Field:field-123:\"
      }
    ]
  }
}
```

**Scope resolution:**
- `GeoContexts[].BasinID` → matches `basin_id` filter
- `GeoContexts[].FieldID` → matches `field_id` filter

**Supported scopes:**
- ✓ `basin_id` (via data.GeoContexts[].BasinID)
- ✓ `field_id` (via data.GeoContexts[].FieldID)
- ✗ `well_id` (NOT supported - 400 error)
- ✗ `wellbore_id` (NOT supported - 400 error)

---

## Ingestion Checklist

Use this checklist to ensure your data is properly structured for scope filtering:

### Step 1: Create Master-Data Records

- [ ] Basin record created with unique ID
- [ ] Field record created with unique ID
- [ ] Well record created with `BasinID` and `FieldID`
- [ ] Wellbore record created with `WellID`, `BasinID`, `FieldID`
- [ ] Sample record created with all four ID fields (`BasinID`, `FieldID`, `WellID`, `WellboreID`)

### Step 2: Create WPCs

**For SamplesAnalysis:**
- [ ] `data.SampleIDs` array contains valid Sample record IDs
- [ ] `data.SampleAcquisition.SampleAcquisitionDetail.WellboreID` is set (or derived from Samples)
- [ ] Referenced Sample records exist and have all hierarchy IDs

**For DepthShift:**
- [ ] `data.WellboreID` is set
- [ ] `data.GeoContexts[0].BasinID` is set
- [ ] `data.GeoContexts[0].FieldID` is set

**For SaturationFunctionSet:**
- [ ] `data.GeoContexts[0].BasinID` is set
- [ ] `data.GeoContexts[0].FieldID` is set
- [ ] No `well_id` or `wellbore_id` scoping attempted

**For ReservoirSimulationRockPhysicsModel:**
- [ ] `data.GeoContexts[0].BasinID` is set
- [ ] `data.GeoContexts[0].FieldID` is set
- [ ] No `well_id` or `wellbore_id` scoping attempted

### Step 3: Test Scope Filtering

```bash
# Test SamplesAnalysis scoping
curl -X GET "http://localhost:8000/api/rafs-ddms/v2/samplesanalysis/relativepermeability/search?wellbore_id=osdu:master-data--Wellbore:wellbore-789:" \
  -H "Authorization: Bearer <token>" \
  -H "data-partition-id: osdu"

# Test DepthShift scoping
curl -X GET "http://localhost:8000/api/rafs-ddms/v2/depthshift/search?basin_id=osdu:master-data--Basin:north-sea:" \
  -H "Authorization: Bearer <token>" \
  -H "data-partition-id: osdu"

# Test SaturationFunctionSet scoping
curl -X GET "http://localhost:8000/api/rafs-ddms/v2/saturationfunctionset/search?field_id=osdu:master-data--Field:field-123:" \
  -H "Authorization: Bearer <token>" \
  -H "data-partition-id: osdu"
```

---

## Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Empty scope results | Master-data records don't exist | Create Basin, Field, Well, Wellbore records first |
| 400 error on unsupported scope | Using `well_id` on SaturationFunctionSet | Use only `basin_id` and `field_id` on that endpoint |
| Scope doesn't filter results | WPC missing required ID fields | Add `SampleIDs` (SamplesAnalysis), `WellboreID` (DepthShift), or `GeoContexts` (SaturationFunctionSet, ReservoirSimulationRockPhysicsModel) |
| Results include unwanted records | Sample records missing hierarchy IDs | Ensure Sample records have `BasinID`, `FieldID`, `WellID`, `WellboreID` |
| Depth-shift with mixed wellbore IDs error | Samples belong to different wellbores | Use more specific `wellbore_id` scope to isolate single wellbore |

---

## Record ID Format

All scope parameters must be valid OSDU record IDs. Format:

```
<partition>:<entity-type>:<identifier>[:<version>]
```

### Valid Examples:
- `osdu:master-data--Basin:north-sea:` (with trailing colon, latest version)
- `osdu:master-data--Field:field-123:1673921980922175` (with numeric version)
- `osdu:master-data--Well:KKS-1:` (different partition example)

### Invalid Examples:
- `north-sea` (missing partition and entity type)
- `master-data--Basin:north-sea` (missing partition)
- `osdu:master-data--Basin` (missing identifier)

---

## See Also

- [Search Scope Filtering](./search_scope_filtering.md) — Full documentation with examples
- [Depth-Shift Functionality](../depth-shift/depth_shift_get_search_functionality.md) — Depth-shift specific scoping rules
- [OpenAPI Schema](../spec/openapi.json) — Complete API documentation
