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

"""Seed the schema subset required by RAFS through Schema Service."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

PUBLISHED_MESSAGES = {
    "Only schema in development stage can be updated",
    "Only schema in developement stage can be updated",
}
SCHEMA_EXISTS_MESSAGE = "Schema Id is already present"
RETRYABLE_CODES = {429, 500, 502, 503, 504}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema-dir", type=Path, required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--authority", default="osdu")
    parser.add_argument("--partition")
    parser.add_argument("--token-env", default="ACCESS_TOKEN")
    parser.add_argument("--report", type=Path, default=Path("schema-seed-report.json"))
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-delay", type=float, default=5.0)
    parser.add_argument("--insecure", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


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


def resolve_schema_file(schema_dir: Path, manifest_path: str, kind: str) -> Path:
    recorded = Path(manifest_path)
    candidates: list[Path] = []
    if not recorded.is_absolute():
        candidates.append(schema_dir / recorded)
    candidates.append(schema_dir / recorded.name)
    candidates.extend(schema_dir.rglob(recorded.name))

    matches: list[Path] = []
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate.is_file() and candidate not in matches:
            matches.append(candidate)
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one file for {kind} ({recorded.name}); " f"found {len(matches)}")
    return matches[0]


def put_schema(
    *,
    url: str,
    payload: bytes,
    headers: dict[str, str],
    context: ssl.SSLContext | None,
) -> tuple[int, str]:
    request = urllib.request.Request(url, data=payload, headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(request, context=context, timeout=120) as response:
            return response.status, response.read().decode(errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")


def write_report(path: Path, results: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "total": len(results),
        "succeeded": sum(item["result"] == "success" for item in results),
        "already_published": sum(item["result"] == "already_published" for item in results),
        "failed": sum(item["result"] == "failed" for item in results),
    }
    path.write_text(
        json.dumps({"summary": summary, "schemas": results}, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    schema_dir = args.schema_dir.resolve()
    manifest_file = schema_dir / "manifest.json"
    if not manifest_file.is_file():
        print(f"ERROR: manifest not found: {manifest_file}", file=sys.stderr)
        return 2

    token = os.environ.get(args.token_env, "")
    if not args.dry_run and not token:
        print(f"ERROR: {args.token_env} is not set", file=sys.stderr)
        return 2

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    order = manifest.get("dependency_order")
    files = manifest.get("files")
    if not isinstance(order, list) or not isinstance(files, dict):
        print("ERROR: invalid schema manifest", file=sys.stderr)
        return 2

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    if args.partition:
        headers["data-partition-id"] = args.partition

    context = ssl._create_unverified_context() if args.insecure else None
    results: list[dict[str, Any]] = []
    failed = False

    for index, kind in enumerate(order, start=1):
        try:
            schema_file = resolve_schema_file(schema_dir, files[kind], kind)
            source = schema_file.read_text(encoding="utf-8")
            rendered = source.replace("{{schema-authority}}", args.authority)
            json.loads(rendered)
        except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"ERROR: {kind}: {exc}", file=sys.stderr)
            results.append({"kind": kind, "result": "failed", "error": str(exc)})
            failed = True
            break

        print(f"[{index}/{len(order)}] {kind}")
        if args.dry_run:
            results.append({"kind": kind, "file": str(schema_file), "result": "success"})
            continue

        status = 0
        body = ""
        for attempt in range(1, args.retries + 1):
            try:
                status, body = put_schema(
                    url=args.url,
                    payload=rendered.encode(),
                    headers=headers,
                    context=context,
                )
            except (OSError, urllib.error.URLError) as exc:
                body = str(exc)
                status = 0

            if 200 <= status < 300:
                break
            message = response_message(body)
            retryable = status in RETRYABLE_CODES or message == SCHEMA_EXISTS_MESSAGE
            if not retryable or attempt == args.retries:
                break
            print(f"  HTTP {status}; retrying in {args.retry_delay:g}s")
            time.sleep(args.retry_delay)

        message = response_message(body)
        if 200 <= status < 300:
            result = "success"
        elif message in PUBLISHED_MESSAGES:
            result = "already_published"
        else:
            result = "failed"
            failed = True

        item = {
            "kind": kind,
            "file": str(schema_file),
            "http_status": status,
            "result": result,
        }
        if result == "failed":
            item["error"] = message[:2000]
        results.append(item)
        print(f"  HTTP {status}: {result}")
        if failed:
            break

    write_report(args.report, results)
    print(f"Report: {args.report}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
