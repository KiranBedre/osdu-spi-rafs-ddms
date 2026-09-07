#!/usr/bin/env python3
"""Compare reference-data IDs used in integration fixtures vs the MVP manifest.

Scans tests/integration/data/v2 for OSDU reference-data IDs and reports which
ones are missing from deployments/rafsddms_ref_data_manifests_mvp.postman_collection.json.

Usage:
    python scripts/list_integration_reference_gaps.py
    python scripts/list_integration_reference_gaps.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "tests" / "integration" / "data" / "v2"
MANIFEST_PATH = REPO_ROOT / "deployments" / "rafsddms_ref_data_manifests_mvp.postman_collection.json"

# Match partition:reference-data--Type:Code (optional trailing version colon stripped later)
REF_ID_RE = re.compile(r"(?:\{data_partition_id\}|[\w\-\.]+):reference-data--([\w\-]+):([^\"'\s,}]+)")
MANIFEST_REF_RE = re.compile(r'reference-data--([\w\-]+):([^"\'\s,}]+)')


def _normalize_code(code: str) -> str:
    """Strip trailing version suffix and Postman placeholders noise."""
    code = code.rstrip(":")
    # Drop accidental truncation from escaped JSON fragments
    if code.endswith("\\"):
        code = code[:-1]
    return code


def collect_fixture_refs(fixtures_dir: Path) -> set[str]:
    refs: set[str] = set()
    for path in fixtures_dir.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        for type_name, code in REF_ID_RE.findall(text):
            code = _normalize_code(code)
            if code and not code.startswith("{"):
                refs.add(f"reference-data--{type_name}:{code}")
    return refs


def _walk_raw_bodies(items: list) -> str:
    chunks: list[str] = []
    for item in items:
        if "item" in item:
            chunks.append(_walk_raw_bodies(item["item"]))
        request = item.get("request") or {}
        body = request.get("body") or {}
        raw = body.get("raw") or ""
        if raw:
            chunks.append(raw)
    return "\n".join(chunks)


def collect_manifest_refs(manifest_path: Path) -> set[str]:
    collection = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw = _walk_raw_bodies(collection.get("item", []))
    refs: set[str] = set()
    for type_name, code in MANIFEST_REF_RE.findall(raw):
        code = _normalize_code(code)
        # Skip schema-looking codes like "1.0.0"
        if re.fullmatch(r"\d+\.\d+\.\d+", code):
            continue
        if code:
            refs.add(f"reference-data--{type_name}:{code}")
    return refs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a human report",
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=FIXTURES_DIR,
        help="Integration fixture root (default: tests/integration/data/v2)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=MANIFEST_PATH,
        help="MVP reference-data Postman collection path",
    )
    parser.add_argument(
        "--all-fixture-ids",
        action="store_true",
        help="Emit every reference-data ID used by integration fixtures",
    )
    args = parser.parse_args()

    fixture_refs = collect_fixture_refs(args.fixtures)
    manifest_refs = collect_manifest_refs(args.manifest)
    missing = sorted(fixture_refs - manifest_refs)
    covered = sorted(fixture_refs & manifest_refs)

    if args.all_fixture_ids:
        fixture_ids = sorted(fixture_refs)

        if args.json:
            print(json.dumps(fixture_ids, indent=2))
        else:
            for reference_id in fixture_ids:
                print(reference_id)

        return 0

    if args.json:
        print(
            json.dumps(
                {
                    "fixture_count": len(fixture_refs),
                    "manifest_count": len(manifest_refs),
                    "covered_count": len(covered),
                    "missing_count": len(missing),
                    "missing": missing,
                    "covered": covered,
                },
                indent=2,
            )
        )
    else:
        print(f"Fixture reference IDs: {len(fixture_refs)}")
        print(f"Manifest reference IDs: {len(manifest_refs)}")
        print(f"Covered by manifest:    {len(covered)}")
        print(f"Missing from manifest:  {len(missing)}")
        print()
        if missing:
            print("Missing (fixture ID not found in MVP manifest):")
            for ref in missing:
                print(f"  - {ref}")
        else:
            print("No gaps found.")

    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
