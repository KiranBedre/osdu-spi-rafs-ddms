# Atmospheric Flash And Compositional Analysis v1.0.0 -> v1.1.0 Schema Changes

## New Fields

| Field | Type | Notes |
|-------|------|-------|
| `Remarks` | `array` | Root-level array of `AbstractRemark` objects for capturing remarks or additional information for this analysis |
| `ContaminationCorrection.ReferenceFluid` | `string` | Replaces `ReferenceFluidID`. The fluid used as a reference to determine the degree of contamination, e.g. stock tank oil or reservoir fluid |

## Soft Deprecation

| Field | Replaced By | Notes |
|-------|-------------|-------|
| `ContaminationCorrection.ReferenceFluidID` | `ContaminationCorrection.ReferenceFluid` | The `ID` suffix was misleading as this field does not reference an OSDU reference list |
