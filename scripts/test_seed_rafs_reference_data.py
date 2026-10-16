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

"""Unit tests for scripts/seed_rafs_reference_data.py's create-if-missing behavior.

Every HTTP call is mocked at the `requests.request` boundary. No test in this
file makes a real network call.
"""

from __future__ import annotations

import json
import urllib.parse
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import requests

from scripts import seed_rafs_reference_data as seed_module
from scripts.seed_rafs_reference_data import SeedError, check_record_exists, seed_records

STORAGE_URL = "https://fake-storage.example.com/api/storage/v2"
RECORDS_URL = f"{STORAGE_URL}/records"
HEADERS = {"Authorization": "Bearer fake-token", "Content-Type": "application/json", "data-partition-id": "opendes"}

# A plain id and a percent-encoded one (mirrors the authoritative convention,
# e.g. UnitOfMeasure:1/Pa -> UnitOfMeasure:1%2FPa, confirmed against
# C:\\work\\ref_data in the Postman-collection investigation).
PLAIN_ID = "opendes:reference-data--UnitOfMeasure:m"
ENCODED_ID = "opendes:reference-data--UnitOfMeasure:1%2FPa"


def make_args(**overrides) -> SimpleNamespace:
    defaults = dict(retries=3, retry_delay=0, timeout=5.0, reactivate=True, verify=True)
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_record(record_id: str) -> dict:
    return {
        "id": record_id,
        "kind": "osdu:wks:reference-data--UnitOfMeasure:1.0.0",
        "acl": {"viewers": ["v@opendes"], "owners": ["o@opendes"]},
        "legal": {"legaltags": ["opendes-demo-legaltag"], "otherRelevantDataCountries": ["US"]},
        "data": {"Code": record_id.rsplit(":", 1)[-1]},
    }


def fake_response(status_code: int, body: object = "") -> SimpleNamespace:
    text = body if isinstance(body, str) else json.dumps(body)
    return SimpleNamespace(status_code=status_code, text=text)


class ScriptedTransport:
    """Replays a scripted sequence of outcomes per (method, url), FIFO per key.

    Each outcome is either a (status_code, body) pair, or an Exception
    instance/class to raise (to simulate a network failure/timeout). Calls
    are recorded for assertions.
    """

    def __init__(self):
        self.scripts: dict[tuple[str, str], list] = {}
        self.calls: list[dict] = []

    def script(self, method: str, url: str, outcomes: list):
        self.scripts[(method, url)] = list(outcomes)

    def __call__(self, method, url, headers=None, json=None, timeout=None, verify=None):
        self.calls.append({"method": method, "url": url, "headers": headers, "json": json})
        key = (method, url)
        queue = self.scripts.get(key)
        if not queue:
            raise AssertionError(f"No scripted outcome left for {method} {url}")
        outcome = queue.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, type) and issubclass(outcome, Exception):
            raise outcome("scripted failure")
        status_code, body = outcome
        return fake_response(status_code, body)


def existing_get_url(record_id: str) -> str:
    return f"{RECORDS_URL}/{urllib.parse.quote(record_id, safe='')}"


# ---------------------------------------------------------------------------
# check_record_exists
# ---------------------------------------------------------------------------


def test_check_record_exists_true_on_200():
    transport = ScriptedTransport()
    transport.script("GET", existing_get_url(PLAIN_ID), [(200, {"id": PLAIN_ID})])
    with patch.object(seed_module.requests, "request", side_effect=transport):
        assert check_record_exists(record_id=PLAIN_ID, records_url=RECORDS_URL, headers=HEADERS, args=make_args()) is True


def test_check_record_exists_false_on_404():
    transport = ScriptedTransport()
    transport.script("GET", existing_get_url(PLAIN_ID), [(404, {"error": "not found"})])
    with patch.object(seed_module.requests, "request", side_effect=transport):
        assert check_record_exists(record_id=PLAIN_ID, records_url=RECORDS_URL, headers=HEADERS, args=make_args()) is False


