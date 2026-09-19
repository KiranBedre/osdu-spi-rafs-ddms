#  Copyright 2023 ExxonMobil Technology and Engineering Company
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

import io

import pandas as pd
import pytest

from app.bulk_data_validation.data_validation import _MAX_RECEIVED_REPR_LEN, DataValidator
from app.models.data_schemas.data_schema import build_data_schema
from app.models.data_schemas.sample_analysis_api_v2.routine_core_analysis_data_model_1_0_0 import (
    RoutineCoreAnalysisModel100,
)
from tests.test_api.api_version import API_VERSION_V2
from tests.test_api.test_routes.data.data_mock_objects import StorageService
from tests.test_validation.test_data import (
    CORRECT_TEST_BULK_DATA,
    INCORRECT_TEST_BULK_DATA,
    TEST_SCHEMA,
)


@pytest.mark.asyncio
async def test_data_validator_success():
    mock_storage_service = StorageService(record_data=None)
    data_validator = DataValidator(TEST_SCHEMA, mock_storage_service, API_VERSION_V2)
    test_df = pd.read_json(io.StringIO(CORRECT_TEST_BULK_DATA), orient="split")

    errors = await data_validator.validate(test_df)
    assert not errors


@pytest.mark.asyncio
async def test_data_validator_fail():
    mock_storage_service = StorageService(record_data=None)
    data_validator = DataValidator(TEST_SCHEMA, mock_storage_service, API_VERSION_V2)
    test_df = pd.read_json(io.StringIO(INCORRECT_TEST_BULK_DATA), orient="split")

    errors = await data_validator.validate(test_df)
    assert isinstance(errors, dict)
    assert errors == {"invalid_type": [{"SampleDepth": "object"}]}


@pytest.mark.asyncio
async def test_pydantic_model_validation_error_enriched():
    mock_storage_service = StorageService(record_data=None)
    rca_schema = build_data_schema(RoutineCoreAnalysisModel100)
    data_validator = DataValidator(rca_schema, mock_storage_service, API_VERSION_V2)

    bad_id = "not_valid"
    test_df = pd.DataFrame([{"SamplesAnalysisID": bad_id}])

    errors = await data_validator.validate(test_df, bulk_mode=True)
    assert isinstance(errors, dict)
    assert "invalid_type" in errors
    first_error = errors["invalid_type"][0]
    assert first_error["field"] == "SamplesAnalysisID"
    assert first_error["received"] == repr(bad_id)
    assert first_error["expected"].startswith("pattern: ")


@pytest.mark.asyncio
async def test_missing_mandatory_main_field_is_reported():
    """Issue-679 QA gap 1: a missing mandatory main column must be named explicitly."""
    mock_storage_service = StorageService(record_data=None)
    rca_schema = build_data_schema(RoutineCoreAnalysisModel100)
    data_validator = DataValidator(rca_schema, mock_storage_service, API_VERSION_V2)

    # "Meta" is required but omitted entirely.
    test_df = pd.DataFrame(
        [
            {
                "SamplesAnalysisID": "osdu:work-product-component--SamplesAnalysis:abc123:1",
                "SampleID": "osdu:master-data--Sample:abc123:1",
            },
        ],
    )

    errors = await data_validator.validate(test_df, bulk_mode=True)
    fields = [entry["field"] for entry in errors["invalid_type"]]
    assert "Meta" in fields
    meta_error = errors["invalid_type"][fields.index("Meta")]
    assert meta_error["received"] == "missing"
    assert meta_error["expected"] == "required field"


