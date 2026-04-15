# XRF v1.0.0 -> v1.1.0 Schema Changes

## Corrections
- `ElementalComposition.description`: added missing period at end of sentence
- `ElementalComposition[*].description`: aligned with parent array description
- `ElementalComposition[*].Content.x-osdu-frame-of-reference`: `"UOM:dimensionless"` → `"UOM:mass per mass"`

## New Fields

| Field | Type | UOM / Notes |
|-------|------|-------------|
| `OxideComposition` | array of objects | Nested properties: `OxideID` (reference-data `Oxides`), `Content` (mass per mass) |
| `XRFSourceTypeID` | string | reference-data `XRFSourceType` |
| `XRFTubeTypeID` | string | reference-data `XRFTubeType` |
| `IsEnergyDispersiveXRF` | boolean | Identifies EDXRF (true) vs WDXRF (false) |
| `XRFInstrumentTypeID` | string | reference-data `XRFInstrumentType` |
| `MassBalance` | number | mass per mass |
| `GravimetricLossOnIgnition` | number | mass per mass |
