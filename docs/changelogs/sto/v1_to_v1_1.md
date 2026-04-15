# STO (Stock Tank Oil Analysis) v1.0.0 -> v1.1.0 Schema Changes

## Soft Deprecation

| Field | Change |
|-------|--------|
| `ParrafinContent` | Marked as `deprecated: true` (misspelled property key with double 'r') |

## New Fields

| Field | Type | Notes |
|-------|------|-------|
| `ParaffinContent` | `number` | Correctly spelled replacement for deprecated `ParrafinContent` |
