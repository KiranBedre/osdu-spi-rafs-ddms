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


def test_compositional_negative_add_data_v1_model_invalid_json(
    api,
    tests_data,
    record_id,
    fluid_model_type,
):
    """Reject Compositional JSON that does not match the Compositional model with 422."""
    data_payload = copy.deepcopy(
        tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1)
    )
    data_payload["data"][0][0] = f"{record_id}:"
    column_index = data_payload["columns"].index("OilViscosityModelTypeID")
    data_payload["data"][0][column_index] = "not-a-reference-id"

    response = api.fluid_model.post_data(
        record_id=record_id,
        body=data_payload,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]


def test_compositional_negative_add_data_v1_columns_and_data_length_mismatch(
    api,
    tests_data,
    record_id,
    fluid_model_type,
):
    """Reject Compositional JSON that cannot be converted to a DataFrame with 422."""
    data_payload = copy.deepcopy(
        tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1)
    )
    data_payload["data"][0][0] = f"{record_id}:"
    data_payload["columns"].append("UnexpectedColumn")

    response = api.fluid_model.post_data(
        record_id=record_id,
        body=data_payload,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    assert response.json()["reason"]


@pytest.mark.parametrize(
    "invalid_parquet_payload",
    [
        b"",
        b"not-a-parquet-file",
    ],
)
def test_compositional_negative_add_data_v1_invalid_parquet_bytes(
    api,
    record_id,
    fluid_model_type,
    invalid_parquet_payload,
):
    """Reject empty or unreadable Compositional Parquet bytes with 422."""
    response = api.fluid_model.post_data(
        record_id=record_id,
        body=invalid_parquet_payload,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={CONTENT_TYPE: "application/x-parquet"},
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    assert response.json()["reason"]


def test_compositional_negative_add_data_v1_model_invalid_parquet(
    api,
    tests_data,
    record_id,
    fluid_model_type,
):
    """Reject readable Compositional Parquet that does not match the Compositional model with 422."""
    data_payload = copy.deepcopy(
        tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1)
    )
    data_payload["data"][0][0] = f"{record_id}:"
    column_index = data_payload["columns"].index("OilViscosityModelTypeID")
    data_payload["data"][0][column_index] = "not-a-reference-id"
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

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
