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

import copy

import pandas as pd
import pytest
from starlette import status

from app.resources.common_headers import CONTENT_TYPE
from tests.integration.config import DataFiles, SchemaVersions


def _thermal_payload(tests_data, record_id):
    payload = copy.deepcopy(tests_data(DataFiles.THERMAL_COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    payload["data"][0][0] = f"{record_id}:"
    return payload


def test_thermal_compositional_negative_add_data_v1_missing_required_name(api, tests_data, record_id, fluid_model_type):
    """Reject Thermal Compositional JSON missing required Name with 422."""
    data_payload = _thermal_payload(tests_data, record_id)
    column_index = data_payload["columns"].index("Name")
    data_payload["columns"].pop(column_index)
    data_payload["data"][0].pop(column_index)

    response = api.fluid_model.post_data(
        record_id=record_id,
        body=data_payload,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    assert response.status_code == 422
    assert "Data validation failed." in response.json()["reason"]


def test_thermal_compositional_negative_add_data_v1_invalid_molecular_weight_type(
    api, tests_data, record_id, fluid_model_type
):
    """Reject a non-array ComponentProperties.MolecularWeight with 422."""
    data_payload = _thermal_payload(tests_data, record_id)
    column_index = data_payload["columns"].index("ComponentProperties")
    data_payload["data"][0][column_index]["MolecularWeight"] = "not-an-array"

    response = api.fluid_model.post_data(
        record_id=record_id,
        body=data_payload,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    assert response.status_code == 422
    assert "Data validation failed." in response.json()["reason"]


def test_thermal_compositional_negative_add_data_v1_invalid_payload_format(
    api, tests_data, record_id, fluid_model_type
):
    """Reject Thermal split JSON wrapped in an outer array with 422."""
    data_payload = _thermal_payload(tests_data, record_id)

    response = api.fluid_model.post_data(
        record_id=record_id,
        body=[data_payload],
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    assert response.status_code == 422
    assert (
        "Data error: split format must be a JSON object, not wrapped in an array. " "Remove the outer [] brackets."
    ) in response.json()["reason"]


@pytest.mark.parametrize("invalid_parquet_payload", [b"", b"not-a-parquet-file"])
def test_thermal_compositional_negative_add_data_v1_invalid_parquet_bytes(
    api, record_id, fluid_model_type, invalid_parquet_payload
):
    """Reject empty or unreadable Thermal Compositional Parquet with 422."""
    response = api.fluid_model.post_data(
        record_id=record_id,
        body=invalid_parquet_payload,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={CONTENT_TYPE: "application/x-parquet"},
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    assert response.status_code == 422
    assert response.json()["reason"]


def test_thermal_compositional_negative_add_data_v1_model_invalid_parquet(api, tests_data, record_id, fluid_model_type):
    """Reject readable Parquet that does not match the Thermal model with 422."""
    data_payload = _thermal_payload(tests_data, record_id)
    column_index = data_payload["columns"].index("ComponentProperties")
    data_payload["data"][0][column_index]["MolecularWeight"] = "not-an-array"
    dataframe = pd.DataFrame(
        data_payload["data"],
        columns=data_payload["columns"],
        index=data_payload["index"],
    )

    response = api.fluid_model.post_data(
        record_id=record_id,
        body=dataframe.to_parquet(),
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={CONTENT_TYPE: "application/x-parquet"},
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    assert response.status_code == 422
    assert "Data validation failed." in response.json()["reason"]
