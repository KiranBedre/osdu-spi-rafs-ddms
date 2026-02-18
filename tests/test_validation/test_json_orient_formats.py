#  Copyright 2025 ExxonMobil Technology and Engineering Company
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

"""Tests for JSON orient format handling (Issue #680).

Verifies that:
1. Records format is passed through with orient='records'
2. Split format is validated and returned with orient='split'
3. Both formats produce identical DataFrames
4. Both formats produce identical parquet files
"""

import io
import json
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.api.dependencies.validation import get_validated_bulk_data_json
from app.bulk_data_validation.data_validation import DataValidator
from app.exceptions.exceptions import UnprocessableContentException
from app.models.data_schemas.data_schema import build_data_schema
from app.models.data_schemas.sample_analysis_api_v2.capillary_pressure_data_model_1_0_0 import (
    CapillaryPressureModel100,
)
from tests.test_api.api_version import API_VERSION_V2
from tests.test_api.test_routes.data.data_mock_objects import (
    build_mock_get_storage_service,
)


class TestGetValidatedBulkDataJson:
    """Tests for get_validated_bulk_data_json function."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request with body."""
        from unittest.mock import AsyncMock

        def _mock_request(body_content):
            request = MagicMock()
            request.body = AsyncMock(return_value=body_content.encode("utf-8"))
            return request
        return _mock_request

    @pytest.mark.asyncio
    async def test_accepts_split_format(self, mock_request):
        """Split format is accepted and returned as-is."""
        body = json.dumps({
            "columns": ["A", "B"],
            "index": [0, 1],
            "data": [[1, 2], [3, 4]],
        })
        request = mock_request(body)

        result_json, orient = await get_validated_bulk_data_json(request)
        result_data = json.loads(result_json)

        assert orient == "split"
        assert "columns" in result_data
        assert "index" in result_data
        assert "data" in result_data
        assert result_data["columns"] == ["A", "B"]

    @pytest.mark.asyncio
    async def test_accepts_records_format(self, mock_request):
        """Records format is passed through as records orient."""
        body = json.dumps([
            {"A": 1, "B": 2},
            {"A": 3, "B": 4},
        ])
        request = mock_request(body)

        result_json, orient = await get_validated_bulk_data_json(request)
        result_data = json.loads(result_json)

        assert orient == "records"
        assert isinstance(result_data, list)
        assert len(result_data) == 2

    @pytest.mark.asyncio
    async def test_records_format_preserves_fields(self, mock_request):
        """Records format preserves field names in the returned data."""
        body = json.dumps([
            {"A": 1, "B": "x"},
            {"A": 2, "B": "y"},
        ])
        request = mock_request(body)

        result_json, orient = await get_validated_bulk_data_json(request)
        result_data = json.loads(result_json)

        assert orient == "records"
        assert set(result_data[0].keys()) == {"A", "B"}
        assert len(result_data) == 2

    @pytest.mark.asyncio
    async def test_empty_records_array_raises_error(self, mock_request):
        """Empty records array raises UnprocessableContentException."""
        body = json.dumps([])
        request = mock_request(body)

        with pytest.raises(UnprocessableContentException) as exc_info:
            await get_validated_bulk_data_json(request)

        assert "empty records array" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_non_object_array_raises_error(self, mock_request):
        """Array of non-objects raises UnprocessableContentException."""
        body = json.dumps([1, 2, 3])
        request = mock_request(body)

        with pytest.raises(UnprocessableContentException) as exc_info:
            await get_validated_bulk_data_json(request)

        assert "body must be a JSON object (dictionary), not a list" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_empty_object_records_raises_error(self, mock_request):
        """Records with empty objects raises UnprocessableContentException."""
        body = json.dumps([{}])
        request = mock_request(body)

        with pytest.raises(UnprocessableContentException) as exc_info:
            await get_validated_bulk_data_json(request)

        assert "no fields" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_wrapped_split_format_raises_error(self, mock_request):
        """Split format wrapped in a list raises UnprocessableContentException."""
        body = json.dumps([{
            "columns": ["SaturationFunctionSetID", "Meta"],
            "index": [0, 1],
            "data": [["id:1", []], ["id:2", []]],
        }])
        request = mock_request(body)

        with pytest.raises(UnprocessableContentException) as exc_info:
            await get_validated_bulk_data_json(request)

        assert "split" in str(exc_info.value.detail)


