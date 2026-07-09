# Search Documentation

This directory contains comprehensive documentation for RAFS DDMS search functionality, including scope filtering, parameters, and usage examples.

## Contents

### 1. [Search Scope Filtering](./search_scope_filtering.md)

Complete guide to hierarchical search scoping across organizational levels (Basin → Field → Well → Wellbore).

**Covers:**
- What search scopes are and how they work
- Scope parameters available for each endpoint type
- Master-data requirements for scope resolution
- WPC data structure requirements
- Usage examples for all endpoint types
- Error handling and best practices

**Start here if:** You want to understand how to use scope filtering to narrow search results.

---

### 2. [Search Scope Data Structure Reference](./search_scope_data_structure_reference.md)

Quick reference guide showing exact JSON structures needed for scope filtering.

**Contains:**
- Master-data record schemas (Basin, Field, Well, Wellbore, Sample)
- WPC data requirements for each record type
- Ingestion checklist
- Record ID format reference
- Common issues and solutions

**Start here if:** You need exact JSON structures for ingesting master-data or WPCs.

---

## Quick Start

### Prerequisites

1. Create master-data records in this order:
   - Basin
   - Field
   - Well (references Basin, Field)
   - Wellbore (references Well, Basin, Field)
   - Sample (references Well, Wellbore, Basin, Field)

2. Ensure your WPCs have the required scope fields:
   - **SamplesAnalysis**: `SampleIDs` (single Sample reference per RAFS ingestion convention)
   - **DepthShift**: `WellboreID` + `GeoContexts` with BasinID/FieldID
   - **SaturationFunctionSet**: `GeoContexts` with BasinID/FieldID
   - **ReservoirSimulationRockPhysicsModel**: `GeoContexts` with BasinID/FieldID

### Usage

```bash
# Search SamplesAnalysis by wellbore
curl -X GET "http://localhost:8000/api/rafs-ddms/v2/samplesanalysis/relativepermeability/search?wellbore_id=osdu:master-data--Wellbore:wellbore-789:" \
  -H "Authorization: Bearer <token>" \
  -H "data-partition-id: osdu"

# Search DepthShift by basin and field
curl -X GET "http://localhost:8000/api/rafs-ddms/v2/depthshift/search?basin_id=osdu:master-data--Basin:north-sea:&field_id=osdu:master-data--Field:field-123:" \
  -H "Authorization: Bearer <token>" \
  -H "data-partition-id: osdu"

# Search SaturationFunctionSet by field
curl -X GET "http://localhost:8000/api/rafs-ddms/v2/saturationfunctionset/search?field_id=osdu:master-data--Field:field-123:" \
  -H "Authorization: Bearer <token>" \
  -H "data-partition-id: osdu"
```

---

## Scope Availability by Endpoint

| Endpoint | basin_id | field_id | well_id | wellbore_id | Resolution |
|----------|:--------:|:--------:|:-------:|:-----------:|-----------|
| **SamplesAnalysis** | ✓ | ✓ | ✓ | ✓ | Two-hop: Scope params → Sample records → SamplesAnalysis IDs |
| **DepthShift** | ✓ | ✓ | ✗ | ✓ | Direct: Match on record data fields |
| **SaturationFunctionSet** | ✓ | ✓ | ✗ | ✗ | Direct: Match on GeoContexts |
| **ReservoirSimulationRockPhysicsModel** | ✓ | ✓ | ✗ | ✗ | Direct: Match on GeoContexts |

---

## Data Flow Diagram

```
Master-Data Layer
├── Basin
├── Field
├── Well (references Basin, Field)
├── Wellbore (references Well, Basin, Field)
└── Sample (references Well, Wellbore, Basin, Field)
        ↓
WPC Layer (uses scope parameters to filter)
├── SamplesAnalysis (references Sample → enables all 4 scopes)
├── DepthShift (has WellboreID → enables 3 scopes)
├── SaturationFunctionSet (has GeoContexts → enables 2 scopes)
└── ReservoirSimulationRockPhysicsModel (has GeoContexts → enables 2 scopes)
        ↓
Search Results (filtered by requested scopes)
```

