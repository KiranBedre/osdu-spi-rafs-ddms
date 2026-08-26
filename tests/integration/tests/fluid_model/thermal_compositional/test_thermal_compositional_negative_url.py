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

from starlette import status

from tests.integration.config import CONFIG, DataFiles, SchemaVersions

DATA_PARTITION_ID = CONFIG["DATA_PARTITION"]


def _thermal_payload(tests_data, record_id):
    payload = copy.deepcopy(tests_data(DataFiles.THERMAL_COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    payload["data"][0][0] = f"{record_id}:"
    return payload


def test_thermal_compositional_negative_invalid_regex_record_id_in_url(api, tests_data, fluid_model_type):
    """Reject a Thermal POST record ID outside the FluidModel OSDU pattern."""
    record_id = "invalid_id"
    response = api.fluid_model.post_data(
        record_id=record_id,
        body=_thermal_payload(tests_data, record_id),
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    assert response.status_code == 422
    assert "Unprocessable entity." in response.json()["reason"]


def test_thermal_compositional_negative_get_data_invalid_regex_record_id_in_url(api, dataset_id, fluid_model_type):
    """Reject a Thermal GET record ID outside the FluidModel OSDU pattern."""
    response = api.fluid_model.get_data(
        record_id="invalid_id",
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    assert response.status_code == 422
    assert "Unprocessable entity." in response.json()["reason"]


def test_thermal_compositional_negative_get_data_invalid_regex_dataset_id_in_url(api, record_id, fluid_model_type):
    """Reject a Thermal content ID outside the supported ID patterns."""
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id="invalid_id",
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    assert response.status_code == 422
    assert any("content_id string does not match regex" in error for error in response.json()["errors"])


def test_thermal_compositional_negative_get_data_unsupported_schema_version(
    api, record_id, dataset_id, fluid_model_type
):
    """Reject a well-formed unsupported Thermal schema version with 404."""
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version="9.0.0",
        allowed_codes=[status.HTTP_404_NOT_FOUND],
        raw=True,
    )

    assert response.status_code == 404
    assert (
        "Model not found for type 'thermalcompositionalfluidmodel',  version '9.0.0'. " "Available versions: {'1.0.0'}"
    ) in response.json()["reason"]


def test_thermal_compositional_negative_get_data_malformed_schema_version(api, record_id, dataset_id, fluid_model_type):
    """Reject a malformed Thermal schema version with 422."""
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version="abc",
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    assert response.status_code == 422
    assert (
        "Invalid version format in content_schema_version: 'abc'. Expected format: " "major.minor.patch (e.g. 1.0.0)"
    ) in response.json()["reason"]


def test_thermal_compositional_negative_get_data_missing_schema_version(api, record_id, dataset_id, fluid_model_type):
    """Reject Thermal GET when neither query nor Accept supplies a version."""
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=None,
        headers={"Accept": None},
        allowed_codes=[status.HTTP_406_NOT_ACCEPTABLE],
        raw=True,
    )

    assert response.status_code == 406
    assert "No schema version specified or invalid schema format" in response.json()["reason"]


def test_thermal_compositional_negative_get_data_invalid_columns_filter_param(
    api, record_id, dataset_id, fluid_model_type
):
    """Reject unknown Thermal columns_filter columns with 422."""
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params={"columns_filter": "UnknownColumn"},
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    assert response.status_code == 422
    assert "Invalid columns:" in response.json()["reason"]


def test_thermal_compositional_negative_get_data_invalid_rows_filter_operator_param(
    api, record_id, dataset_id, fluid_model_type
):
    """Reject unsupported Thermal rows_filter operators with 422."""
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params={"rows_filter": f"FluidModelID,equal,{record_id}:"},
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    assert response.status_code == 422
    assert "Invalid comparison operator 'equal'" in response.json()["reason"]


def test_thermal_compositional_negative_get_data_invalid_columns_aggregation_operator_param(
    api, record_id, dataset_id, fluid_model_type
):
    """Reject unsupported Thermal aggregation operators with 422."""
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params={"columns_aggregation": "FluidModelID,avg"},
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    assert response.status_code == 422
    assert "Invalid aggregation operator 'avg'" in response.json()["reason"]


def test_thermal_compositional_negative_get_data_non_existing_dataset_id_in_url(api, record_id, fluid_model_type):
    """Reject a valid-format Thermal dataset ID absent from the WPC."""
    dataset_id = f"{DATA_PARTITION_ID}:dataset--File.Generic:" "thermalcompositionalfluidmodel-InvalidId"
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        allowed_codes=[status.HTTP_404_NOT_FOUND],
        raw=True,
    )

    assert response.status_code == 404
    body = response.json()
    assert "Not found." in body["reason"]
    assert f"{dataset_id} does not exist in current record." in body["message"]