class TestFormatEquivalence:
    """Tests that split and records formats produce identical results."""

    def test_simple_data_produces_same_dataframe(self):
        """Both formats produce identical DataFrames for simple data."""
        split_json = json.dumps({
            "columns": ["A", "B", "C"],
            "index": [0, 1],
            "data": [[1, 2, 3], [4, 5, 6]],
        })

        records_json = json.dumps([
            {"A": 1, "B": 2, "C": 3},
            {"A": 4, "B": 5, "C": 6},
        ])

        df_split = pd.read_json(io.StringIO(split_json), orient="split")
        df_records = pd.read_json(io.StringIO(records_json), orient="records")

        pd.testing.assert_frame_equal(df_split, df_records)

    def test_nested_data_produces_same_dataframe(self):
        """Both formats produce identical DataFrames for nested data."""
        nested_obj = {"kind": "Unit", "name": "percent"}

        split_json = json.dumps({
            "columns": ["SamplesAnalysisID", "Meta"],
            "index": [0],
            "data": [["id:123", [nested_obj]]],
        })

        records_json = json.dumps([
            {"SamplesAnalysisID": "id:123", "Meta": [nested_obj]},
        ])

        df_split = pd.read_json(io.StringIO(split_json), orient="split")
        df_records = pd.read_json(io.StringIO(records_json), orient="records")

        pd.testing.assert_frame_equal(df_split, df_records)

    def test_null_values_produce_same_dataframe(self):
        """Both formats handle null values identically."""
        split_json = json.dumps({
            "columns": ["A", "B"],
            "index": [0],
            "data": [[1, None]],
        })

        records_json = json.dumps([
            {"A": 1, "B": None},
        ])

        df_split = pd.read_json(io.StringIO(split_json), orient="split")
        df_records = pd.read_json(io.StringIO(records_json), orient="records")

        pd.testing.assert_frame_equal(df_split, df_records)

    def test_cec_example_produces_same_dataframe(self):
        """CEC SAT type example produces identical DataFrames."""
        meta = [{"kind": "Unit", "name": "percentage", "propertyNames": ["CeC"]}]

        split_json = json.dumps({
            "columns": ["SamplesAnalysisID", "SampleID", "Meta", "CeC", "Qv"],
            "index": [0],
            "data": [["wpc:123:", "sample:456:", meta, 0.563, 0.975]],
        })

        records_json = json.dumps([{
            "SamplesAnalysisID": "wpc:123:",
            "SampleID": "sample:456:",
            "Meta": meta,
            "CeC": 0.563,
            "Qv": 0.975,
        }])

        df_split = pd.read_json(io.StringIO(split_json), orient="split")
        df_records = pd.read_json(io.StringIO(records_json), orient="records")

        pd.testing.assert_frame_equal(df_split, df_records)


class TestParquetEquivalence:
    """Tests that both formats produce identical parquet files."""

    def test_simple_data_produces_same_parquet(self):
        """Both formats produce identical parquet bytes."""
        split_json = json.dumps({
            "columns": ["A", "B"],
            "index": [0, 1],
            "data": [[1, 2], [3, 4]],
        })

        records_json = json.dumps([
            {"A": 1, "B": 2},
            {"A": 3, "B": 4},
        ])

        df_split = pd.read_json(io.StringIO(split_json), orient="split")
        df_records = pd.read_json(io.StringIO(records_json), orient="records")

        # Convert to parquet and back to verify content equivalence
        parquet_split = df_split.to_parquet(index=False)
        parquet_records = df_records.to_parquet(index=False)

        # Read back and compare
        df_from_split = pd.read_parquet(io.BytesIO(parquet_split))
        df_from_records = pd.read_parquet(io.BytesIO(parquet_records))

        pd.testing.assert_frame_equal(df_from_split, df_from_records)

    def test_complex_nested_data_produces_same_parquet(self):  # noqa: WPS210
        """Complex nested data produces equivalent parquet files."""
        nested_data = {
            "TestConditionID": "ref:data:123",
            "Values": [1.0, 2.0, 3.0],
        }

        split_json = json.dumps({
            "columns": ["ID", "Data"],
            "index": [0],
            "data": [["id:1", nested_data]],
        })

        records_json = json.dumps([
            {"ID": "id:1", "Data": nested_data},
        ])

        df_split = pd.read_json(io.StringIO(split_json), orient="split")
        df_records = pd.read_json(io.StringIO(records_json), orient="records")

        # Convert to parquet and back
        parquet_split = df_split.to_parquet(index=False)
        parquet_records = df_records.to_parquet(index=False)

        df_from_split = pd.read_parquet(io.BytesIO(parquet_split))
        df_from_records = pd.read_parquet(io.BytesIO(parquet_records))

        pd.testing.assert_frame_equal(df_from_split, df_from_records)


