"""Discover and provision shared reference-data prerequisites for integration tests."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import quote

from loguru import logger
from starlette import status

REFERENCE_DATA_LEGAL_TAG = "RAFS-Integration-Reference-Data"
# Keep this empty unless a positive dependency is generated at runtime and cannot
# be represented in a JSON payload. Each entry must include a short rationale.
SUPPLEMENTAL_REFERENCE_IDS: dict[str, str] = {
    "{data_partition_id}:reference-data--DepthShiftInterpolationMethod:None": (
        "Created directly by the apply-depth-shift test payload."
    ),
    "{data_partition_id}:reference-data--FluidModelType:Compositional": (
        "Set directly by the compositional fluid-model fixtures."
    ),
    "{data_partition_id}:reference-data--FluidModelType:ThermalCompositional": (
        "Set directly by the thermal-compositional fluid-model fixtures."
    ),
    "{data_partition_id}:reference-data--VerticalMeasurementSource:LOG": (
        "Set directly by the apply-depth-shift test payload."
    ),
    "{data_partition_id}:reference-data--VerticalMeasurementType:SampleMean": (
        "Set directly by the apply-depth-shift test payload."
    ),
}
REFERENCE_ID_RE = re.compile(
    r"(?P<namespace>\{data_partition_id\}|[A-Za-z0-9_.-]+):"
    r"reference-data--(?P<kind>[A-Za-z0-9_-]+):"
    r"(?P<value>[A-Za-z0-9_.%/-]+(?::[A-Za-z0-9_.%/-]*)*)"
    r":?"
)


class ReferenceDataPreflightError(AssertionError):
    """Raised when the complete prerequisite set cannot be made available."""


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)


def _normalise_reference_id(match: re.Match[str], partition: str) -> str:
    namespace = match.group("namespace")
    if namespace == "{data_partition_id}":
        namespace = partition
    return f"{namespace}:reference-data--{match.group('kind')}:{match.group('value').rstrip(':')}"


def extract_reference_ids(value: Any, partition: str) -> set[str]:
    """Return deduplicated canonical IDs found in nested payload content."""
    found = set()
    for text in _walk_strings(value):
        for match in REFERENCE_ID_RE.finditer(text):
            reference_id = _normalise_reference_id(match, partition)
            if "{" not in reference_id:
                found.add(reference_id)
    return found


def discover_reference_ids(
    data_dir: Path,
    partition: str,
    supplemental_ids: Iterable[str] = (),
) -> set[str]:
    """Discover IDs from executable JSON payloads, excluding schema examples."""
    discovered = set()
    for path in sorted(data_dir.rglob("*.json")):
        if "schema" in path.name.lower():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ReferenceDataPreflightError(
                f"Could not read integration payload {path}: {error}"
            ) from error
        discovered.update(extract_reference_ids(payload, partition))
    discovered.update(
        reference_id.replace("{data_partition_id}", partition)
        for reference_id in supplemental_ids
    )
    return discovered


def _render(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, str):
        for source, replacement in replacements.items():
            value = value.replace(source, replacement)
        return value
    if isinstance(value, list):
        return [_render(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: _render(item, replacements) for key, item in value.items()}
    return value


def load_required_records(
    catalog_path: Path,
    required_ids: set[str],
    partition: str,
    owners_group: str,
    viewers_group: str,
) -> list[dict[str, Any]]:
    """Load canonical definitions and fail once for every uncovered dependency."""
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReferenceDataPreflightError(
            f"Could not read reference-data catalog {catalog_path}: {error}"
        ) from error

    rendered = _render(
        catalog,
        {
            "{{NAMESPACE}}": partition,
            "{{data-partition-id}}": partition,
            "{{DATA_OWNERS_GROUP}}": owners_group,
            "{{DATA_VIEWERS_GROUP}}": viewers_group,
            "{{LEGAL_TAG}}": REFERENCE_DATA_LEGAL_TAG,
            "{{ISO_3166_ALPHA_2_CODE}}": "US",
        },
    )
    records_by_id = {
        record.get("id"): record for record in rendered if isinstance(record, dict)
    }
    missing_definitions = sorted(required_ids - set(records_by_id))
    if missing_definitions:
        raise ReferenceDataPreflightError(
            "RAFS integration reference-data preflight failed.\n\n"
            "Missing canonical definitions:\n"
            + "\n".join(f"  - {reference_id}" for reference_id in missing_definitions)
        )
    return [records_by_id[reference_id] for reference_id in sorted(required_ids)]


def _storage_status(api, reference_id: str) -> int:
    response = api.storage.get(
        path=f"/records/{quote(reference_id, safe='')}",
        allowed_codes=[status.HTTP_200_OK, status.HTTP_404_NOT_FOUND],
    )
    return response.status_code


def load_available_records(
    catalog_path: Path,
    required_ids: set[str],
    partition: str,
    owners_group: str,
    viewers_group: str,
) -> tuple[list[dict[str, Any]], set[str]]:
    """Return catalogued requirements while retaining every undefined ID."""
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReferenceDataPreflightError(
            f"Could not read reference-data catalog {catalog_path}: {error}"
        ) from error
    rendered = _render(
        catalog,
        {
            "{{NAMESPACE}}": partition,
            "{{data-partition-id}}": partition,
            "{{DATA_OWNERS_GROUP}}": owners_group,
            "{{DATA_VIEWERS_GROUP}}": viewers_group,
            "{{LEGAL_TAG}}": REFERENCE_DATA_LEGAL_TAG,
            "{{ISO_3166_ALPHA_2_CODE}}": "US",
        },
    )
    records_by_id = {
        record.get("id"): record for record in rendered if isinstance(record, dict)
    }
    missing = required_ids - set(records_by_id)
    return [
        records_by_id[reference_id] for reference_id in sorted(required_ids - missing)
    ], missing


def _format_missing(
    missing_storage: set[str], missing_definitions: set[str] | None = None
) -> str:
    sections = ["RAFS integration reference-data preflight failed."]
    if missing_storage:
        sections.append(
            "Missing in Storage:\n"
            + "\n".join(f"  - {item}" for item in sorted(missing_storage))
        )
    if missing_definitions:
        sections.append(
            "Missing canonical definitions:\n"
            + "\n".join(f"  - {item}" for item in sorted(missing_definitions))
        )
    return "\n\n".join(sections)


def ensure_legal_tag(api) -> None:
    """Create the persistent prerequisite legal tag only when it is absent."""
    response = api.legal.get(
        path=f"/legaltags/{REFERENCE_DATA_LEGAL_TAG}",
        allowed_codes=[status.HTTP_200_OK, status.HTTP_404_NOT_FOUND],
    )
    if response.status_code == status.HTTP_200_OK:
        return
    body = {
        "name": REFERENCE_DATA_LEGAL_TAG,
        "description": "Persistent legal tag for RAFS integration reference-data prerequisites",
        "properties": {
            "contractId": "123456",
            "countryOfOrigin": ["US", "CA"],
            "dataType": "Public Domain Data",
            "exportClassification": "EAR99",
            "originator": "RAFS integration tests",
            "personalData": "No Personal Data",
            "securityClassification": "Private",
            "expirationDate": "2099-12-31",
        },
    }
    api.legal.post(
        path="/legaltags",
        json=body,
        allowed_codes=[status.HTTP_201_CREATED, status.HTTP_409_CONFLICT],
    )


def seed_required_reference_data(
    api,
    records: list[dict[str, Any]],
    before_seed: Callable[[], None] | None = None,
    missing_definitions: set[str] | None = None,
) -> dict[str, int]:
    """Idempotently create missing records, then aggregate Storage preflight failures."""
    record_ids = {record["id"] for record in records}
    existing = {
        record_id
        for record_id in record_ids
        if _storage_status(api, record_id) == status.HTTP_200_OK
    }
    missing_before = record_ids - existing
    if missing_before:
        if before_seed:
            before_seed()
        api.storage.create_or_update_records(
            [record for record in records if record["id"] in missing_before]
        )
    missing_after = {
        record_id
        for record_id in record_ids
        if _storage_status(api, record_id) != status.HTTP_200_OK
    }
    if missing_after or missing_definitions:
        raise ReferenceDataPreflightError(
            _format_missing(missing_after, missing_definitions)
        )
    result = {
        "inventory": len(record_ids),
        "existing": len(existing),
        "seeded": len(missing_before),
    }
    logger.info(
        "Reference-data preflight: inventory={inventory}, existing={existing}, seeded={seeded}",
        **result,
    )
    return result