@pytest.mark.asyncio
async def test_extra_main_field_has_dedicated_message():
    """Issue-679 QA gap 3: an extra main column must say it's not allowed, not 'unknown'."""
    mock_storage_service = StorageService(record_data=None)
    rca_schema = build_data_schema(RoutineCoreAnalysisModel100)
    data_validator = DataValidator(rca_schema, mock_storage_service, API_VERSION_V2)

    test_df = pd.DataFrame(
        [
            {
                "SamplesAnalysisID": "osdu:work-product-component--SamplesAnalysis:abc123:1",
                "SampleID": "osdu:master-data--Sample:abc123:1",
                "Meta": [{"kind": "Unit", "name": "percentage", "propertyNames": ["Porosity"]}],
                "ExtraColumn": "ExtraValue",
            },
        ],
    )

    errors = await data_validator.validate(test_df, bulk_mode=True)
    fields = [entry["field"] for entry in errors["invalid_type"]]
    assert "ExtraColumn" in fields
    extra_error = errors["invalid_type"][fields.index("ExtraColumn")]
    assert extra_error["received"] == "present"
    assert extra_error["expected"] == "not allowed (extra field)"


@pytest.mark.asyncio
async def test_extra_main_field_with_null_value_is_consistent():
    """Issue-679 QA gap 4: an extra column with a null value must match the non-null case."""
    mock_storage_service = StorageService(record_data=None)
    rca_schema = build_data_schema(RoutineCoreAnalysisModel100)
    data_validator = DataValidator(rca_schema, mock_storage_service, API_VERSION_V2)

    test_df = pd.DataFrame(
        [
            {
                "SamplesAnalysisID": "osdu:work-product-component--SamplesAnalysis:abc123:1",
                "SampleID": "osdu:master-data--Sample:abc123:1",
                "Meta": [{"kind": "Unit", "name": "percentage", "propertyNames": ["Porosity"]}],
                "ExtraColumn": None,
            },
        ],
    )

    errors = await data_validator.validate(test_df, bulk_mode=True)
    fields = [entry["field"] for entry in errors["invalid_type"]]
    assert "ExtraColumn" in fields
    extra_error = errors["invalid_type"][fields.index("ExtraColumn")]
    assert extra_error["received"] == "null"
    assert extra_error["expected"] == "not allowed (extra field)"


@pytest.mark.asyncio
async def test_nested_union_field_error_pinpoints_leaf_field():
    """Issue-679 QA gap 2: a nested field error must name the failing sub-field, not dump the raw Union type."""
    mock_storage_service = StorageService(record_data=None)
    rca_schema = build_data_schema(RoutineCoreAnalysisModel100)
    data_validator = DataValidator(rca_schema, mock_storage_service, API_VERSION_V2)

    test_df = pd.DataFrame(
        [
            {
                "SamplesAnalysisID": "osdu:work-product-component--SamplesAnalysis:abc123:1",
                "SampleID": "osdu:master-data--Sample:abc123:1",
                "Meta": [
                    {
                        "kind": "Unit",
                        "name": "percentage",
                        "unitOfMeasureID": "osdu:reference-data-UnitOfMeasure:%25:",  # single dash: invalid
                        "propertyNames": ["Porosity"],
                    },
                ],
            },
        ],
    )

    errors = await data_validator.validate(test_df, bulk_mode=True)
    fields = [entry["field"] for entry in errors["invalid_type"]]
    assert fields == ["Meta[0].unitOfMeasureID"]
    leaf_error = errors["invalid_type"][0]
    assert leaf_error["expected"].startswith("pattern: ")
    assert "typing." not in leaf_error["expected"]
    assert "app.models" not in leaf_error["expected"]


@pytest.mark.asyncio
async def test_fallback_enriches_only_reported_fields_when_revalidation_passes():
    """MR review point 1: if pandera flags a row that standalone re-validation accepts,
    only the fields pandera reported may be enriched — not every column of the
    reconstructed row.

    This pandera/pydantic disagreement can't be forced deterministically through
    ``validate()``, so the enrichment entrypoint is called directly with a real
    dataframe, real schema, and a partial failure case.
    """
    mock_storage_service = StorageService(record_data=None)
    rca_schema = build_data_schema(RoutineCoreAnalysisModel100)
    data_validator = DataValidator(rca_schema, mock_storage_service, API_VERSION_V2)

    test_df = pd.DataFrame(
        [
            {
                "SamplesAnalysisID": "osdu:work-product-component--SamplesAnalysis:abc123:1",
                "SampleID": "osdu:master-data--Sample:abc123:1",
                "Meta": [{"kind": "Unit", "name": "percentage", "propertyNames": ["Porosity"]}],
            },
        ],
    )

    raw_failure = repr({"SamplesAnalysisID": "osdu:work-product-component--SamplesAnalysis:abc123:1"})
    result = data_validator._enrich_pydantic_error(raw_failure, index=0, df=test_df)

    assert len(result) == 1
    assert result[0]["field"] == "SamplesAnalysisID"


