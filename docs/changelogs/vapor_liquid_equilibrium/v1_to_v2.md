# VLE v1.0.0 -> v2.0.0 Schema Changes

## Metadata
- `$id`: `vapor_liquid_equilibrium.1.0.0.json` → `vapor_liquid_equilibrium.2.0.0.json`
- `x-osdu-review-status`: `"Pending Review"` → `"Accepted"`
- Schema description updated: expanded "EOR" to "enhanced oil recovery", added "equilibrium contact" terminology

## Corrections
- `SamplesAnalysisID.title`: corrected typo `"Samples Analysis D"` → `"Samples Analysis ID"`
- `Meta.example`: corrected type from `""` (empty string) to `[]` (empty array); same correction applied to `Remarks` arrays
- Removed `"additionalProperties": false` from individual numeric/string properties (not applicable to non-object types per JSON Schema spec)
- Removed `"additionalProperties": false` from nested array items (`VaporComposition`, `LiquidComposition`, `Remarks`)
- Added `"x-osdu-inheriting-from-kind": []` at root level for OSDU schema compliance

## Changed Fields

| v1.0.0 | v2.0.0 |
|--------|--------|
| `MixtureRelativeVolumeRelativeToPsat` | `MixtureRelativeVolume` |
| `AtmosphericFlashTestReference` | Split into `VaporPhaseAtmosphericFlashTestReferenceID` and `LiquidPhaseAtmosphericFlashTestReferenceID` |
| `VaporTransportTestReference` | `VaporTransportTestReferenceID` |
| `LiquidTransportTestReference` | `LiquidTransportTestReferenceID` |

## New Fields

| Field | Type | UOM |
|-------|------|-----|
| `GasToFluidMoleFraction` | number | dimensionless |
| `GasToFluidMolePercent` | number | dimensionless |
| `GasToTotalMoleFraction` | number | dimensionless |
| `GasToTotalMolePercent` | number | dimensionless |
| `MixtureRelativeVolume` | number | dimensionless |
| `InjectedGas` | array of objects | Nested properties: `ComponentNameID`, `RelativeMoleWeight`, `MolecularWeight`, `MolePercent`, `MassPercent`, `VolumePercent`, `SpecificGravity` |
| `LiquidPhaseViscosity` | number | dynamic viscosity |
| `VaporPhaseAtmosphericFlashTestReferenceID` | string | OSDU relationship (`SamplesAnalysisID`) |
| `LiquidPhaseAtmosphericFlashTestReferenceID` | string | OSDU relationship (`SamplesAnalysisID`) |

## Removed Fields

| Field | Type | UOM | Notes |
|-------|------|-----|-------|
| `GasSolventAdded` | number | amount of substance | |
| `MixtureGasSolventMoleFraction` | number | dimensionless | |
| `MixtureRelativeVolumeRelativeToPsat` | number | dimensionless | Replaced by `MixtureRelativeVolume` |
| `AtmosphericFlashTestReference` | string | — | Split into per-phase reference IDs |
| `InjectedGasAdded` | number | volume | Replaced by `InjectedGas` array |
| `CumulativeGasAdded` | number | volume | |
