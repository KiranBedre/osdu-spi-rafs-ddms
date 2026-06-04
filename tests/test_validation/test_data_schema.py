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
async def test_pydantic_model_validation_error_received_truncated():
    mock_storage_service = StorageService(record_data=None)
    rca_schema = build_data_schema(RoutineCoreAnalysisModel100)
    data_validator = DataValidator(rca_schema, mock_storage_service, API_VERSION_V2)

    long_val = "x" * 500
    raw_failure = repr({"SamplesAnalysisID": long_val})
    result = data_validator._enrich_pydantic_error(raw_failure)

    assert len(result) == 1
    assert result[0]["field"] == "SamplesAnalysisID"
    assert result[0]["received"].endswith("...[truncated]")
    assert len(result[0]["received"]) == _MAX_RECEIVED_REPR_LEN + len("...[truncated]")