@pytest.mark.parametrize("status", [401, 403, 500])
def test_check_record_exists_raises_on_non_200_404(status):
    """401/403/exhausted-500 must raise, never be treated as missing."""
    transport = ScriptedTransport()
    # retries=1 so a non-retryable or exhausted-retryable status surfaces immediately.
    transport.script("GET", existing_get_url(PLAIN_ID), [(status, {"message": "nope"})])
    with patch.object(seed_module.requests, "request", side_effect=transport):
        with pytest.raises(SeedError, match="Existence check failed"):
            check_record_exists(
                record_id=PLAIN_ID, records_url=RECORDS_URL, headers=HEADERS, args=make_args(retries=1)
            )


def test_check_record_exists_percent_encoded_id_is_double_encoded_on_wire():
    """The id already contains %2F; the client must encode the WHOLE string
    again (quote(id, safe="")) so the server's single decode pass lands on
    the correct canonical form - mirroring tests/integration/helpers/
    reference_data.py's _storage_status and storage_client.py's
    _encode_record_id, both verified against the real 400 seen in production.
    """
    transport = ScriptedTransport()
    expected_url = existing_get_url(ENCODED_ID)
    transport.script("GET", expected_url, [(200, {"id": ENCODED_ID})])
    with patch.object(seed_module.requests, "request", side_effect=transport):
        result = check_record_exists(record_id=ENCODED_ID, records_url=RECORDS_URL, headers=HEADERS, args=make_args())
    assert result is True
    sent_url = transport.calls[0]["url"]
    assert sent_url == expected_url
    # the literal '%' in the id must itself have been escaped to %25
    assert "%252F" in sent_url


# ---------------------------------------------------------------------------
# seed_records: core create-if-missing behavior
# ---------------------------------------------------------------------------


def test_all_records_already_exist_zero_put_patch():
    records = [make_record(PLAIN_ID), make_record(ENCODED_ID)]
    transport = ScriptedTransport()
    for r in records:
        transport.script("GET", existing_get_url(r["id"]), [(200, {"id": r["id"]})])

    report = {"reactivated": 0, "verified": 0}
    with patch.object(seed_module.requests, "request", side_effect=transport):
        seed_records(records=records, storage_url=STORAGE_URL, headers=HEADERS, args=make_args(), report=report)

    assert report["existing"] == 2
    assert report["missing"] == 0
    assert report["created"] == 0
    assert report["upload_http_status"] is None
    put_or_patch_calls = [c for c in transport.calls if c["method"] in ("PUT", "PATCH")]
    assert put_or_patch_calls == []


def test_all_records_missing_creates_them():
    records = [make_record(PLAIN_ID), make_record(ENCODED_ID)]
    transport = ScriptedTransport()
    for r in records:
        transport.script("GET", existing_get_url(r["id"]), [(404, {"error": "not found"})])
    transport.script("PUT", RECORDS_URL, [(201, {"recordIds": [r["id"] for r in records], "skippedRecordIds": []})])
    for r in records:
        transport.script("PATCH", existing_get_url(r["id"]), [(200, {})])
        # Verify GETs reuse the same URL as the existence-check GET; append a
        # second 200 for each, since ScriptedTransport is FIFO per key.
        transport.scripts[("GET", existing_get_url(r["id"]))].append((200, {"id": r["id"]}))

    report = {"reactivated": 0, "verified": 0}
    with patch.object(seed_module.requests, "request", side_effect=transport):
        seed_records(records=records, storage_url=STORAGE_URL, headers=HEADERS, args=make_args(), report=report)

    assert report["existing"] == 0
    assert report["missing"] == 2
    assert report["created"] == 2
    assert report["upload_http_status"] == 201
    assert report["reactivated"] == 2
    assert report["verified"] == 2
    put_calls = [c for c in transport.calls if c["method"] == "PUT"]
    assert len(put_calls) == 1
    assert sorted(rec["id"] for rec in put_calls[0]["json"]) == sorted(r["id"] for r in records)