---

## Scope Resolution Strategies

### Two-Hop Resolution (SamplesAnalysis)

1. **Input:** Scope parameters (e.g., `wellbore_id`)
2. **Hop 1:** Resolve Sample master-data records matching the criteria
3. **Hop 2:** Extract Sample IDs and filter SamplesAnalysis records by those IDs
4. **Output:** Scoped SamplesAnalysis results

**Why:** SamplesAnalysis doesn't carry well/wellbore data directly; it references Samples, which carry hierarchy information.

### Direct Resolution (DepthShift, SaturationFunctionSet, ReservoirSimulationRockPhysicsModel)

1. **Input:** Scope parameters (e.g., `basin_id`, `field_id`)
2. **Matching:** Filter records where `data` fields match the scope values
3. **Output:** Scoped results

**Why:** These WPCs carry scope data directly (WellboreID or GeoContexts), so no intermediate resolution is needed.

---

## API Endpoints with Scope Support

### SamplesAnalysis Search

```
GET /api/rafs-ddms/v2/samplesanalysis/{analysis_type}/search
GET /api/rafs-ddms/v2/samplesanalysis/{analysis_type}/search/
GET /api/rafs-ddms/v2/samplesanalysis/{analysis_type}/search/data
```

**Scopes:** `basin_id`, `field_id`, `well_id`, `wellbore_id`

### DepthShift Search

```
GET /api/rafs-ddms/v2/depthshift/search
GET /api/rafs-ddms/v2/depthshift/search/
GET /api/rafs-ddms/v2/depthshift/search/data
```

**Scopes:** `basin_id`, `field_id`, `wellbore_id`

### SaturationFunctionSet Search

```
GET /api/rafs-ddms/v2/saturationfunctionset/search
GET /api/rafs-ddms/v2/saturationfunctionset/search/
GET /api/rafs-ddms/v2/saturationfunctionset/search/data
```

**Scopes:** `basin_id`, `field_id`

### ReservoirSimulationRockPhysicsModel Search

```
GET /api/rafs-ddms/v2/reservoirsimulationrockphysicsmodel/search
GET /api/rafs-ddms/v2/reservoirsimulationrockphysicsmodel/search/
GET /api/rafs-ddms/v2/reservoirsimulationrockphysicsmodel/search/data
```

**Scopes:** `basin_id`, `field_id`

---

## Error Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 400 | Bad Request | Invalid scope format, unsupported scope parameter, malformed query |
| 404 | Not Found | Referenced master-data record doesn't exist |
| 422 | Unprocessable Entity | Scope resolution ambiguous, depth-shift validation failed, mixed wellbore IDs |

---

## Related Documentation

- **[OpenAPI Schema](../spec/openapi.json)** — Complete API documentation with all parameters
- **[Depth-Shift Functionality](../depth-shift/depth_shift_get_search_functionality.md)** — Depth-shift specific scoping rules and validation
- **[Tutorial](../tutorial/README.md)** — Step-by-step ingestion examples
- **[Architecture](../architecture/README.md)** — System overview and component design

---

## Key Points to Remember

1. **Scopes are optional** — searches work without scope parameters
2. **Scopes are hierarchical** — where supported by the endpoint, combine them for more specific results (basin → field → well → wellbore)
3. **Master-data must exist first** — create Basin, Field, Well, Wellbore records before WPCs reference them
4. **Each endpoint type has different scope support** — check the table above for your endpoint (SamplesAnalysis supports all 4, DepthShift supports 3, others support 2)
5. **SamplesAnalysis uses two-hop resolution** — scopes resolve through Sample master-data
6. **Other types use direct resolution** — scopes match data fields directly

---

## Troubleshooting

**No results even with valid scopes?**
→ Check that master-data records exist and WPCs reference them correctly

**400 error on scope parameter?**
→ Verify the record ID format (`authority:kind:identifier:version`)

**Empty results instead of error?**
→ This is normal when no records match the scope criteria

**Depth-shift error with multiple wellbores?**
→ Add `wellbore_id` scope to isolate a single wellbore

---

For detailed information on any topic, see the full documentation files above.
