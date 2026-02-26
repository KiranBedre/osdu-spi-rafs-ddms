# XRD v1.0.0 -> v2.0.0 Schema Changes

## Metadata
- `$id`: `xrd.1.0.0.json` → `xrd.2.0.0.json`
- `x-osdu-review-status`: `"Pending Review"` → `"Accepted"`
- `title`: `"Xrd Data Schema"` → `"XRD Data Schema"`

## Corrections
- `Meta.example`: corrected type from `""` (empty string) to `[]` (empty array)
- `QuartzCrystallinity.description`: simplified to "Measure of the degree of crystallinity of quartz in a sample by crystallite size and strain."
- `MineralContent.description`: minor wording correction ("in a rock sample" → "in sample")
- `MineralContent[*].WeightPercent.description`: "reported as a percentage of weight" → "reported in weight percent"
- `MineralContent[*].VolumePercent.description`: "reported as a percentage of volume" → "reported in volume percent"

## New Fields

| Field | Type | UOM |
|-------|------|-----|
| `IsClayFraction` | boolean | — |
| `ClayFractionCutoff` | number | length |
| `TotalClay` | number | mass per mass |
| `TotalPhyllosilicates` | number | mass per mass |