def test_mixed_existing_and_missing_creates_only_missing():
    existing_record = make_record(PLAIN_ID)
    missing_record = make_record(ENCODED_ID)
    transport = ScriptedTransport()
    transport.script("GET", existing_get_url(PLAIN_ID), [(200, {"id": PLAIN_ID})])
    transport.script("GET", existing_get_url(ENCODED_ID), [(404, {"error": "not found"})])
    transport.script("PUT", RECORDS_URL, [(201, {"recordIds": [ENCODED_ID], "skippedRecordIds": []})])
    transport.script("PATCH", existing_get_url(ENCODED_ID), [(200, {})])
    transport.scripts[("GET", existing_get_url(ENCODED_ID))].append((200, {"id": ENCODED_ID}))

    report = {"reactivated": 0, "verified": 0}
    with patch.object(seed_module.requests, "request", side_effect=transport):
        seed_records(
            records=[existing_record, missing_record],
            storage_url=STORAGE_URL,
            headers=HEADERS,
            args=make_args(),
            report=report,
        )

    assert report["existing"] == 1
    assert report["missing"] == 1
    assert report["created"] == 1
    put_calls = [c for c in transport.calls if c["method"] == "PUT"]
    assert len(put_calls) == 1
    assert [rec["id"] for rec in put_calls[0]["json"]] == [ENCODED_ID]
    # the already-existing record must never appear in any PUT/PATCH body or URL
    patch_calls = [c for c in transport.calls if c["method"] == "PATCH"]
    assert all(PLAIN_ID not in c["url"] for c in patch_calls)


# ---------------------------------------------------------------------------
# Failure handling: auth, server errors, transient failures, timeouts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", [401, 403])
def test_auth_failure_fails_safely_no_put(status):
    records = [make_record(PLAIN_ID)]
    transport = ScriptedTransport()
    transport.script("GET", existing_get_url(PLAIN_ID), [(status, {"message": "unauthorized"})])

    report = {"reactivated": 0, "verified": 0}
    with patch.object(seed_module.requests, "request", side_effect=transport):
        with pytest.raises(SeedError):
            seed_records(
                records=records, storage_url=STORAGE_URL, headers=HEADERS, args=make_args(retries=1), report=report
            )

    assert all(c["method"] != "PUT" for c in transport.calls)
    assert all(c["method"] != "PATCH" for c in transport.calls)


def test_http_500_retries_then_succeeds():
    records = [make_record(PLAIN_ID)]
    transport = ScriptedTransport()
    # two transient 500s then a 404 (confirmed missing) on the 3rd attempt
    transport.script(
        "GET",
        existing_get_url(PLAIN_ID),
        [(500, {"message": "boom"}), (500, {"message": "boom"}), (404, {"error": "not found"})],
    )
    transport.script("PUT", RECORDS_URL, [(201, {"recordIds": [PLAIN_ID], "skippedRecordIds": []})])
    transport.script("PATCH", existing_get_url(PLAIN_ID), [(200, {})])
    transport.scripts[("GET", existing_get_url(PLAIN_ID))].append((200, {"id": PLAIN_ID}))

    report = {"reactivated": 0, "verified": 0}
    with patch.object(seed_module.requests, "request", side_effect=transport):
        seed_records(
            records=records, storage_url=STORAGE_URL, headers=HEADERS, args=make_args(retries=3), report=report
        )

    assert report["created"] == 1
    get_calls = [c for c in transport.calls if c["method"] == "GET" and c["url"] == existing_get_url(PLAIN_ID)]
    assert len(get_calls) >= 3  # the two 500s were retried


def test_http_500_exhausted_retries_fails_safely():
    records = [make_record(PLAIN_ID)]
    transport = ScriptedTransport()
    transport.script("GET", existing_get_url(PLAIN_ID), [(500, {}), (500, {})])

    report = {"reactivated": 0, "verified": 0}
    with patch.object(seed_module.requests, "request", side_effect=transport):
        with pytest.raises(SeedError, match="Existence check failed"):
            seed_records(
                records=records, storage_url=STORAGE_URL, headers=HEADERS, args=make_args(retries=2), report=report
            )

    assert all(c["method"] != "PUT" for c in transport.calls)