@pytest.mark.asyncio
async def test_union_candidate_selected_by_kind_discriminator():
    """MR review point 3: the union member must be chosen by the `kind` discriminator,
    not by whichever candidate happens to produce the fewest errors."""
    mock_storage_service = StorageService(record_data=None)
    rca_schema = build_data_schema(RoutineCoreAnalysisModel100)
    data_validator = DataValidator(rca_schema, mock_storage_service, API_VERSION_V2)

    # kind="CRS" selects Meta1, whose required persistableReference is missing.
    # The fewest-errors heuristic alone would tie with the "Unit" member's
    # const-mismatch error and misreport Meta[0].kind instead.
    test_df = pd.DataFrame(
        [
            {
                "SamplesAnalysisID": "osdu:work-product-component--SamplesAnalysis:abc123:1",
                "SampleID": "osdu:master-data--Sample:abc123:1",
                "Meta": [{"kind": "CRS", "name": "WGS 84 / UTM zone 15N"}],
            },
        ],
    )

    errors = await data_validator.validate(test_df, bulk_mode=True)
    fields = [entry["field"] for entry in errors["invalid_type"]]
    assert fields == ["Meta[0].persistableReference"]
    missing_error = errors["invalid_type"][0]
    assert missing_error["received"] == "missing"
    assert missing_error["expected"] == "required field"


@pytest.mark.asyncio
async def test_duplicate_dataframe_index_falls_back_to_reported_failure():
    """MR review point 4: duplicate index labels make the true row ambiguous;
    enrichment must fall back to the reported failure case instead of iterating
    a mis-shaped ``df.loc`` result."""
    mock_storage_service = StorageService(record_data=None)
    rca_schema = build_data_schema(RoutineCoreAnalysisModel100)
    data_validator = DataValidator(rca_schema, mock_storage_service, API_VERSION_V2)

    valid_meta = [{"kind": "Unit", "name": "percentage", "propertyNames": ["Porosity"]}]
    test_df = pd.DataFrame(
        [
            {
                "SamplesAnalysisID": "not-a-valid-id",
                "SampleID": "osdu:master-data--Sample:abc123:1",
                "Meta": valid_meta,
            },
            {
                "SamplesAnalysisID": "osdu:work-product-component--SamplesAnalysis:abc123:1",
                "SampleID": "osdu:master-data--Sample:abc123:1",
                "Meta": valid_meta,
            },
        ],
        index=[0, 0],
    )

    errors = await data_validator.validate(test_df, bulk_mode=True)
    fields = [entry["field"] for entry in errors["invalid_type"]]
    assert fields == ["SamplesAnalysisID"]
    pattern_error = errors["invalid_type"][0]
    assert pattern_error["received"] == "'not-a-valid-id'"
    assert pattern_error["expected"].startswith("pattern: ")


