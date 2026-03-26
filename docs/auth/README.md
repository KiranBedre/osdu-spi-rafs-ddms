# OSDU Rock and Fluid Sample DDMS - Endpoint Permissions (Grouped)

## Permission Model

- **All endpoints require HTTP Bearer authentication.**
- **ACL Membership:** All endpoints (except `/info`) require the user to be a member of the relevant data group (ACL).
- **Role Mapping by HTTP Method:**
  - **GET**: `users.datalake.viewers`, `users.datalake.editors`, or `users.datalake.admins`
  - **POST**: `users.datalake.editors` or `users.datalake.admins`
  - **DELETE**: `users.datalake.editors` or `users.datalake.admins`

---

## Resource Groups

### 1. SamplesAnalysesReport
**Base Path:** `/api/rafs-ddms/v2/samplesanalysesreport`

| Method(s) | Endpoints (suffix) | Permissions |
|-----------|--------------------|-------------|
| GET       | `/`, `/{record_id}`, `/{record_id}/versions`, `/{record_id}/versions/{version}`, `/{record_id}/source` | viewers, editors, admins + ACL |
| POST      | `/`                | editors, admins + ACL |
| DELETE    | `/{record_id}`     | editors, admins + ACL |

---

### 2. SamplesAnalysis
**Base Path:** `/api/rafs-ddms/v2/samplesanalysis`

| Method(s) | Endpoints (suffix) | Permissions |
|-----------|--------------------|-------------|
| GET       | `/analysistypes`, `/{record_id}`, `/{record_id}/versions`, `/{record_id}/versions/{version}`, `/{analysistype}/data/schema`, `/{record_id}/data/{analysis_type}/{content_id}`, `/{analysis_type}/search`, `/{analysis_type}/search/data` | viewers, editors, admins + ACL |
| POST      | `/`, `/{record_id}/data/{analysis_type}` | editors, admins + ACL |
| DELETE    | `/{record_id}`     | editors, admins + ACL |

---

### 3. SaturationFunctionSet
**Base Path:** `/api/rafs-ddms/v2/saturationfunctionset`

| Method(s) | Endpoints (suffix) | Permissions |
|-----------|--------------------|-------------|
| GET       | `/search`, `/search/data`, `/{record_id}`, `/{record_id}/versions`, `/{record_id}/versions/{version}`, `/data/schema`, `/{record_id}/data/{content_id}` | viewers, editors, admins + ACL |
| POST      | `/`, `/{record_id}/data` | editors, admins + ACL |
| DELETE    | `/{record_id}`     | editors, admins + ACL |

---

### 4. MasterData
**Base Path:** `/api/rafs-ddms/v2/masterdata`

| Method(s) | Endpoints (suffix) | Permissions |
|-----------|--------------------|-------------|
| GET       | `/{record_id}`, `/{record_id}/versions`, `/{record_id}/versions/{version}` | viewers, editors, admins + ACL |
| POST      | `/`                | editors, admins + ACL |
| DELETE    | `/{record_id}`     | editors, admins + ACL |

---

### 5. ReservoirSimulationRockPhysicsModel
**Base Path:** `/api/rafs-ddms/v2/reservoirsimulationrockphysicsmodel`

| Method(s) | Endpoints (suffix) | Permissions |
|-----------|--------------------|-------------|
| GET       | `/search`, `/search/data`, `/{record_id}`, `/{record_id}/versions`, `/{record_id}/versions/{version}`, `/data/schema`, `/{record_id}/data/{content_id}` | viewers, editors, admins + ACL |
| POST      | `/`, `/{record_id}/data` | editors, admins + ACL |
| DELETE    | `/{record_id}`     | editors, admins + ACL |

---

### 6. FluidModel
**Base Path:** `/api/rafs-ddms/v
2/fluidmodel`

| Method(s) | Endpoints (suffix) | Permissions |
|-----------|--------------------|-------------|
| GET       | `/{record_id}`, `/{record_id}/versions`, `/{record_id}/versions/{version}` | viewers, editors, admins + ACL |
| POST      | `/`                | editors, admins + ACL |
| DELETE    | `/{record_id}`     | editors, admins + ACL |

---

### 7. Dev Endpoints (SamplesAnalysis)
**Base Path:** `/api/rafs-ddms/dev/samplesanalysis`

| Method(s) | Endpoints (suffix) | Permissions |
|-----------|--------------------|-------------|
| GET       | `/{record_id}/data/{analysis_type}`, `/{analysis_type}/search/data`, `/{analysis_type}/search` | viewers, editors, admins + ACL |
| POST      | `/{record_id}/data/{analysis_type}` | editors, admins + ACL |

---

### 8. Info
| Endpoint | Method | Permissions |
|----------|--------|-------------|
| `/api/rafs-ddms/info` | GET | Public (no roles required) |

---
