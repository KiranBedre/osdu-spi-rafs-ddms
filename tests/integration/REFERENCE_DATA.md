# Integration reference data

The integration suite recursively discovers `reference-data--*` IDs from executable JSON payloads under `tests/integration/data`; schema files are excluded because their examples are not runtime prerequisites.

One xdist worker uses the existing cross-worker lock to check every discovered ID in Storage and create only missing records from `deployments/reference-data/rafs_integration_reference_data.json`. It rechecks Storage and reports all remaining missing IDs together. Prerequisite records and their persistent `RAFS-Integration-Reference-Data` legal tag are never deleted. Search is not preflighted because reference records are used for Storage referential integrity, not read through Search.

## Adding a dependency

1. Add the ID to a positive JSON payload.
2. Add its canonical record (kind, ACL/legal placeholders, and data) to the catalog.
3. Run `python -m pytest -q tests/integration/test_reference_data.py`.

For a positive dependency that cannot be represented in JSON, add it to `SUPPLEMENTAL_REFERENCE_IDS` with a short rationale.
