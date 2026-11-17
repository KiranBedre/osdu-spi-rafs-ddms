import copy
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from app.models.data_schemas.sample_analysis_api_v2.relative_permeability_data_model_2_0_0 import (
    RelativePermeabilityModel200,
)
from tests.integration.config import CONFIG, TEST_DATA_STORE, DataFiles, SamplesAnalysisTypes
from tests.integration.data_provider import load_test_data, scope_fixture_id
from tests.integration.fixture_ids import scope_fixture_ids
from tests.integration.helpers.common import CommonHelper
from tests.integration.helpers.parallel_execution import (
    begin_cross_worker_session,
    end_cross_worker_session,
    shared_session_directory,
)
from tests.integration.tests.samples_analysis.relative_permeability import test_relative_permeability as permeability


def test_ac_855_fixture_ids_are_run_owned_and_preserve_reference_data():
    payload = (
        '"osdu:master-data--Field:SomeUniqueFieldID:", '
        '"osdu:work-product-component--SamplesAnalysis:parent:123", '
        '"osdu:wks:work-product-component--SamplesAnalysis:1.0.0", '
        '"osdu:wks:master-data--Sample:3.1.0", '
        '"osdu:reference-data--UnitOfMeasure:m:"'
    )
    first = scope_fixture_ids(payload, "run_one")
    second = scope_fixture_ids(payload, "run_two")
    assert "SomeUniqueFieldID_run_one:" in first
    assert "SamplesAnalysis:parent_run_one:123" in first
    assert "SomeUniqueFieldID_run_two:" in second
    assert scope_fixture_ids(first, "run_one") == first
    assert "osdu:reference-data--UnitOfMeasure:m:" in first
    assert "osdu:wks:work-product-component--SamplesAnalysis:1.0.0" in first
    assert "osdu:wks:master-data--Sample:3.1.0" in first
    assert scope_fixture_ids(payload, "") == payload


def test_ac_855_rendered_payloads_share_scope_and_keep_the_real_parent_id(monkeypatch):
    monkeypatch.setitem(CONFIG, "CLOUD_PROVIDER", "cimpl")
    monkeypatch.setitem(CONFIG, "DATA_PARTITION", "osdu")
    monkeypatch.setitem(TEST_DATA_STORE, "legal_tag", "osdu-owned-tag")
    monkeypatch.setitem(TEST_DATA_STORE, "fixture_namespace", "run_one")
    parent_id = "osdu:work-product-component--SamplesAnalysesReport:parent_run_one"
    monkeypatch.setitem(TEST_DATA_STORE, "sar_record_id", parent_id)
    sample = load_test_data(DataFiles.SAMPLE)
    analysis = load_test_data(DataFiles.SAMPLE_ANALYSIS, SamplesAnalysisTypes.NMR)
    assert analysis["data"]["SampleIDs"] == [sample["id"] + ":"]
    assert sample["kind"] == "osdu:wks:master-data--Sample:2.0.0"
    assert analysis["kind"] == "osdu:wks:work-product-component--SamplesAnalysis:1.0.0"
    assert analysis["data"]["ParentSamplesAnalysesReports"][0]["ParentSamplesAnalysesReportID"] == parent_id + ":"
    assert sample["legal"]["legaltags"] == ["osdu-owned-tag"]
    assert scope_fixture_id("osdu:master-data--Field:SomeUniqueFieldID:").endswith("_run_one:")


def test_ac_855_expected_schema_examples_are_not_scoped(monkeypatch):
    monkeypatch.setitem(CONFIG, "CLOUD_PROVIDER", "cimpl")
    monkeypatch.setitem(CONFIG, "DATA_PARTITION", "osdu")
    monkeypatch.setitem(TEST_DATA_STORE, "legal_tag", "osdu-owned-tag")
    monkeypatch.setitem(TEST_DATA_STORE, "fixture_namespace", "run_one")
    schema = load_test_data(DataFiles.SIMULATION_ROCK_PHYSICS_SCHEMA)
    example = schema["properties"]["ReservoirSimulationRockPhysicsID"]["example"]
    assert example == "namespace:work-product-component--ReservoirSimulationRockPhysicsModel:uuid:"


