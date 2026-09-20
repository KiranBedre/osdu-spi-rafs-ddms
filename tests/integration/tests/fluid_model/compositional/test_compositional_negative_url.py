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


def test_compositional_negative_invalid_regex_record_id_in_url(
    api,
    tests_data,
    fluid_model_type,
):
    """Reject a record ID not matching the FluidModel OSDU pattern with 422."""
    record_id = "invalid_id"
    data_payload = copy.deepcopy(
        tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1)
    )
    data_payload["data"][0][0] = f"{record_id}:"

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
    assert "Unprocessable entity." in body["reason"]
    assert (
        "work-product-component--FluidModel ID is not provided in expected OSDU pattern "
        '"^[\\w\\-\\.]+:work-product-component--FluidModel:[\\w\\-\\.\\:\\%]+$"'
    ) in body["errors"]


def test_compositional_negative_get_data_invalid_regex_record_id_in_url(
    api,
    dataset_id,
    fluid_model_type,
):
    """Reject Compositional data retrieval with record ID not matching the FluidModel OSDU pattern."""
    record_id = "invalid_id"

    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert any(
        "work-product-component--FluidModel ID is not provided in expected OSDU pattern"
        in error
        for error in body["errors"]
    )


def test_compositional_negative_invalid_data_partition_id_record_id_in_url(
    api,
    tests_data,
    fluid_model_type,
):
    """Reject a FluidModel record ID from another partition with 400."""
    record_id = "WrongID:work-product-component--FluidModel:Test123"
    data_payload = copy.deepcopy(
        tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1)
    )
    data_payload["data"][0][0] = f"{record_id}:"

    response = api.fluid_model.post_data(
        record_id=record_id,
        body=data_payload,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        allowed_codes=[status.HTTP_400_BAD_REQUEST],
        raw=True,
    )

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert "Invalid record ID" in body["reason"]
    assert (
        f"The record '{record_id}' does not belong to account '{DATA_PARTITION_ID}'"
        in body["message"]
    )


def test_compositional_negative_non_existing_record_id_in_url(
    api,
    tests_data,
    fluid_model_type,
):
    """Reject Compositional content upload for a non-existent FluidModel record with 404."""
    record_id = f"{DATA_PARTITION_ID}:work-product-component--FluidModel:NonExistingID"
    data_payload = copy.deepcopy(
        tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1)
    )
    data_payload["data"][0][0] = f"{record_id}:"

    response = api.fluid_model.post_data(
        record_id=record_id,
        body=data_payload,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        allowed_codes=[status.HTTP_404_NOT_FOUND],
        raw=True,
    )

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert "Record not found" in body["reason"]
    assert (
        f"The record '{record_id}' was not found" in body["message"]
        or f"Record with id '{record_id}' does not exist" in body["message"]
    )


def test_compositional_negative_get_data_non_existing_record_id_in_url(
    api,
    dataset_id,
    fluid_model_type,
):
    """Reject Compositional data retrieval for a non-existent FluidModel record with 404."""
    record_id = f"{DATA_PARTITION_ID}:work-product-component--FluidModel:NonExistingID"

    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        allowed_codes=[status.HTTP_404_NOT_FOUND],
        raw=True,
    )

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert "Record not found" in body["reason"]
    assert (
        f"The record '{record_id}' was not found" in body["message"]
        or f"Record with id '{record_id}' does not exist" in body["message"]
    )


def test_compositional_negative_get_data_invalid_regex_dataset_id_in_url(
    api,
    record_id,
    fluid_model_type,
):
    """Reject Compositional data retrieval with content ID not matching UUID or OSDU format."""
    dataset_id = "invalid_id"

    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert any(
        "content_id string does not match regex" in error for error in body["errors"]
    )


def test_compositional_negative_get_data_unsupported_schema_version(
    api,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Reject unsupported Compositional schema version with 404 Not Found."""
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version="9.0.0",
        allowed_codes=[status.HTTP_404_NOT_FOUND],
        raw=True,
    )

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert (
        "Model not found for type 'compositionalfluidmodel',  version '9.0.0'. "
        "Available versions: {'1.0.0'}"
    ) in body["reason"]


def test_compositional_negative_get_data_malformed_schema_version(
    api,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Reject malformed content_schema_version query parameter with 422."""
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version="abc",
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert (
        "Invalid version format in content_schema_version: 'abc'. Expected format: major.minor.patch (e.g. 1.0.0)"
    ) in body["reason"]


def test_compositional_negative_get_data_missing_schema_version(
    api,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Reject Compositional data retrieval when neither query nor Accept header supplies a schema version."""
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=None,
        headers={"Accept": None},
        allowed_codes=[status.HTTP_406_NOT_ACCEPTABLE],
        raw=True,
    )

    # Assert
    assert response.status_code == 406
    body = response.json()
    assert "No schema version specified or invalid schema format" in body["reason"]


def test_compositional_negative_get_data_dataset_id_not_linked_to_record(
    api,
    fresh_record_id,
    dataset_id,
    fluid_model_type,
):
    """Reject Compositional data retrieval when the content ID is not linked to the FluidModel record."""
    response = api.fluid_model.get_data(
        record_id=fresh_record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        allowed_codes=[status.HTTP_404_NOT_FOUND],
        raw=True,
    )

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert "Not found." in body["reason"]
    assert "does not exist in current record." in body["message"]


def test_compositional_negative_get_data_invalid_columns_filter_param(
    api,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Reject non-existent columns in Compositional columns filter with 422."""
    params = {"columns_filter": "UnknownColumn"}

    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Invalid columns:" in body["reason"]


def test_compositional_negative_get_data_invalid_rows_filter_format_param(
    api,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Reject badly formatted Compositional rows filter with 422."""
    params = {"rows_filter": "Invalid syntax"}

    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Bad rows_filter expression. Correct format" in body["reason"]


def test_compositional_negative_get_data_invalid_rows_filter_column_param(
    api,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Reject non-existent columns in Compositional rows filter with 422."""
    params = {"rows_filter": f"UnknownColumn,eq,{record_id}:"}

    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "For filter select one of" in body["reason"]


def test_compositional_negative_get_data_invalid_rows_filter_operator_param(
    api,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Reject unsupported operators in Compositional rows filter with 422."""
    params = {"rows_filter": f"FluidModelID,equal,{record_id}:"}

    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Invalid comparison operator 'equal'" in body["reason"]


def test_compositional_negative_get_data_invalid_columns_aggregation_column_param(
    api,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Reject non-existent columns in Compositional columns aggregation with 422."""
    params = {"columns_aggregation": "UnknownColumn,describe"}

    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "For aggregation select one of" in body["reason"]


def test_compositional_negative_get_data_invalid_columns_aggregation_operator_param(
    api,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Reject unsupported operators in Compositional columns aggregation with 422."""
    params = {"columns_aggregation": "FluidModelID,avg"}

    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Invalid aggregation operator 'avg'" in body["reason"]
