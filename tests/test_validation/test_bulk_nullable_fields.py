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

"""Test bulk ingestion with nullable optional object fields.

This test demonstrates the issue where bulk ingestion fails when some records
have optional object fields populated while others don't, resulting in NaN values
that fail validation.
"""

import io

import pandas as pd
import pytest

from app.bulk_data_validation.data_validation import DataValidator
from app.models.data_schemas.data_schema import build_data_schema
from app.models.data_schemas.sample_analysis_api_v2.capillary_pressure_data_model_1_0_0 import (
    CapillaryPressureModel100,
)
from tests.test_api.api_version import API_VERSION_V2
from tests.test_api.test_routes.data.data_mock_objects import (
    build_mock_get_storage_service,
)

# Single record - no nullable issue (should pass strict validation)
SINGLE_RECORD_PAYLOAD = """{
    "columns": [
        "SamplesAnalysisID",
        "SampleID",
        "Meta"
    ],
    "index": [0],
    "data": [
        [
            "osdu-dev:work-product-component--SamplesAnalysis:test-analysis:",
            "osdu-dev:master-data--Sample:test-sample:",
            []
        ]
    ]
}"""

# Bulk records where ALL rows have null for InitialConditions
# When ALL values in a column are null, pandas converts to float64/NaN
# This causes validation failure because NaN is not a valid object
BULK_RECORDS_ALL_NULL_OPTIONAL_FIELD = """{
    "columns": [
        "SamplesAnalysisID",
        "SampleID",
        "Meta",
        "InitialConditions"
    ],
    "index": [0, 1, 2],
    "data": [
        [
            "osdu-dev:work-product-component--SamplesAnalysis:test-1:",
            "osdu-dev:master-data--Sample:test-sample-1:",
            [],
            null
        ],
        [
            "osdu-dev:work-product-component--SamplesAnalysis:test-2:",
            "osdu-dev:master-data--Sample:test-sample-2:",
            [],
            null
        ],
        [
            "osdu-dev:work-product-component--SamplesAnalysis:test-3:",
            "osdu-dev:master-data--Sample:test-sample-3:",
            [],
            null
        ]
    ]
}"""


@pytest.mark.asyncio
async def test_single_record_strict_validation_passes():
    """Test that single record ingestion passes strict validation.

    Single records can properly omit optional fields, so strict validation works.
    """
    test_df = pd.read_json(io.StringIO(SINGLE_RECORD_PAYLOAD), orient="split")
    mock_storage_service = await build_mock_get_storage_service(record_data=None, data_payload=test_df)()
    data_schema = build_data_schema(CapillaryPressureModel100)
    data_validator = DataValidator(data_schema, mock_storage_service, API_VERSION_V2)

    # Single record should pass with current validation
    errors = await data_validator.validate(test_df)
    assert not errors, f"Single record should pass validation, got errors: {errors}"


@pytest.mark.asyncio
async def test_bulk_records_all_null_optional_field_also_fails():
    """Test that bulk records where ALL rows have null for an optional field ALSO fail.

    When ALL values in an optional column are null, pandas converts it to float64/NaN.
    The current code at data_validation.py:66 has dropna(axis=1, how='all'), but it
    doesn't help because validation runs on the original DataFrame BEFORE dropping.

    This demonstrates that the bug affects multiple records too!
    """
    test_df = pd.read_json(io.StringIO(BULK_RECORDS_ALL_NULL_OPTIONAL_FIELD), orient="split")

    # Verify that InitialConditions became NaN (float64)
    assert test_df['InitialConditions'].dtype == 'float64', "All-null column should be float64"
    assert all(pd.isna(test_df['InitialConditions'])), "All InitialConditions should be NaN"

    mock_storage_service = await build_mock_get_storage_service(record_data=None, data_payload=test_df)()
    data_schema = build_data_schema(CapillaryPressureModel100)
    data_validator = DataValidator(data_schema, mock_storage_service, API_VERSION_V2)

    # This FAILS - the dropna doesn't help because validation happens first
    errors = await data_validator.validate(test_df)
    assert errors, "Expected validation errors - dropna doesn't prevent this!"
    assert "invalid_type" in errors, f"Expected invalid_type errors, got: {errors}"