@pytest.mark.asyncio
async def test_deep_nested_error_reports_leaf_value():
    """MR review point 5: for a deep nested error the received value must be the
    offending leaf, not the whole first-level parent object."""
    mock_storage_service = StorageService(record_data=None)
    rca_schema = build_data_schema(RoutineCoreAnalysisModel100)
    data_validator = DataValidator(rca_schema, mock_storage_service, API_VERSION_V2)

    test_df = pd.DataFrame(
        [
            {
                "SamplesAnalysisID": "osdu:work-product-component--SamplesAnalysis:abc123:1",
                "SampleID": "osdu:master-data--Sample:abc123:1",
                "Meta": [{"kind": "Unit", "name": "percentage", "propertyNames": ["Porosity"]}],
                "Permeability": [
                    {
                        "Value": 1.5,
                        "Conditions": {"Pressure": "not-a-number", "Temperature": 300.0},
                    },
                ],
            },
        ],
    )

    errors = await data_validator.validate(test_df, bulk_mode=True)
    fields = [entry["field"] for entry in errors["invalid_type"]]
    assert fields == ["Permeability[0].Conditions.Pressure"]
    leaf_error = errors["invalid_type"][0]
    assert leaf_error["received"] == "'not-a-number'"
    assert "Temperature" not in leaf_error["received"]
    assert leaf_error["expected"] == "float"


@pytest.mark.asyncio
async def test_non_castable_string_index_falls_back_gracefully():
    """Gap coverage: a non-numeric index string (e.g. from an unusual DataFrame index)
    must not raise — enrichment falls back to the parsed failure case without error."""
    mock_storage_service = StorageService(record_data=None)
    rca_schema = build_data_schema(RoutineCoreAnalysisModel100)
    data_validator = DataValidator(rca_schema, mock_storage_service, API_VERSION_V2)

    test_df = pd.DataFrame(
        [
            {
                "SamplesAnalysisID": "osdu:work-product-component--SamplesAnalysis:abc123:1",
                "SampleID": "osdu:master-data--Sample:abc123:1",
                "Meta": [{"kind": "Unit", "name": "percentage", "propertyNames": ["Porosity"]}],
            },
        ],
        index=["row-a"],
    )

    raw_failure = repr({"SamplesAnalysisID": "not-a-valid-id"})
    result = data_validator._enrich_pydantic_error(raw_failure, index="not-an-integer", df=test_df)

    assert result
    assert result[0]["field"] == "SamplesAnalysisID"


@pytest.mark.asyncio
async def test_empty_loc_validation_error_is_skipped_without_raising():
    """Gap coverage: a pydantic error entry with loc=() (e.g. from a root validator)
    must be silently skipped — it must not crash, and real field-level errors in the
    same batch are still enriched correctly."""
    mock_storage_service = StorageService(record_data=None)
    rca_schema = build_data_schema(RoutineCoreAnalysisModel100)
    data_validator = DataValidator(rca_schema, mock_storage_service, API_VERSION_V2)

    failed_fields = {
        "SamplesAnalysisID": "not-a-valid-id",
        "SampleID": "osdu:master-data--Sample:abc123:1",
        "Meta": [{"kind": "Unit", "name": "percentage", "propertyNames": ["Porosity"]}],
    }
    pydantic_model = data_validator._get_pydantic_model()
    synthetic_errors = [
        {"loc": (), "msg": "value is not valid", "type": "value_error"},
        {"loc": ("SamplesAnalysisID",), "msg": "string does not match regex", "type": "value_error.str.regex"},
    ]

    result = data_validator._enrich_from_validation_errors(failed_fields, pydantic_model, synthetic_errors)

    fields = [entry["field"] for entry in result]
    assert fields == ["SamplesAnalysisID"]


@pytest.mark.asyncio
async def test_required_field_set_to_none_reports_null_not_missing():
    """Point 1: a required field explicitly set to None must be reported with
    received=repr(None), not silently dropped and reported as received='missing'."""
    mock_storage_service = StorageService(record_data=None)
    rca_schema = build_data_schema(RoutineCoreAnalysisModel100)
    data_validator = DataValidator(rca_schema, mock_storage_service, API_VERSION_V2)

    # SamplesAnalysisID is required. Passing None explicitly is different from
    # omitting the field: the former is an invalid value, the latter is a missing
    # field. Both should be reported, but with distinct received messages.
    test_df = pd.DataFrame(
        [
            {
                "SamplesAnalysisID": None,
                "SampleID": "osdu:master-data--Sample:abc123:1",
                "Meta": [{"kind": "Unit", "name": "percentage", "propertyNames": ["Porosity"]}],
            },
        ],
    )

    errors = await data_validator.validate(test_df, bulk_mode=True)
    assert "invalid_type" in errors
    fields = [e["field"] for e in errors["invalid_type"]]
    assert "SamplesAnalysisID" in fields
    sa_error = next(e for e in errors["invalid_type"] if e["field"] == "SamplesAnalysisID")
    assert sa_error["received"] == repr(None)
    assert sa_error["received"] != "missing"