class TestRecordsNanValidationBypass:
    """Regression tests for records-format NaN validation bypass.

    When records format has a missing optional object/list field, pd.read_json
    with orient='records' produces NaN (not None). The bulk_mode NaN filter
    in DataValidator could then suppress the entire row error, including
    real validation failures like regex violations on other fields.

    The fix normalizes NaN to None in object columns after pd.read_json
    with orient='records', matching the split-path behavior.
    """

    @pytest.mark.asyncio
    async def test_invalid_regex_not_masked_by_missing_optional_field(self):
        """Regex violation must be caught even when optional field is absent."""
        valid_id = "osdu:work-product-component--SamplesAnalysis:test:"
        invalid_id = "INVALID-NO-MATCH!!!"
        meta = [{"kind": "Unit", "name": "psi"}]
        valid_sat = "osdu:reference-data--SaturationProcessMethod:primary:"

        records_json = json.dumps([
            {
                "SamplesAnalysisID": valid_id,
                "SampleID": "osdu:master-data--Sample:s1:",
                "Meta": meta,
                "SaturationProcessMethodID": valid_sat,
            },
            {
                "SamplesAnalysisID": invalid_id,
                "SampleID": "osdu:master-data--Sample:s2:",
                "Meta": meta,
            },
        ])

        df = pd.read_json(io.StringIO(records_json), orient="records")

        # Apply the fix: normalize NaN to None in object columns
        from app.api.routes.data.api import _normalize_nan_to_none
        _normalize_nan_to_none(df)

        mock_storage = await build_mock_get_storage_service(
            record_data=None, data_payload=df,
        )()
        schema = build_data_schema(CapillaryPressureModel100)
        validator = DataValidator(schema, mock_storage, API_VERSION_V2)

        errors = await validator.validate(df, bulk_mode=True)
        assert errors, "Invalid SamplesAnalysisID regex should be caught"

    @pytest.mark.asyncio
    async def test_nan_without_fix_masks_regex_error(self):
        """Demonstrates the bug: without NaN normalization, regex error is masked."""
        valid_id = "osdu:work-product-component--SamplesAnalysis:test:"
        invalid_id = "INVALID-NO-MATCH!!!"
        meta = [{"kind": "Unit", "name": "psi"}]
        valid_sat = "osdu:reference-data--SaturationProcessMethod:primary:"

        records_json = json.dumps([
            {
                "SamplesAnalysisID": valid_id,
                "SampleID": "osdu:master-data--Sample:s1:",
                "Meta": meta,
                "SaturationProcessMethodID": valid_sat,
            },
            {
                "SamplesAnalysisID": invalid_id,
                "SampleID": "osdu:master-data--Sample:s2:",
                "Meta": meta,
            },
        ])

        # Read WITHOUT the NaN->None fix (the old buggy behavior)
        df = pd.read_json(io.StringIO(records_json), orient="records")

        # Confirm the bug precondition: optional field is NaN, not None
        assert pd.isna(df["SaturationProcessMethodID"].iloc[1]), "Missing field is NaN"

        mock_storage = await build_mock_get_storage_service(
            record_data=None, data_payload=df,
        )()
        schema = build_data_schema(CapillaryPressureModel100)
        validator = DataValidator(schema, mock_storage, API_VERSION_V2)

        # Without the fix, bulk_mode NaN filter suppresses the regex error
        errors = await validator.validate(df, bulk_mode=True)
        assert not errors, "Bug: NaN in optional field masks the regex violation"

    @pytest.mark.asyncio
    async def test_records_nan_normalized_to_none_in_object_columns(self):
        """After NaN normalization, object columns have None instead of NaN."""
        records_json = json.dumps([
            {"ID": "a", "OptionalObj": {"nested": True}},
            {"ID": "b"},
        ])

        from app.api.routes.data.api import _normalize_nan_to_none

        df = pd.read_json(io.StringIO(records_json), orient="records")
        assert pd.isna(df["OptionalObj"].iloc[1]), "Before fix: NaN"

        _normalize_nan_to_none(df)

        assert df["OptionalObj"].iloc[1] is None, "After fix: None"
        assert df["OptionalObj"].iloc[0] == {"nested": True}, "Non-null preserved"
