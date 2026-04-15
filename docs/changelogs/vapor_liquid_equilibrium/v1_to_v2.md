# Vapor Liquid Equilibrium v1.0.0 -> v2.0.0

## Overview
Schema updated from v1.0.0 to v2.0.0. Major version bump reflecting new fields, field renames,
and removal of several v1 properties. The `InjectedGas` array replaces the scalar
`InjectedGasAdded`/`CumulativeGasAdded` fields. Transport and flash test references are
renamed to the `*ReferenceID` convention and split per phase.

## Changes

### New Fields
- `GasToFluidMoleFraction` — mole fraction of injected gas relative to liquid in the mixture (`UOM:dimensionless`)
- `GasToFluidMolePercent` — mole percent of injected gas relative to liquid in the mixture (`UOM:dimensionless`)
- `GasToTotalMoleFraction` — mole fraction of injected gas relative to total mixture (`UOM:dimensionless`)
- `GasToTotalMolePercent` — mole percent of injected gas relative to total mixture (`UOM:dimensionless`)
- `MixtureRelativeVolume` — ratio of measured volume to volume at saturation pressure (`UOM:dimensionless`); replaces `MixtureRelativeVolumeRelativeToPsat`
- `InjectedGas` — array of objects capturing injected gas composition and properties (replaces scalar `InjectedGasAdded`/`CumulativeGasAdded`); nested fields: `ComponentNameID`, `RelativeMoleWeight`, `MolecularWeight`, `MolePercent`, `MassPercent`, `VolumePercent`, `SpecificGravity`
- `LiquidPhaseViscosity` — viscosity of the liquid phase (`UOM:dynamic viscosity`)
- `VaporTransportTestReferenceID` — replaces `VaporTransportTestReference`; plain string reference (upstream: missing pattern/relationship — see upstream schema issues)
- `LiquidTransportTestReferenceID` — replaces `LiquidTransportTestReference`; plain string reference (upstream: missing pattern/relationship — see upstream schema issues)
- `VaporPhaseAtmosphericFlashTestReferenceID` — replaces `AtmosphericFlashTestReference` (vapor phase); OSDU work-product-component relationship
- `LiquidPhaseAtmosphericFlashTestReferenceID` — replaces `AtmosphericFlashTestReference` (liquid phase); OSDU work-product-component relationship

### Corrections
- `SamplesAnalysisID.title`: corrected typo `"Samples Analysis D"` → `"Samples Analysis ID"`
- `Meta.example`: corrected type from `""` (empty string) to `[]` (empty array); same correction applied to `VaporComposition[*].Remarks` and `LiquidComposition[*].Remarks` arrays
- Removed `"additionalProperties": false` from individual numeric/string properties (not valid per JSON Schema spec for non-object types)
- Removed `"additionalProperties": false` from nested array items (`VaporComposition`, `LiquidComposition`, `Remarks`)
- Added `"x-osdu-inheriting-from-kind": []` at root level for OSDU schema compliance
- `x-osdu-review-status`: `"Pending Review"` → `"Accepted"`

### Removed Fields
- `GasSolventAdded` — removed (amount of substance); no direct replacement
- `MixtureGasSolventMoleFraction` — removed (dimensionless); no direct replacement
- `MixtureRelativeVolumeRelativeToPsat` — removed; replaced by `MixtureRelativeVolume`
- `AtmosphericFlashTestReference` — removed; replaced by per-phase `VaporPhaseAtmosphericFlashTestReferenceID` and `LiquidPhaseAtmosphericFlashTestReferenceID`
- `InjectedGasAdded` — removed (volume); replaced by `InjectedGas` array
- `CumulativeGasAdded` — removed (volume); replaced by `InjectedGas` array
- `VaporTransportTestReference` — removed; replaced by `VaporTransportTestReferenceID`
- `LiquidTransportTestReference` — removed; replaced by `LiquidTransportTestReferenceID`

## Migration Notes
- The `InjectedGas` array structure replaces scalar volume fields. Existing data stored using
  `InjectedGasAdded`/`CumulativeGasAdded` must be migrated to the array format.
- `AtmosphericFlashTestReference` (single string) is now split into two typed reference ID
  fields — one per phase. Both fields are optional.
- Transport test reference fields retain their string nature but are renamed to the `*ReferenceID`
  convention. Note: `VaporTransportTestReferenceID` and `LiquidTransportTestReferenceID` lack
  OSDU pattern and relationship annotations (upstream schema defect).
- The Meta block must cover all new UOM-annotated properties including the seven new
  `InjectedGas[*]` sub-fields and the four `GasTo*` top-level fields.
