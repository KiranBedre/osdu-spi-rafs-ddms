# XRF v1.0.0 -> v2.0.0 Schema Changes

## Metadata
- `$id`: `xrf.1.0.0.json` → `xrf.2.0.0.json`
- `x-osdu-review-status`: `"Pending Review"` → `"Accepted"`
- `title`: `"X-Ray Fluorescence Data Schema"` → `"XRF Data Schema"`
- `description`: expanded to include "non-destructive" characterization

## Corrections
- `Meta.example`: corrected type from `""` (empty string) to `[]` (empty array)
- `ElementalComposition.description`: added missing period at end of sentence
- `ElementalComposition[*].description`: aligned with parent array description
- `ElementalComposition[*].Content.x-osdu-frame-of-reference`: `"UOM:dimensionless"` → `"UOM:mass per mass"`

## Changed Fields

| Field | Change |
|-------|--------|
| `FrameOfReferenceUOM.required` | Added `unitOfMeasureID` and `propertyNames` to required array: `["kind"]` → `["kind", "unitOfMeasureID", "propertyNames"]` |

## New Fields

| Field | Type | UOM / Notes |
|-------|------|-------------|
| `OxideComposition` | array of objects | Nested properties: `OxideID` (OSDU relationship → `Oxides`), `Content` (mass per mass) |
| `XRFSourceTypeID` | string | OSDU relationship (`XRFSourceType`) |
| `XRFTubeTypeID` | string | OSDU relationship (`XRFTubeType`) |
| `IsEnergyDispersiveXRF` | boolean | Identifies EDXRF (true) vs WDXRF (false) |
| `XRFInstrumentTypeID` | string | OSDU relationship (`XRFInstrumentType`) |
| `MassBalance` | number | mass per mass |
| `GravimetricLossOnIgnition` | number | mass per mass |