def test_ac_855_dependency_cleanup_does_not_delete_existing_records():
    existing = "osdu:master-data--Field:existing"
    created = "osdu:master-data--Field:owned"
    reference = "osdu:reference-data--UnitOfMeasure:m"
    stored = {existing}
    api = SimpleNamespace(storage=Mock())

    def get(path, allowed_codes):
        return SimpleNamespace(status_code=200 if path.removeprefix("/records/") in stored else 404)

    def upsert(records):
        stored.update(record["id"] for record in records)
        return Mock()

    api.storage.get.side_effect = get
    api.storage.create_or_update_records.side_effect = upsert
    api.storage.purge_record.side_effect = stored.remove
    helper = CommonHelper(api)
    state = helper.create_reference_records(
        api, helper, lambda _: {"data": {}}, "osdu", {existing, created, reference}, [], []
    )
    api.storage.purge_record.assert_not_called()
    helper.purge_reference_records(api, state, {existing, created, reference}, [])
    assert stored == {existing}
    api.storage.purge_record.assert_called_once_with(created)


def test_ac_855_overlapping_runs_cannot_delete_each_others_dependencies():
    stored = set()
    api = SimpleNamespace(storage=Mock())
    api.storage.get.side_effect = lambda path, allowed_codes: SimpleNamespace(
        status_code=200 if path.removeprefix("/records/") in stored else 404
    )
    api.storage.create_or_update_records.side_effect = lambda records: stored.update(record["id"] for record in records)
    api.storage.purge_record.side_effect = stored.remove
    helper = CommonHelper(api)
    original = "osdu:master-data--Field:SomeUniqueFieldID"
    first_id, second_id = (scope_fixture_ids(original, name) for name in ("run_one", "run_two"))
    first = helper.create_reference_records(api, helper, lambda _: {"data": {}}, "osdu", {first_id}, [], [])
    second = helper.create_reference_records(api, helper, lambda _: {"data": {}}, "osdu", {second_id}, [], [])
    helper.purge_reference_records(api, first, {first_id}, [])
    assert stored == {second_id}
    helper.purge_reference_records(api, second, {second_id}, [])
    assert not stored
    assert original not in stored


def test_ac_855_cleanup_attempts_remaining_records_after_a_rejection():
    api = SimpleNamespace(storage=Mock())
    api.storage.purge_record.side_effect = [AssertionError("Storage rejected cleanup"), None]
    helper = CommonHelper(api)
    state = {"storage_dependency_ids": ["first", "second"], "fixed_record_ids": []}
    with pytest.raises(AssertionError, match="Storage rejected cleanup"):
        helper.purge_reference_records(api, state, set(), [])
    assert api.storage.purge_record.call_count == 2


def test_ac_855_dependency_setup_verifies_storage_and_rolls_back_partial_writes():
    record_id = "osdu:master-data--Field:owned"
    api = SimpleNamespace(storage=Mock())
    api.storage.get.return_value.status_code = 404
    helper = CommonHelper(api)
    with pytest.raises(AssertionError, match="unavailable"):
        helper.create_reference_records(api, helper, lambda _: {"data": {}}, "osdu", {record_id}, [], [])
    api.storage.purge_record.assert_called_once_with(record_id)


def test_ac_855_fixed_sample_created_by_run_is_cleaned():
    sample = {"id": "osdu:master-data--Sample:owned", "data": {}}
    api = SimpleNamespace(storage=Mock())
    api.storage.get.return_value.status_code = 404
    helper = CommonHelper(api)
    with pytest.raises(AssertionError, match="unavailable"):
        helper.create_reference_records(
            api,
            helper,
            lambda name: copy.deepcopy(sample if name == DataFiles.SAMPLE else {"data": {}}),
            "osdu",
            set(),
            [],
            [DataFiles.SAMPLE],
        )
    api.storage.purge_record.assert_called_once_with(sample["id"])


def test_ac_855_workers_keep_shared_prerequisites_until_last_teardown(tmp_path):
    setup, teardown = Mock(return_value={"ids": ["owned"]}), Mock()
    first = begin_cross_worker_session(tmp_path, "records", setup)
    second = begin_cross_worker_session(tmp_path, "records", setup)
    end_cross_worker_session(tmp_path, "records", first, teardown)
    teardown.assert_not_called()
    end_cross_worker_session(tmp_path, "records", second, teardown)
    setup.assert_called_once()
    teardown.assert_called_once_with(first)


