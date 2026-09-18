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

"""Direct repro of GitLab issue #679 note #474398 (Viktoriia Lesina, 2026-09-11),
against the Reservoir Simulation Rock Physics model, in JSON split representation
exactly as QA described it, to independently verify what ci/integration actually
returns today (QA did not participate in reviewing the recent ci/integration fixes).
"""

import io

import pandas as pd
import pytest

from app.bulk_data_validation.data_validation import DataValidator
from app.models.data_schemas.data_schema import build_data_schema
from app.models.data_schemas.reservoir_simulation_rock_physics_v2.reservoir_simulation_rock_physics_model_data_model_1_0_0 import (  # noqa: E501
    ReservoirSimulationRockPhysicsModelModel100,
)
from tests.test_api.api_version import API_VERSION_V2
from tests.test_api.test_routes.data.data_mock_objects import StorageService

SPLIT_JSON_CONTROL = """
{
    "columns": ["ReservoirSimulationRockPhysicsID", "Compressibility", "ExtraColumn"],
    "index": [0],
    "data": [[
        "namespace:work-product-component--ReservoirSimulationRockPhysicsModel:uuid:0",
        {"ReferencePressure": 1000.0, "PoreVolumeCompressibilityAtReferencePressure": 0.0001},
        "ExtraValue"
    ]]
}
"""

SPLIT_JSON_NULL_EXTRA = """
{
    "columns": ["ReservoirSimulationRockPhysicsID", "Compressibility", "ExtraColumn"],
    "index": [0],
    "data": [[
        "namespace:work-product-component--ReservoirSimulationRockPhysicsModel:uuid:0",
        {"ReferencePressure": 1000.0, "PoreVolumeCompressibilityAtReferencePressure": 0.0001},
        null
    ]]
}
"""


async def _validate(split_json: str) -> dict:
    mock_storage_service = StorageService(record_data=None)
    schema = build_data_schema(ReservoirSimulationRockPhysicsModelModel100)
    data_validator = DataValidator(schema, mock_storage_service, API_VERSION_V2)
    test_df = pd.read_json(io.StringIO(split_json), orient="split")
    return await data_validator.validate(test_df, bulk_mode=True)


@pytest.mark.asyncio
async def test_qa_control_case_extra_column_with_value():
    """QA's control case: 'ExtraColumn': 'ExtraValue' -> must name the field."""
    errors = await _validate(SPLIT_JSON_CONTROL)
    print("\nCONTROL CASE (ExtraColumn='ExtraValue') ->", errors)
    fields = [entry["field"] for entry in errors["invalid_type"]]
    assert "ExtraColumn" in fields
    extra_error = errors["invalid_type"][fields.index("ExtraColumn")]
    assert extra_error["received"] == "present"
    assert extra_error["expected"] == "not allowed (extra field)"


@pytest.mark.asyncio
async def test_qa_note_474398_null_extra_column():
    """QA's exact repro from note #474398: 'ExtraColumn': null.

    The note reports this comes back as
    {"field": "DataSchema", "received": "{'ExtraColumn': nan}", "expected": "unknown"}.
    This asserts the current ci/integration code instead of trusting that claim.
    """
    errors = await _validate(SPLIT_JSON_NULL_EXTRA)
    print("\nNULL CASE (ExtraColumn=null) ->", errors)

    all_fields = [entry["field"] for category in errors.values() for entry in category]
    assert "DataSchema" not in all_fields, f"regression: bug from note #474398 reproduced! errors={errors}"

    fields = [entry["field"] for entry in errors["invalid_type"]]
    assert "ExtraColumn" in fields
    extra_error = errors["invalid_type"][fields.index("ExtraColumn")]
    assert extra_error["received"] == "null"
    assert extra_error["expected"] == "not allowed (extra field)"
