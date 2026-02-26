# Slimtube v1.0.0 → v2.0.0 Schema Changes

## Metadata
- `$id`: `slimtube.1.0.0.json` → `slimtube.2.0.0.json`
- `x-osdu-license`: Copyright year updated from 2025 → 2026
- `x-osdu-review-status`: `"Pending Review"` → `"Accepted"`
- No change in schema title or description.

## Corrections
- Fixed typos and improved clarity in some property descriptions (e.g., "Slim Tube Test" instead of "SLim Tube Test", more explicit descriptions for new fields).

## Changed Fields
- **PackedColumnProperties** renamed to **SlimTubeSpecification** and expanded:
  - Added new properties: `PermeabilityMeasurementMethodID`, `FluidTypeID`, `ColumnOuterDiameter`, `ColumnInnerDiameter`, `ColumnFlowCrossSectionalArea`
  - `ColumnDiameter` split into `ColumnOuterDiameter` and `ColumnInnerDiameter`
  - `PackingMaterial` description expanded to include more materials and rationale for being a free string
- **SlimTubeTestSteps**:
  - Added new properties: `StepAverageTemperature`, `StepBackPressure`, `SlimTubeTestVolumeSteps`, `MaterialBalanceData`
  - `SlimTubeTestVolumeSteps` moved from root to inside each `SlimTubeTestSteps` item
- **SlimTubeTestVolumeSteps** (now nested under `SlimTubeTestSteps`):
  - Renamed `CumulativeOilProductionSTO` to `CumulativeOilProductionAtStockTankConditions`
  - Added: `CumulativeGasProductionAtStockTankConditions`, `CumulativeVaporCompositionalAnalysis`, `CumulativeLiquidCompositionalAnalysis`, `IncrementalVaporCompositionalAnalysis`, `IncrementalLiquidCompositionalAnalysis`, `InstantaneousVaporCompositionalAnalysis`, `InstantaneousLiquidCompositionalAnalysis`, `SeparatorTemperature`, `SeparatorPressure`
- **MaterialBalanceData** (now nested under `SlimTubeTestSteps`):
  - Replaced previous fields with a new, more detailed set: `MassOfReservoirOilInSlimTube`, `MassOfReservoirOilInConnectingLines`, `MassOfReservoirOil`, `MassOfGasSolvent`, `MassTotalInjected`, `MassOfEffluentStockTankOilBeforeBlowDown`, `MassOfProducedEffluentGasBeforeBlowDown`, `MassOfEffluentStockTankOilAfterBlowDown`, `MassOfProducedEffluentGasAfterBlowDown`, `MassOfResidualOil`, `MassTotalRecovered`, `WeightPercentRecovered`
- **InjectedGas**: New array capturing composition and properties of injected gas.
- **CalculatedProperties.ResidueCalculatedProperties**: Added `ResidueMolecularWeight` and clarified descriptions.

## New Fields
- `InjectedGas` (array): Captures composition and properties of injected gas.
- `SlimTubeSpecification` (array): Replaces and expands on `PackedColumnProperties`.
- `SlimTubeTestSteps[*].SlimTubeTestVolumeSteps` (array): Now nested, with expanded compositional and production analysis.
- `SlimTubeTestSteps[*].MaterialBalanceData` (array): Now nested, with expanded detail.
- New compositional analysis arrays under `SlimTubeTestSteps[*].SlimTubeTestVolumeSteps`:  
  - `CumulativeVaporCompositionalAnalysis`
  - `CumulativeLiquidCompositionalAnalysis`
  - `IncrementalVaporCompositionalAnalysis`
  - `IncrementalLiquidCompositionalAnalysis`
  - `InstantaneousVaporCompositionalAnalysis`
  - `InstantaneousLiquidCompositionalAnalysis`
- New properties in `SlimTubeTestSteps[*].SlimTubeTestVolumeSteps`:  
  - `CumulativeGasProductionAtStockTankConditions`
  - `SeparatorTemperature`
  - `SeparatorPressure`

## Removed Fields
- `PackedColumnProperties` (replaced by `SlimTubeSpecification`)
- `CoreFlooding`
- `PackedColumnDisplacement`
- `VaporCompositionalAnalysis`
- `LiquidCompositionalAnalysis`
- Top-level `MaterialBalanceData` (now nested under `SlimTubeTestSteps`)
- Top-level `SlimTubeTestVolumeSteps` (now nested under `SlimTubeTestSteps`)

---

Let me know if you need a more granular field-by-field diff or a table format!
