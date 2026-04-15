# Slimtube v1.0.0 → v2.0.0 Schema Changes

## Metadata

* `$id`: `slimtube.1.0.0.json` → `slimtube.2.0.0.json`
* `x-osdu-license`: Copyright year updated from 2025 → 2026
* `x-osdu-review-status`: `"Pending Review"` → `"Accepted"`
* No change in schema title or description.

## Corrections

* Fixed typos and improved clarity in several property descriptions (e.g., "Slim Tube Test" instead of "SLim Tube Test").
* Improved wording and clarity in multiple descriptions across the schema.
* Expanded explanation for `PackingMaterial`, including the rationale for keeping it a free string rather than converting it to a reference list.

## Changed Fields

* **PackedColumnProperties** renamed to **SlimTubeSpecification** and expanded:

  * Added new properties: `ColumnPermeabilityMeasurementMethodID`, `ColumnPermeabilityFluidTypeID`, `ColumnOuterDiameter`, `ColumnInnerDiameter`, `ColumnFlowCrossSectionalArea`
  * `ColumnDiameter` split into `ColumnOuterDiameter` and `ColumnInnerDiameter`
  * `PackingMaterial` description expanded to include more materials and rationale for being a free string
* **SlimTubeTestSteps**:

  * Added new properties: `StepAverageTemperature`, `StepBackPressure`, `SlimTubeTestVolumeSteps`, `MaterialBalanceData`
  * `SlimTubeTestVolumeSteps` moved from root to inside each `SlimTubeTestSteps` item
* **SlimTubeTestVolumeSteps** (now nested under `SlimTubeTestSteps`):

  * Renamed `CumulativeOilProductionSTO` to `CumulativeOilProductionAtStockTankConditions`
  * Added: `CumulativeGasProductionAtStockTankConditions`, `CumulativeVaporCompositionalAnalysis`, `CumulativeLiquidCompositionalAnalysis`, `IncrementalVaporCompositionalAnalysis`, `IncrementalLiquidCompositionalAnalysis`, `InstantaneousVaporCompositionalAnalysis`, `InstantaneousLiquidCompositionalAnalysis`, `SeparatorTemperature`, `SeparatorPressure`
* **MaterialBalanceData** (now nested under `SlimTubeTestSteps`):

  * Replaced previous fields with a new, more detailed set: `MassOfReservoirOilInSlimTube`, `MassOfReservoirOilInConnectingLines`, `MassOfReservoirOil`, `MassOfGasSolvent`, `MassTotalInjected`, `MassOfEffluentStockTankOilBeforeBlowDown`, `MassOfProducedEffluentGasBeforeBlowDown`, `MassOfEffluentStockTankOilAfterBlowDown`, `MassOfProducedEffluentGasAfterBlowDown`, `MassOfResidualOil`, `MassTotalRecovered`, `WeightPercentRecovered`
* **InjectedGasID**: Injected gas used in this analysis, x-osdu-relation-ship: master-data--Sample.
* **InjectedGas**: Introduced as a new array capturing the composition and properties of injected gas. Each entry now contains `VaporSpecificGravity`, `VaporMolecularWeight`, and a nested `VaporComposition` array describing gas components and their composition properties.
* **CalculatedProperties.ResidueCalculatedProperties**: Added `ResidueMolecularWeight` and clarified descriptions.

## New Fields

* `InjectedGas` (array): Captures composition and properties of injected gas.
* `SlimTubeSpecification` (array): Replaces and expands on `PackedColumnProperties`.
* `SlimTubeTestSteps[*].SlimTubeTestVolumeSteps` (array): Now nested, with expanded compositional and production analysis.
* `SlimTubeTestSteps[*].MaterialBalanceData` (array): Now nested, with expanded detail.
* New compositional analysis arrays under `SlimTubeTestSteps[*].SlimTubeTestVolumeSteps`:

  * `CumulativeVaporCompositionalAnalysis`
  * `CumulativeLiquidCompositionalAnalysis`
  * `IncrementalVaporCompositionalAnalysis`
  * `IncrementalLiquidCompositionalAnalysis`
  * `InstantaneousVaporCompositionalAnalysis`
  * `InstantaneousLiquidCompositionalAnalysis`
* New properties in `SlimTubeTestSteps[*].SlimTubeTestVolumeSteps`:

  * `CumulativeGasProductionAtStockTankConditions`
  * `SeparatorTemperature`
  * `SeparatorPressure`

## Removed Fields

* `PackedColumnProperties` (replaced by `SlimTubeSpecification`)
* `CoreFlooding`
* `PackedColumnDisplacement`
* `VaporCompositionalAnalysis`
* `LiquidCompositionalAnalysis`
* Top-level `MaterialBalanceData` (now nested under `SlimTubeTestSteps`)
* Top-level `SlimTubeTestVolumeSteps` (now nested under `SlimTubeTestSteps`)
