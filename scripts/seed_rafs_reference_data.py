#  Copyright 2026 ExxonMobil Technology and Engineering Company
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Seed the reference-data records required by RAFS through Storage Service."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any

import requests

RETRYABLE_CODES = {429, 500, 502, 503, 504}
ALREADY_ACTIVE_MESSAGE = "Record State already updated"
PLACEHOLDER_PATTERN = re.compile(r"\{\{[^}]+\}\}")


class SeedError(RuntimeError):
    """Raised when reference-data seeding cannot complete."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("deployments/reference-data/" "rafs_integration_reference_data.json"),
    )
    parser.add_argument("--storage-url", required=True)
    parser.add_argument(
        "--legal-url",
        help="Legal Service v1 base URL; omit to skip legal-tag creation",
    )
    parser.add_argument("--partition", required=True)
    parser.add_argument("--authority", default="osdu")
    parser.add_argument("--legal-tag", default="osdu-demo-legaltag")
    parser.add_argument("--country", default="US")
    parser.add_argument("--owners-group")
    parser.add_argument("--viewers-group")
    parser.add_argument("--token-env", default="ACCESS_TOKEN")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reference-data-seed-report.json"),
    )
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-delay", type=float, default=5.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--reactivate",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--verify",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def validate_service_url(url: str, name: str) -> None:
    """Reject URL schemes that could access local files or expose credentials."""
    try:
        parsed = urllib.parse.urlsplit(url)
        hostname = parsed.hostname
    except ValueError as exc:
        raise SeedError(f"{name} is invalid: {exc}") from exc

    if not hostname:
        raise SeedError(f"{name} must include a hostname")

    if parsed.username is not None or parsed.password is not None:
        raise SeedError(f"{name} must not include credentials")

    if parsed.scheme == "https":
        return

    local_hosts = {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme == "http" and hostname.lower() in local_hosts:
        return

    raise SeedError(f"{name} must use HTTPS; HTTP is allowed only for localhost")


def response_message(body: str) -> str:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body.strip()

    if not isinstance(payload, dict):
        return body.strip()

    error = payload.get("error")
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return error["message"]

    if isinstance(payload.get("message"), str):
        return payload["message"]

    return body.strip()


def render_placeholders(
    value: Any,
    replacements: dict[str, str],
) -> Any:
    if isinstance(value, str):
        for source, replacement in replacements.items():
            value = value.replace(source, replacement)
        return value

    if isinstance(value, list):
        return [render_placeholders(item, replacements) for item in value]

    if isinstance(value, dict):
        return {key: render_placeholders(item, replacements) for key, item in value.items()}

    return value


def load_catalog(
    path: Path,
    replacements: dict[str, str],
    authority: str,
) -> list[dict[str, Any]]:
    try:
        source = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SeedError(f"Could not load catalog {path}: {exc}") from exc

    rendered = render_placeholders(source, replacements)

    if not isinstance(rendered, list) or not rendered:
        raise SeedError("Reference-data catalog must be a non-empty array")

    ids: list[str] = []
    for index, record in enumerate(rendered):
        if not isinstance(record, dict):
            raise SeedError(f"Record {index} is not an object")

        record_id = record.get("id")
        kind = record.get("kind")

        if not isinstance(record_id, str) or ":reference-data--" not in record_id:
            raise SeedError(f"Record {index} has an invalid reference-data id")

        if not isinstance(kind, str) or not kind.startswith(f"{authority}:"):
            raise SeedError(f"Record {record_id} has an invalid kind")

        ids.append(record_id)

    duplicates = sorted(record_id for record_id in set(ids) if ids.count(record_id) > 1)
    if duplicates:
        raise SeedError("Catalog contains duplicate IDs: " + ", ".join(duplicates))

    unresolved = sorted(set(PLACEHOLDER_PATTERN.findall(json.dumps(rendered))))
    if unresolved:
        raise SeedError("Catalog contains unresolved placeholders: " + ", ".join(unresolved))

    return rendered


def request(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    payload: Any | None,
    retries: int,
    retry_delay: float,
    timeout: float,
) -> tuple[int, str]:
    status = 0
    body = ""

    for attempt in range(1, retries + 1):
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                json=payload,
                timeout=timeout,
                verify=True,
            )
            status = response.status_code
            body = response.text
        except requests.RequestException as exc:
            status = 0
            body = str(exc)

        if status not in RETRYABLE_CODES and status != 0:
            break

        if attempt < retries:
            print(f"  {method} {url}: HTTP {status}; " f"retrying in {retry_delay:g}s")
            time.sleep(retry_delay)

    return status, body


def ensure_legal_tag(
    *,
    legal_url: str,
    legal_tag: str,
    country: str,
    headers: dict[str, str],
    args: argparse.Namespace,
) -> int:
    payload = {
        "name": legal_tag,
        "description": ("Legal Tag added for RAFS DDMS integration tests"),
        "properties": {
            "contractId": "123456",
            "countryOfOrigin": [country],
            "dataType": "Public Domain Data",
            "exportClassification": "EAR99",
            "originator": "RAFS DDMS",
            "personalData": "No Personal Data",
            "securityClassification": "Private",
            "expirationDate": "2035-12-25",
        },
    }

    status, body = request(
        method="POST",
        url=f"{legal_url.rstrip('/')}/legaltags",
        headers=headers,
        payload=payload,
        retries=args.retries,
        retry_delay=args.retry_delay,
        timeout=args.timeout,
    )

    if status not in {200, 201, 409}:
        raise SeedError(f"Legal-tag creation failed with HTTP {status}: " f"{response_message(body)}")

    return status


def check_record_exists(
    *,
    record_id: str,
    records_url: str,
    headers: dict[str, str],
    args: argparse.Namespace,
) -> bool:
    """Return True if the record already exists, False if confirmed missing.

    Mirrors the safe check-then-create pattern already used by
    ``tests/integration/helpers/reference_data.py`` (``_storage_status`` /
    ``seed_required_reference_data``): only HTTP 200 is treated as "exists"
    and only HTTP 404 is treated as "missing". Any other outcome - auth
    failures, unexpected statuses, exhausted retries, or a network error
    (status 0 from ``request()``) - is a hard failure, never silently
    treated as "missing". The id is percent-encoded with ``quote(id,
    safe="")`` for the URL path, matching the convention already used below
    for the reactivation PATCH/GET calls and documented in
    ``tests/test_api/unit/services/clients/storage_client_test.py``.

    :raises SeedError: if the existence check does not return 200 or 404.
    """
    encoded_id = urllib.parse.quote(record_id, safe="")
    url = f"{records_url}/{encoded_id}"

    status, body = request(
        method="GET",
        url=url,
        headers=headers,
        payload=None,
        retries=args.retries,
        retry_delay=args.retry_delay,
        timeout=args.timeout,
    )

    if status == 200:
        return True
    if status == 404:
        return False
    raise SeedError(f"Existence check failed for {record_id}: HTTP {status}: {response_message(body)}")


def validate_bulk_creation_response(
    *,
    submitted_ids: set[str],
    response_payload: Any,
) -> tuple[set[str], set[str]]:
    """Validate a Storage PUT /records response and return (created_ids, skipped_ids).

    Every id in ``submitted_ids`` must be accounted for in exactly one of
    ``recordIds`` (confirmed created) or ``skippedRecordIds`` (explicitly
    skipped) - never both, never neither - and the response must not
    reference ids that were never submitted. A malformed or inconsistent
    batch response is never safe to interpret as "it worked": any violation
    raises SeedError naming the exact ids involved.

    :raises SeedError: if the response is malformed, missing either field,
        or inconsistent with ``submitted_ids`` in any way.
    """
    if not isinstance(response_payload, dict):
        raise SeedError("Reference-data creation response was not a JSON object")

    record_ids_field = response_payload.get("recordIds")
    skipped_field = response_payload.get("skippedRecordIds")

    if not isinstance(record_ids_field, list) or not all(isinstance(x, str) for x in record_ids_field):
        raise SeedError("Reference-data creation response is missing a valid 'recordIds' list")
    if not isinstance(skipped_field, list) or not all(isinstance(x, str) for x in skipped_field):
        raise SeedError("Reference-data creation response is missing a valid 'skippedRecordIds' list")

    if len(record_ids_field) != len(set(record_ids_field)):
        raise SeedError("Reference-data creation response contains duplicate entries within 'recordIds'")
    if len(skipped_field) != len(set(skipped_field)):
        raise SeedError("Reference-data creation response contains duplicate entries within 'skippedRecordIds'")

    created_ids = set(record_ids_field)
    skipped_ids = set(skipped_field)

    overlap = created_ids & skipped_ids
    if overlap:
        raise SeedError(
            "Reference-data creation response lists the same id(s) in both "
            "'recordIds' and 'skippedRecordIds': " + ", ".join(sorted(overlap))
        )

    unknown_ids = (created_ids | skipped_ids) - submitted_ids
    if unknown_ids:
        raise SeedError(
            "Reference-data creation response references id(s) that were not submitted: "
            + ", ".join(sorted(unknown_ids))
        )

    unaccounted_ids = submitted_ids - created_ids - skipped_ids
    if unaccounted_ids:
        raise SeedError(
            "Reference-data creation response does not account for submitted id(s) "
            "(neither created nor skipped): " + ", ".join(sorted(unaccounted_ids))
        )

    return created_ids, skipped_ids


def seed_records(
    *,
    records: list[dict[str, Any]],
    storage_url: str,
    headers: dict[str, str],
    args: argparse.Namespace,
    report: dict[str, Any],
) -> None:
    records_url = f"{storage_url.rstrip('/')}/records"

    # Check-then-create: never PUT a record that already exists. A failed
    # existence check raises immediately (see check_record_exists), so a
    # single bad check aborts here, before any PUT is attempted - it cannot
    # fall through into an unconditional bulk upload.
    #
    # KNOWN LIMITATION (TOCTOU race, documented not solved): between this GET
    # and the PUT below, another concurrent process (another seeding run, a
    # Postman/CI run, a manual edit) could create or delete the same record.
    # This script has no cross-process lock equivalent to the pytest
    # fixtures' FileLock (tests/integration/helpers/parallel_execution.py),
    # so that window cannot be fully closed from here.
    print(f"Checking existence of {len(records)} reference-data records")
    existing_ids: set[str] = set()
    for index, record in enumerate(records, start=1):
        record_id = record["id"]
        if check_record_exists(
            record_id=record_id,
            records_url=records_url,
            headers=headers,
            args=args,
        ):
            existing_ids.add(record_id)
        state = "exists - will not be modified" if record_id in existing_ids else "missing - eligible for creation"
        print(f"[{index}/{len(records)}] {record_id}: {state}")

    report["existing"] = len(existing_ids)
    missing_records = [record for record in records if record["id"] not in existing_ids]
    report["missing"] = len(missing_records)

    if not missing_records:
        print("All reference-data records already exist; nothing to create.")
        report["created"] = 0
        report["upload_http_status"] = None
        report["skipped_in_response"] = []
        return

    print(f"Creating {len(missing_records)} missing reference-data records")
    status, body = request(
        method="PUT",
        url=records_url,
        headers=headers,
        payload=missing_records,
        retries=args.retries,
        retry_delay=args.retry_delay,
        timeout=args.timeout,
    )
    report["upload_http_status"] = status

    if not 200 <= status < 300:
        raise SeedError(f"Reference-data creation failed with HTTP {status}: " f"{response_message(body)}")

    # Validate the batch-ingestion response before trusting it: a record is
    # only ever counted as created if Storage's own "recordIds" explicitly
    # confirms it. "skippedRecordIds" is itself a valid, safe outcome (e.g.
    # the TOCTOU race documented above resolving safely - Storage declined
    # to touch a record that showed up concurrently), but anything the
    # response can't account for cleanly - malformed fields, duplicates,
    # overlap between the two lists, unknown ids, or submitted ids missing
    # from both lists - raises SeedError rather than being assumed safe.
    try:
        response_payload = json.loads(body) if body else {}
    except json.JSONDecodeError as exc:
        raise SeedError(f"Reference-data creation response was not valid JSON: {exc}") from exc

    submitted_ids = {record["id"] for record in missing_records}
    created_ids, skipped_ids = validate_bulk_creation_response(
        submitted_ids=submitted_ids,
        response_payload=response_payload,
    )

    report["skipped_in_response"] = sorted(skipped_ids)
    if skipped_ids:
        print(
            f"WARNING: Storage reported {len(skipped_ids)} record(s) skipped during creation: "
            f"{sorted(skipped_ids)}"
        )

    # Never PATCH or verify a record unless its creation was explicitly
    # confirmed via "recordIds" above.
    created_records = [record for record in missing_records if record["id"] in created_ids]
    report["created"] = len(created_records)

    if args.reactivate:
        # Only the records actually just created may need post-creation
        # steps. Records already confirmed to exist above, and records
        # Storage itself reported as skipped, are never touched again.
        for index, record in enumerate(created_records, start=1):
            record_id = record["id"]
            encoded_id = urllib.parse.quote(record_id, safe="")
            record_url = f"{records_url}/{encoded_id}"

            print(f"[{index}/{len(created_records)}] Reactivating {record_id}")
            patch_status, patch_body = request(
                method="PATCH",
                url=record_url,
                headers={
                    **headers,
                    "Content-Type": "application/merge-patch+json",
                },
                payload={"deleted": False},
                retries=args.retries,
                retry_delay=args.retry_delay,
                timeout=args.timeout,
            )

            already_active = patch_status == 400 and response_message(patch_body) == ALREADY_ACTIVE_MESSAGE
            if patch_status not in {200, 204} and not already_active:
                raise SeedError(
                    f"Could not reactivate {record_id}: " f"HTTP {patch_status}: " f"{response_message(patch_body)}"
                )

            report["reactivated"] += 1

            if args.verify:
                verify_status, verify_body = request(
                    method="GET",
                    url=record_url,
                    headers=headers,
                    payload=None,
                    retries=args.retries,
                    retry_delay=args.retry_delay,
                    timeout=args.timeout,
                )
                if verify_status != 200:
                    raise SeedError(
                        f"Verification failed for {record_id}: "
                        f"HTTP {verify_status}: "
                        f"{response_message(verify_body)}"
                    )

                report["verified"] += 1


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    report: dict[str, Any] = {
        "catalog": str(args.catalog),
        "partition": args.partition,
        "authority": args.authority,
        "result": "failed",
        "total": 0,
        "existing": 0,
        "missing": 0,
        "created": 0,
        "skipped_in_response": [],
        "reactivated": 0,
        "verified": 0,
    }

    try:
        owners_group = args.owners_group or f"data.default.owners@{args.partition}.group"
        viewers_group = args.viewers_group or f"data.default.viewers@{args.partition}.group"

        replacements = {
            "{{NAMESPACE}}": args.partition,
            "{{data-partition-id}}": args.partition,
            "{{DATA_OWNERS_GROUP}}": owners_group,
            "{{DATA_VIEWERS_GROUP}}": viewers_group,
            "{{LEGAL_TAG}}": args.legal_tag,
            "{{ISO_3166_ALPHA_2_CODE}}": args.country,
            "{{rafsddms-schema-authority}}": args.authority,
            "{{schema-authority}}": args.authority,
        }

        records = load_catalog(
            args.catalog.resolve(),
            replacements,
            args.authority,
        )
        report["total"] = len(records)

        if args.dry_run:
            report["result"] = "success"
            report["dry_run"] = True
            print(f"Validated {len(records)} reference-data records")
            return 0

        validate_service_url(args.storage_url, "Storage Service URL")
        if args.legal_url:
            validate_service_url(args.legal_url, "Legal Service URL")

        token = os.environ.get(args.token_env, "")
        if not token:
            raise SeedError(f"{args.token_env} is not set")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "data-partition-id": args.partition,
        }
        if args.legal_url:
            print(f"Ensuring legal tag {args.legal_tag} exists")
            report["legal_tag_http_status"] = ensure_legal_tag(
                legal_url=args.legal_url,
                legal_tag=args.legal_tag,
                country=args.country,
                headers=headers,
                args=args,
            )

        print(f"Seeding {len(records)} reference-data records (create-if-missing) " f"against {args.storage_url}")
        seed_records(
            records=records,
            storage_url=args.storage_url,
            headers=headers,
            args=args,
            report=report,
        )
        report["result"] = "success"
        return 0

    except SeedError as exc:
        report["error"] = str(exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    finally:
        write_report(args.report, report)
        print(f"Report: {args.report}")


if __name__ == "__main__":
    raise SystemExit(main())