@pytest.mark.asyncio
async def test_mixed_list_with_scalar_and_invalid_dict_reports_both():
    """Point 2: a list containing an invalid scalar at one position and an
    invalid dict at another must report errors for both positions."""
    mock_storage_service = StorageService(record_data=None)
    rca_schema = build_data_schema(RoutineCoreAnalysisModel100)
    data_validator = DataValidator(rca_schema, mock_storage_service, API_VERSION_V2)

    test_df = pd.DataFrame(
        [
            {
                "SamplesAnalysisID": "osdu:work-product-component--SamplesAnalysis:abc123:1",
                "SampleID": "osdu:master-data--Sample:abc123:1",
                "Meta": [
                    42,  # invalid scalar at position 0
                    {
                        "kind": "Unit",
                        "name": "percentage",
                        "propertyNames": ["Porosity"],
                        "unitOfMeasureID": "bad-id",  # invalid id at position 1
                    },
                ],
            },
        ],
    )

    errors = await data_validator.validate(test_df, bulk_mode=True)
    assert "invalid_type" in errors
    fields = [e["field"] for e in errors["invalid_type"]]
    assert "Meta[0]" in fields, f"expected Meta[0] in fields but got {fields}"
    assert any(f.startswith("Meta[1]") for f in fields), f"expected Meta[1].* in fields but got {fields}"


def test_locationless_only_errors_fall_back_to_legacy(monkeypatch):
    """Point 3: when _revalidate_with_pydantic returns only loc=() errors
    (e.g. a root validator), the failure must not be silently dropped.
    The legacy path must produce output for the pandera-reported fields.

    This shape cannot occur with current RAFS schemas (no root validators),
    but the code must handle it defensively.
    """
    mock_storage_service = StorageService(record_data=None)
    rca_schema = build_data_schema(RoutineCoreAnalysisModel100)
    data_validator = DataValidator(rca_schema, mock_storage_service, API_VERSION_V2)

    def always_locationless(_pydantic_model, _failed_fields):
        return [{"loc": (), "msg": "value is not valid", "type": "value_error"}]

    monkeypatch.setattr(DataValidator, "_revalidate_with_pydantic", staticmethod(always_locationless))

    raw_failure = repr({"SamplesAnalysisID": "not-valid"})
    result = data_validator._enrich_pydantic_error(raw_failure)

    assert result, "enrichment must not return empty for a real pandera failure"
    assert result[0]["field"] == "SamplesAnalysisID"


@pytest.mark.asyncio
async def test_pydantic_model_validation_error_received_truncated():
    mock_storage_service = StorageService(record_data=None)
    rca_schema = build_data_schema(RoutineCoreAnalysisModel100)
    data_validator = DataValidator(rca_schema, mock_storage_service, API_VERSION_V2)

    long_val = "x" * 500
    # Only SamplesAnalysisID is invalid; the other required fields are valid so
    # re-validation surfaces exactly the one error we're asserting on.
    row = {
        "SamplesAnalysisID": long_val,
        "SampleID": "osdu:master-data--Sample:abc123:1",
        "Meta": [{"kind": "Unit", "name": "percentage", "propertyNames": ["Porosity"]}],
    }
    raw_failure = repr(row)
    result = data_validator._enrich_pydantic_error(raw_failure)

    assert len(result) == 1
    assert result[0]["field"] == "SamplesAnalysisID"
    assert result[0]["received"].endswith("...[truncated]")
    assert len(result[0]["received"]) == _MAX_RECEIVED_REPR_LEN + len("...[truncated]")