def test_network_timeout_fails_safely_not_treated_as_missing():
    records = [make_record(PLAIN_ID)]
    transport = ScriptedTransport()
    transport.script(
        "GET",
        existing_get_url(PLAIN_ID),
        [requests.exceptions.Timeout("timed out"), requests.exceptions.Timeout("timed out")],
    )

    report = {"reactivated": 0, "verified": 0}
    with patch.object(seed_module.requests, "request", side_effect=transport):
        with pytest.raises(SeedError, match="Existence check failed"):
            seed_records(
                records=records, storage_url=STORAGE_URL, headers=HEADERS, args=make_args(retries=2), report=report
            )

    assert all(c["method"] != "PUT" for c in transport.calls)


def test_a_single_failed_check_aborts_before_any_put_even_with_other_missing_records():
    """Requirement: a failed existence check cannot fall through into an
    unconditional bulk PUT, even when other records in the same catalog were
    already confirmed missing earlier in the loop."""
    first_missing = make_record(PLAIN_ID)
    second_bad = make_record(ENCODED_ID)
    transport = ScriptedTransport()
    transport.script("GET", existing_get_url(PLAIN_ID), [(404, {"error": "not found"})])
    transport.script("GET", existing_get_url(ENCODED_ID), [(500, {}), (500, {})])

    report = {"reactivated": 0, "verified": 0}
    with patch.object(seed_module.requests, "request", side_effect=transport):
        with pytest.raises(SeedError):
            seed_records(
                records=[first_missing, second_bad],
                storage_url=STORAGE_URL,
                headers=HEADERS,
                args=make_args(retries=2),
                report=report,
            )

    assert all(c["method"] != "PUT" for c in transport.calls)


# ---------------------------------------------------------------------------
# Partial bulk-ingestion failure
# ---------------------------------------------------------------------------


def test_partial_bulk_ingestion_response_is_recorded_not_fatal():
    records = [make_record(PLAIN_ID), make_record(ENCODED_ID)]
    transport = ScriptedTransport()
    for r in records:
        transport.script("GET", existing_get_url(r["id"]), [(404, {"error": "not found"})])
    # Storage reports success overall but skipped one id (e.g. created
    # concurrently between our GET and this PUT - the TOCTOU race resolving safely).
    transport.script(
        "PUT",
        RECORDS_URL,
        [(201, {"recordIds": [PLAIN_ID], "skippedRecordIds": [ENCODED_ID]})],
    )
    # Only the non-skipped record (PLAIN_ID) should be reactivated/verified.
    transport.script("PATCH", existing_get_url(PLAIN_ID), [(200, {})])
    transport.scripts[("GET", existing_get_url(PLAIN_ID))].append((200, {"id": PLAIN_ID}))

    report = {"reactivated": 0, "verified": 0}
    with patch.object(seed_module.requests, "request", side_effect=transport):
        seed_records(
            records=records, storage_url=STORAGE_URL, headers=HEADERS, args=make_args(), report=report
        )

    assert report["skipped_in_response"] == [ENCODED_ID]
    assert report["created"] == 1  # the skipped id is excluded from the created count
    assert report["reactivated"] == 1
    patch_calls = [c for c in transport.calls if c["method"] == "PATCH"]
    assert len(patch_calls) == 1
    assert ENCODED_ID not in patch_calls[0]["url"]


def test_bulk_put_hard_failure_raises():
    records = [make_record(PLAIN_ID)]
    transport = ScriptedTransport()
    transport.script("GET", existing_get_url(PLAIN_ID), [(404, {"error": "not found"})])
    transport.script("PUT", RECORDS_URL, [(500, {"message": "server exploded"})])

    report = {"reactivated": 0, "verified": 0}
    with patch.object(seed_module.requests, "request", side_effect=transport):
        with pytest.raises(SeedError, match="Reference-data creation failed"):
            seed_records(
                records=records, storage_url=STORAGE_URL, headers=HEADERS, args=make_args(retries=1), report=report
            )


# ---------------------------------------------------------------------------
# validate_bulk_creation_response: inconsistent/malformed Storage responses
#
# A record is only ever counted as created if it is explicitly present in
# "recordIds". Anything the response can't cleanly account for must raise,
# never be silently assumed safe.
# ---------------------------------------------------------------------------


