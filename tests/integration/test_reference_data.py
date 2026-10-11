import json
from urllib.parse import unquote

import pytest

from tests.integration.helpers.reference_data import (
    ReferenceDataPreflightError,
    discover_reference_ids,
    extract_reference_ids,
    load_required_records,
    seed_required_reference_data,
)


class _Response:
    def __init__(self, status_code):
        self.status_code = status_code


class _Storage:
    def __init__(self, existing=(), create_records=True):
        self.existing, self.create_records, self.upserts = (
            set(existing),
            create_records,
            [],
        )

    def get(self, path, allowed_codes):
        return _Response(
            200 if unquote(path.rsplit("/", 1)[-1]) in self.existing else 404
        )

    def create_or_update_records(self, records):
        self.upserts.append(records)
        if self.create_records:
            self.existing.update(record["id"] for record in records)


class _Api:
    def __init__(self, storage):
        self.storage = storage


def test_extract_reference_ids_walks_nested_payload_and_deduplicates():
    payload = {
        "one": "{data_partition_id}:reference-data--UnitOfMeasure:m:",
        "nested": [
            "osdu:reference-data--ViscosityModelType:FrictionTheory:",
            {"same": "{data_partition_id}:reference-data--UnitOfMeasure:m:"},
        ],
    }
    assert extract_reference_ids(payload, "demo") == {
        "demo:reference-data--UnitOfMeasure:m",
        "osdu:reference-data--ViscosityModelType:FrictionTheory",
    }


def test_discover_reference_ids_ignores_schema_examples_and_supports_supplements(
    tmp_path,
):
    (tmp_path / "payload.json").write_text(
        json.dumps({"id": "{data_partition_id}:reference-data--UnitOfMeasure:m:"})
    )
    (tmp_path / "payload_schema.json").write_text(
        json.dumps({"example": "{data_partition_id}:reference-data--UnitOfMeasure:ft:"})
    )
    assert discover_reference_ids(
        tmp_path, "demo", {"demo:reference-data--Generated:Runtime"}
    ) == {
        "demo:reference-data--UnitOfMeasure:m",
        "demo:reference-data--Generated:Runtime",
    }


def test_load_required_records_reports_all_missing_definitions(tmp_path):
    catalog = tmp_path / "catalog.json"
    catalog.write_text("[]")
    with pytest.raises(
        ReferenceDataPreflightError, match="Missing canonical definitions"
    ) as error:
        load_required_records(
            catalog,
            {"osdu:reference-data--A:one", "osdu:reference-data--B:two"},
            "osdu",
            "owners",
            "viewers",
        )
    assert "osdu:reference-data--A:one" in str(error.value)
    assert "osdu:reference-data--B:two" in str(error.value)


def test_seed_only_upserts_missing_records_and_skips_legal_tag_when_complete():
    existing, missing = (
        "osdu:reference-data--UnitOfMeasure:m",
        "osdu:reference-data--UnitOfMeasure:ft",
    )
    storage, legal_tag_calls = _Storage(existing=[existing]), []
    result = seed_required_reference_data(
        _Api(storage),
        [{"id": existing}, {"id": missing}],
        lambda: legal_tag_calls.append(True),
    )
    assert result == {"inventory": 2, "existing": 1, "seeded": 1}
    assert storage.upserts == [[{"id": missing}]] and legal_tag_calls == [True]
    seed_required_reference_data(
        _Api(storage),
        [{"id": existing}, {"id": missing}],
        lambda: legal_tag_calls.append(True),
    )
    assert legal_tag_calls == [True]


def test_seed_reports_every_unavailable_record():
    records = [
        {"id": "osdu:reference-data--A:one"},
        {"id": "osdu:reference-data--B:two"},
    ]
    with pytest.raises(
        ReferenceDataPreflightError, match="Missing in Storage"
    ) as error:
        seed_required_reference_data(_Api(_Storage(create_records=False)), records)
    assert "osdu:reference-data--A:one" in str(error.value)
    assert "osdu:reference-data--B:two" in str(error.value)


def test_seed_reports_storage_and_catalog_gaps_together():
    with pytest.raises(ReferenceDataPreflightError) as error:
        seed_required_reference_data(
            _Api(_Storage(create_records=False)),
            [{"id": "osdu:reference-data--A:one"}],
            missing_definitions={"osdu:reference-data--B:two"},
        )

    assert "Missing in Storage" in str(error.value)
    assert "osdu:reference-data--A:one" in str(error.value)
    assert "Missing canonical definitions" in str(error.value)
    assert "osdu:reference-data--B:two" in str(error.value)


def test_seed_accepts_uncatalogued_record_already_in_storage():
    external = "osdu:reference-data--BasinType:PassiveMargin"

    result = seed_required_reference_data(
        _Api(_Storage(existing=[external])),
        [],
        missing_definitions={external},
    )

    assert result == {"inventory": 0, "existing": 0, "seeded": 0}
