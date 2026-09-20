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

import pytest
from starlette import status

from app.resources.common_headers import CONTENT_TYPE
from tests.integration.config import DataFiles, SchemaVersions

GENERIC_MANDATORY_DATA_FIELDS = [
    "/columns",
    "/index",
    "/data",
]

SPECIFIC_MANDATORY_DATA_MAIN_COLUMNS = [
    ("/columns/0", "/data/0/0"),  # FluidModelID
    ("/columns/1", "/data/0/1"),  # Meta
]

OIL_TABLE_REQUIRED_FIELDS = [
    "/data/0/2/0/BubblePointPressure",
    "/data/0/2/0/SolutionGOR",
    "/data/0/2/0/Pressure",
    "/data/0/2/0/FormationVolumeFactor",
    "/data/0/2/0/Viscosity",
]

SPECIFIC_INVALID_TYPE_DATA_V1_FIELDS = [
    ("/data/0/0", ["FluidModelID"]),  # FluidModelID must be a string
    ("/data/0/1", "Meta"),  # Meta must be an array
    ("/data/0/2", "OilTable"),  # OilTable must be an array
    ("/data/0/2/0/BubblePointPressure", "BubblePointPressure"),  # BubblePointPressure must be an array
    ("/data/0/2/0/Pressure", "Pressure"),  # Pressure must be an array
    ("/data/0/2/0/Viscosity/0", "Viscosity"),  # Viscosity items must be numeric
]


@pytest.mark.parametrize("field_path", GENERIC_MANDATORY_DATA_FIELDS)
def test_black_oil_negative_add_data_v1_missing_mandatory_generic_field(
    api,
    tests_data,
    helper,
    field_path,
    record_id,
    fluid_model_type,
):
    """Reject Black Oil JSON missing a required split-format field with 422."""
    data_payload = copy.deepcopy(tests_data(DataFiles.BLACK_OIL_FLUID_MODEL_DATA_V1))
    data_payload["data"][0][0] = f"{record_id}:"
    helper.delete_by_path(data_payload, field_path)
    field_name = field_path.split("/")[-1]

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
    assert f"Data error: missing required fields: '{field_name}'." in body["reason"]


@pytest.mark.parametrize("main_column,main_column_value", SPECIFIC_MANDATORY_DATA_MAIN_COLUMNS)
def test_black_oil_negative_add_data_v1_missing_mandatory_main_column(
    api,
    tests_data,
    helper,
    main_column,
    main_column_value,
    record_id,
    fluid_model_type,
):
    """Reject Black Oil content missing a required schema column with 422."""
    data_payload = copy.deepcopy(tests_data(DataFiles.BLACK_OIL_FLUID_MODEL_DATA_V1))
    data_payload["data"][0][0] = f"{record_id}:"
    helper.delete_by_path(data_payload, main_column)
    helper.delete_by_path(data_payload, main_column_value)

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


@pytest.mark.parametrize("field_path", OIL_TABLE_REQUIRED_FIELDS)
def test_black_oil_negative_add_data_v1_missing_required_oil_table_field(
    api,
    tests_data,
    helper,
    field_path,
    record_id,
    fluid_model_type,
):
    """Reject OilTable item missing a required Black Oil property with 422."""
    data_payload = copy.deepcopy(tests_data(DataFiles.BLACK_OIL_FLUID_MODEL_DATA_V1))
    data_payload["data"][0][0] = f"{record_id}:"
    helper.delete_by_path(data_payload, field_path)

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


@pytest.mark.parametrize("field_path,value", SPECIFIC_INVALID_TYPE_DATA_V1_FIELDS)
def test_black_oil_negative_add_data_v1_invalid_type_specific_field(
    api,
    tests_data,
    helper,
    field_path,
    value,
    record_id,
    fluid_model_type,
):
    """Reject Black Oil content containing a property with an invalid type with 422."""
    data_payload = copy.deepcopy(tests_data(DataFiles.BLACK_OIL_FLUID_MODEL_DATA_V1))
    data_payload["data"][0][0] = f"{record_id}:"
    helper.set_by_path(data_payload, field_path, value)

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


def test_black_oil_negative_add_data_v1_invalid_payload_format(
    api,
    tests_data,
    record_id,
    fluid_model_type,
):
    """Reject Black Oil split JSON wrapped in an outer array with 422."""
    data_payload = copy.deepcopy(tests_data(DataFiles.BLACK_OIL_FLUID_MODEL_DATA_V1))

    response = api.fluid_model.post_data(
        record_id=record_id,
        body=[data_payload],
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert (
        "Data error: split format must be a JSON object, not wrapped in an array. Remove the outer [] brackets."
        in body["reason"]
    )


def test_black_oil_negative_add_data_v1_columns_and_data_length_mismatch(
    api,
    tests_data,
    record_id,
    fluid_model_type,
):
    """Reject Black Oil JSON that cannot be converted to a DataFrame with 422."""
    data_payload = copy.deepcopy(tests_data(DataFiles.BLACK_OIL_FLUID_MODEL_DATA_V1))
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


def test_black_oil_negative_add_data_v1_record_id_mismatch_between_payload_and_url(
    api,
    tests_data,
    record_id,
    fresh_record_id,
    fluid_model_type,
):
    """Reject Black Oil content whose FluidModelID differs from the URL record ID."""
    data_payload = copy.deepcopy(tests_data(DataFiles.BLACK_OIL_FLUID_MODEL_DATA_V1))
    data_payload["data"][0][0] = f"{fresh_record_id}:"

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
    assert body["errors"]["Invalid value"][0]["FluidModelID"] == f"{fresh_record_id}:"


def test_black_oil_negative_add_data_v1_malformed_schema_version(
    api,
    tests_data,
    record_id,
    fluid_model_type,
):
    """Reject malformed content_schema_version query parameter for Black Oil upload with 422."""
    data_payload = copy.deepcopy(tests_data(DataFiles.BLACK_OIL_FLUID_MODEL_DATA_V1))
    data_payload["data"][0][0] = f"{record_id}:"

    response = api.fluid_model.post_data(
        record_id=record_id,
        body=data_payload,
        fluid_model_type=fluid_model_type,
        schema_version="0",
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    assert (
        "Invalid version format in content_schema_version: '0'. Expected format: major.minor.patch (e.g. 1.0.0)"
        in response.json()["reason"]
    )


@pytest.mark.parametrize(
    "invalid_parquet_payload",
    [
        b"",
        b"not-a-parquet-file",
    ],
)


def test_black_oil_negative_add_data_v1_invalid_parquet_bytes(
    api,
    record_id,
    fluid_model_type,
    invalid_parquet_payload,
):
    """Reject empty or unreadable Black Oil Parquet bytes with 422."""
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