def test_ac_855_serial_runs_do_not_share_state_directory(tmp_path):
    first, second = tmp_path / "pytest-1", tmp_path / "pytest-2"
    assert shared_session_directory(first, False) != shared_session_directory(second, False)
    assert shared_session_directory(first / "popen-gw0", True) == first
    assert shared_session_directory(first / "popen-gw1", True) == first


def test_ac_855_successful_setup_cleans_owned_sample_but_preserves_existing_sample():
    for existing in (False, True):
        sample = {"id": "osdu:master-data--Sample:owned", "data": {}}
        stored = {sample["id"]} if existing else set()
        api = SimpleNamespace(storage=Mock())
        api.storage.get.side_effect = lambda path, allowed_codes: SimpleNamespace(
            status_code=200 if path.removeprefix("/records/") in stored else 404
        )
        api.storage.create_or_update_records.side_effect = lambda records: stored.update(
            record["id"] for record in records
        )
        api.storage.purge_record.side_effect = stored.remove
        helper = CommonHelper(api)
        state = helper.create_reference_records(
            api,
            helper,
            lambda name: copy.deepcopy(sample if name == DataFiles.SAMPLE else {"data": {}}),
            "osdu",
            set(),
            [],
            [DataFiles.SAMPLE],
        )
        helper.purge_reference_records(api, state, set(), [], [DataFiles.SAMPLE])
        assert stored == ({sample["id"]} if existing else set())


def test_ac_855_cleanup_failure_is_not_silently_successful(tmp_path):
    state = begin_cross_worker_session(tmp_path, "records", lambda: {"ids": ["owned"]})
    teardown = Mock(side_effect=RuntimeError("Storage rejected cleanup"))
    with pytest.raises(RuntimeError, match="Storage rejected cleanup"):
        end_cross_worker_session(tmp_path, "records", state, teardown)
    assert (tmp_path / "records.state.json").is_file()


@pytest.mark.parametrize("operation", ["json_upload", "parquet_upload", "search"])
def test_ac_855_relative_permeability_json_rejects_unexpected_null_fields(operation, monkeypatch):
    monkeypatch.setitem(CONFIG, "CLOUD_PROVIDER", "cimpl")
    monkeypatch.setitem(CONFIG, "DATA_PARTITION", "osdu")
    monkeypatch.setitem(TEST_DATA_STORE, "legal_tag", "osdu-owned-tag")
    payload = load_test_data(DataFiles.RELATIVE_PERMEABILITY_DATA_V2)
    payload = permeability._prepare_v2_payload(payload, "owned")
    response = copy.deepcopy(payload)
    response["data"][0][response["columns"].index("ReferencePermeability")]["UnexpectedField"] = None
    api = SimpleNamespace(sample_analysis=Mock())
    api.sample_analysis.post_data.return_value = {"ddms_urn": "urn/test/dataset"}
    api.sample_analysis.post.return_value.json.return_value = {"ddms_urn": "urn/test/dataset"}
    api.sample_analysis.get_data.return_value = response
    api.sample_analysis.search_data.return_value = {"result": response}
    helper = CommonHelper(api)
    helper.wait_for_search_data = lambda request, record_id: request()
    tests_data = lambda _: copy.deepcopy(payload)

    with pytest.raises(AssertionError, match="UnexpectedField"):
        if operation == "json_upload":
            permeability.test_relative_permeability_add_data_v2(api, helper, tests_data, "owned")
        elif operation == "parquet_upload":
            permeability.test_relative_permeability_parquet_v2_round_trip(api, helper, tests_data, "owned")
        else:
            permeability.test_relative_permeability_search_data_filtered_in_by_row_v2(
                api, helper, tests_data, "owned", "dataset"
            )


def test_ac_855_relative_permeability_fixture_survives_parquet_without_normalization(monkeypatch):
    monkeypatch.setitem(CONFIG, "CLOUD_PROVIDER", "cimpl")
    monkeypatch.setitem(CONFIG, "DATA_PARTITION", "osdu")
    monkeypatch.setitem(TEST_DATA_STORE, "legal_tag", "osdu-owned-tag")
    payload = load_test_data(DataFiles.RELATIVE_PERMEABILITY_DATA_V2)
    RelativePermeabilityModel200.model_validate(dict(zip(payload["columns"], payload["data"][0])))
    parquet = pd.DataFrame(payload["data"], columns=payload["columns"], index=payload["index"]).to_parquet()
    materialized = CommonHelper.load_parquet_data(parquet, "parquet")
    assert materialized == payload