@pytest.mark.asyncio
async def test_single_record_with_null_optional_field_fails():
    """Test that even a single record with null optional field fails validation.

    THE REAL BUG: When JSON has null for optional fields, pandas converts to NaN.
    Even with just 1 record, this causes validation failure.

    This matches the original issue from test_capillary_pressure_issue.py
    """
    test_df = pd.read_json(io.StringIO(BULK_RECORDS_ALL_NULL_OPTIONAL_FIELD), orient="split")

    # Take just the first record
    test_df = test_df.head(1)

    # Verify that InitialConditions is NaN (float64)
    assert test_df['InitialConditions'].dtype == 'float64', "Null converts to float64"
    assert pd.isna(test_df['InitialConditions'].iloc[0]), "InitialConditions should be NaN"

    mock_storage_service = await build_mock_get_storage_service(record_data=None, data_payload=test_df)()
    data_schema = build_data_schema(CapillaryPressureModel100)
    data_validator = DataValidator(data_schema, mock_storage_service, API_VERSION_V2)

    # This FAILS because NaN is not a valid object type
    errors = await data_validator.validate(test_df)
    assert errors, "Expected validation errors - this is the bug!"
    assert "invalid_type" in errors, f"Expected invalid_type errors, got: {errors}"


@pytest.mark.asyncio
async def test_records_with_null_optional_fields_relaxed_validation_passes():
    """Test that records with null optional fields pass with bulk_mode=True.

    This test verifies the fix: bulk_mode=True should allow NaN values in
    optional object fields.
    """
    test_df = pd.read_json(io.StringIO(BULK_RECORDS_ALL_NULL_OPTIONAL_FIELD), orient="split")

    # Take just the first record to match the real bug
    test_df = test_df.head(1)

    # Verify NaN
    assert pd.isna(test_df['InitialConditions'].iloc[0]), "InitialConditions should be NaN"

    mock_storage_service = await build_mock_get_storage_service(record_data=None, data_payload=test_df)()
    data_schema = build_data_schema(CapillaryPressureModel100)
    data_validator = DataValidator(data_schema, mock_storage_service, API_VERSION_V2)

    # Should PASS with relaxed validation
    errors = await data_validator.validate(test_df, bulk_mode=True)
    assert not errors, f"Records should pass with relaxed validation, got errors: {errors}"


@pytest.mark.asyncio
async def test_required_field_with_nan_still_fails_in_bulk_mode():
    """Test that required fields with NaN still fail validation even in bulk_mode.

    This ensures the improved fix only filters NaN for optional fields,
    not required fields. Required fields must always be present and valid.
    """
    # Payload with NaN in a required field (SamplesAnalysisID)
    payload_missing_required = """{
        "columns": [
            "SamplesAnalysisID",
            "SampleID",
            "Meta"
        ],
        "index": [0],
        "data": [
            [
                null,
                "osdu-dev:master-data--Sample:test-sample:",
                []
            ]
        ]
    }"""

    test_df = pd.read_json(io.StringIO(payload_missing_required), orient="split")

    # Verify that SamplesAnalysisID is NaN
    assert pd.isna(test_df['SamplesAnalysisID'].iloc[0]), "SamplesAnalysisID should be NaN"

    mock_storage_service = await build_mock_get_storage_service(record_data=None, data_payload=test_df)()
    data_schema = build_data_schema(CapillaryPressureModel100)
    data_validator = DataValidator(data_schema, mock_storage_service, API_VERSION_V2)

    # Should FAIL even with bulk_mode=True because SamplesAnalysisID is required
    errors = await data_validator.validate(test_df, bulk_mode=True)
    assert errors, "Required field with NaN should fail validation even in bulk mode"
    assert "invalid_type" in errors or "invalid_value" in errors, \
        f"Expected validation error for required field, got: {errors}"