def test_validate_response_missing_record_ids_field():
    """Missing recordIds field entirely."""
    with pytest.raises(SeedError, match="missing a valid 'recordIds'"):
        seed_module.validate_bulk_creation_response(
            submitted_ids={PLAIN_ID},
            response_payload={"skippedRecordIds": []},
        )


def test_validate_response_submitted_id_absent_from_both_lists():
    """Submitted ID present in neither recordIds nor skippedRecordIds."""
    with pytest.raises(SeedError, match="does not account for submitted"):
        seed_module.validate_bulk_creation_response(
            submitted_ids={PLAIN_ID, ENCODED_ID},
            response_payload={"recordIds": [PLAIN_ID], "skippedRecordIds": []},
        )


def test_validate_response_same_id_in_both_lists():
    """Same ID reported in both recordIds and skippedRecordIds."""
    with pytest.raises(SeedError, match="both"):
        seed_module.validate_bulk_creation_response(
            submitted_ids={PLAIN_ID},
            response_payload={"recordIds": [PLAIN_ID], "skippedRecordIds": [PLAIN_ID]},
        )


def test_validate_response_unexpected_id_in_response():
    """Response references an id that was never submitted."""
    unexpected_id = "opendes:reference-data--UnitOfMeasure:never-submitted"
    with pytest.raises(SeedError, match="not submitted"):
        seed_module.validate_bulk_creation_response(
            submitted_ids={PLAIN_ID},
            response_payload={"recordIds": [PLAIN_ID, unexpected_id], "skippedRecordIds": []},
        )


def test_validate_response_valid_partial_success():
    """Every submitted id accounted for exactly once - the happy partial case."""
    created_ids, skipped_ids = seed_module.validate_bulk_creation_response(
        submitted_ids={PLAIN_ID, ENCODED_ID},
        response_payload={"recordIds": [PLAIN_ID], "skippedRecordIds": [ENCODED_ID]},
    )
    assert created_ids == {PLAIN_ID}
    assert skipped_ids == {ENCODED_ID}


def test_validate_response_duplicate_entries_within_record_ids():
    """Malformed: the same id listed twice within recordIds itself."""
    with pytest.raises(SeedError, match="duplicate entries"):
        seed_module.validate_bulk_creation_response(
            submitted_ids={PLAIN_ID},
            response_payload={"recordIds": [PLAIN_ID, PLAIN_ID], "skippedRecordIds": []},
        )


def test_validate_response_non_string_entries_are_malformed():
    """Malformed: recordIds contains a non-string entry."""
    with pytest.raises(SeedError, match="missing a valid 'recordIds'"):
        seed_module.validate_bulk_creation_response(
            submitted_ids={PLAIN_ID},
            response_payload={"recordIds": [123], "skippedRecordIds": []},
        )


def test_validate_response_not_a_json_object():
    """Malformed: response body parses to a list/scalar, not an object."""
    with pytest.raises(SeedError, match="not a JSON object"):
        seed_module.validate_bulk_creation_response(
            submitted_ids={PLAIN_ID},
            response_payload=["unexpected", "array"],
        )


def test_seed_records_aborts_before_reactivate_on_inconsistent_response():
    """End-to-end: an inconsistent PUT response must abort before any
    PATCH/verify - creation is never assumed just because the HTTP status
    was 2xx."""
    records = [make_record(PLAIN_ID), make_record(ENCODED_ID)]
    transport = ScriptedTransport()
    for r in records:
        transport.script("GET", existing_get_url(r["id"]), [(404, {"error": "not found"})])
    # ENCODED_ID is submitted but accounted for in neither list.
    transport.script("PUT", RECORDS_URL, [(201, {"recordIds": [PLAIN_ID], "skippedRecordIds": []})])

    report = {"reactivated": 0, "verified": 0}
    with patch.object(seed_module.requests, "request", side_effect=transport):
        with pytest.raises(SeedError, match="does not account for submitted"):
            seed_records(
                records=records, storage_url=STORAGE_URL, headers=HEADERS, args=make_args(), report=report
            )

    assert all(c["method"] != "PATCH" for c in transport.calls)


# ---------------------------------------------------------------------------
# Repeated execution (idempotency) - no modification of existing records
# ---------------------------------------------------------------------------


