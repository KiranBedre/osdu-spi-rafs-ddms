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


def seed_records(
    *,
    records: list[dict[str, Any]],
    storage_url: str,
    headers: dict[str, str],
    args: argparse.Namespace,
    report: dict[str, Any],
) -> None:
    records_url = f"{storage_url.rstrip('/')}/records"

    status, body = request(
        method="PUT",
        url=records_url,
        headers=headers,
        payload=records,
        retries=args.retries,
        retry_delay=args.retry_delay,
        timeout=args.timeout,
    )
    report["upload_http_status"] = status

    if not 200 <= status < 300:
        raise SeedError(f"Reference-data upload failed with HTTP {status}: " f"{response_message(body)}")

    if args.reactivate:
        for index, record in enumerate(records, start=1):
            record_id = record["id"]
            encoded_id = urllib.parse.quote(record_id, safe="")
            record_url = f"{records_url}/{encoded_id}"

            print(f"[{index}/{len(records)}] Reactivating {record_id}")
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

        print(f"Uploading {len(records)} reference-data records " f"to {args.storage_url}")
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