def test_repeated_execution_does_not_modify_existing_records():
    records = [make_record(PLAIN_ID)]

    # First run: record is missing, gets created.
    transport1 = ScriptedTransport()
    transport1.script("GET", existing_get_url(PLAIN_ID), [(404, {"error": "not found"})])
    transport1.script("PUT", RECORDS_URL, [(201, {"recordIds": [PLAIN_ID], "skippedRecordIds": []})])
    transport1.script("PATCH", existing_get_url(PLAIN_ID), [(200, {})])
    transport1.scripts[("GET", existing_get_url(PLAIN_ID))].append((200, {"id": PLAIN_ID}))

    report1 = {"reactivated": 0, "verified": 0}
    with patch.object(seed_module.requests, "request", side_effect=transport1):
        seed_records(records=records, storage_url=STORAGE_URL, headers=HEADERS, args=make_args(), report=report1)
    assert report1["created"] == 1

    # Second run against the same (now-existing) record: must be a pure read,
    # zero PUT/PATCH calls.
    transport2 = ScriptedTransport()
    transport2.script("GET", existing_get_url(PLAIN_ID), [(200, {"id": PLAIN_ID})])

    report2 = {"reactivated": 0, "verified": 0}
    with patch.object(seed_module.requests, "request", side_effect=transport2):
        seed_records(records=records, storage_url=STORAGE_URL, headers=HEADERS, args=make_args(), report=report2)

    assert report2["existing"] == 1
    assert report2["created"] == 0
    assert all(c["method"] in ("GET",) for c in transport2.calls)


# ---------------------------------------------------------------------------
# main(): CLI/report/exit-code behavior
# ---------------------------------------------------------------------------


def _write_catalog(tmp_path, records):
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(records), encoding="utf-8")
    return catalog_path


def _run_main(monkeypatch, argv_extra):
    argv = [
        "seed_rafs_reference_data.py",
        "--storage-url",
        STORAGE_URL,
        "--partition",
        "opendes",
        "--owners-group",
        "owners@opendes.group",
        "--viewers-group",
        "viewers@opendes.group",
        "--retries",
        "1",
        "--retry-delay",
        "0",
        *argv_extra,
    ]
    monkeypatch.setattr("sys.argv", argv)
    monkeypatch.setenv("ACCESS_TOKEN", "fake-token")
    return seed_module.main()


def test_main_success_exit_code_and_report(tmp_path, monkeypatch):
    record_id = "opendes:reference-data--UnitOfMeasure:m"
    catalog_path = _write_catalog(tmp_path, [{"id": record_id, "kind": "osdu:wks:reference-data--UnitOfMeasure:1.0.0"}])
    report_path = tmp_path / "report.json"

    transport = ScriptedTransport()
    transport.script("GET", existing_get_url(record_id), [(200, {"id": record_id})])

    with patch.object(seed_module.requests, "request", side_effect=transport):
        exit_code = _run_main(
            monkeypatch,
            ["--catalog", str(catalog_path), "--report", str(report_path)],
        )

    assert exit_code == 0
    written = json.loads(report_path.read_text(encoding="utf-8"))
    assert written["result"] == "success"
    assert written["existing"] == 1
    assert written["created"] == 0


def test_main_auth_failure_exit_code_and_report(tmp_path, monkeypatch):
    record_id = "opendes:reference-data--UnitOfMeasure:m"
    catalog_path = _write_catalog(tmp_path, [{"id": record_id, "kind": "osdu:wks:reference-data--UnitOfMeasure:1.0.0"}])
    report_path = tmp_path / "report.json"

    transport = ScriptedTransport()
    transport.script("GET", existing_get_url(record_id), [(403, {"message": "forbidden"})])

    with patch.object(seed_module.requests, "request", side_effect=transport):
        exit_code = _run_main(
            monkeypatch,
            ["--catalog", str(catalog_path), "--report", str(report_path)],
        )

    assert exit_code == 1
    written = json.loads(report_path.read_text(encoding="utf-8"))
    assert written["result"] == "failed"
    assert "error" in written
    assert all(c["method"] != "PUT" for c in transport.calls)
