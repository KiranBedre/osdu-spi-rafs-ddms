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

from app.resources.common_headers import (
    ACCEPT,
    AUTHORIZATION,
    CONTENT_TYPE,
    DATA_PARTITION_ID,
)
from tests.integration.config import DataFiles, SchemaVersions


def test_compositional_negative_missing_authorization_header(
    api,
    tests_data,
    record_id,
    fluid_model_type,
):
    """Reject Compositional data upload without Authorization header with 401 Unauthorized."""
    data_payload = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    data_payload["data"][0][0] = f"{record_id}:"

    response = api.fluid_model.post_data(
        record_id=record_id,
        body=data_payload,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={AUTHORIZATION: None},
        allowed_codes=[status.HTTP_401_UNAUTHORIZED],
        raw=True,
    )

    # Assert
    assert response.status_code == 401
    body = response.json()
    assert "Not authenticated" in body["reason"]


def test_compositional_negative_invalid_access_token_authorization_header(
    api,
    tests_data,
    record_id,
    fluid_model_type,
):
    """Reject Compositional data upload with invalid Bearer token with 401 Unauthorized."""
    data_payload = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    data_payload["data"][0][0] = f"{record_id}:"

    response = api.fluid_model.post_data(
        record_id=record_id,
        body=data_payload,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={AUTHORIZATION: "Bearer dummy"},
        allowed_codes=[status.HTTP_401_UNAUTHORIZED],
        raw=True,
    )

    # Assert
    assert response.status_code == 401

    content_type = response.headers.get("content-type", "").lower()

    if "json" in content_type:
        body = response.json()
        assert "Access denied" in body["reason"]
        assert "The user is not authorized to perform this action" in body["message"]
    else:
        www_authenticate = response.headers.get("www-authenticate")
        assert www_authenticate is not None
        assert 'error="invalid_token"' in www_authenticate


def test_compositional_negative_missing_data_partition_id_header(
    api,
    tests_data,
    record_id,
    fluid_model_type,
):
    """Reject Compositional data upload without Data-Partition-ID header with 400 Bad Request."""
    data_payload = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    data_payload["data"][0][0] = f"{record_id}:"

    response = api.fluid_model.post_data(
        record_id=record_id,
        body=data_payload,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={DATA_PARTITION_ID: None},
        allowed_codes=[status.HTTP_400_BAD_REQUEST],
        raw=True,
    )

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert len(body["errors"]) == 1, f"Expected errors list length 1, got {len(body['errors'])}"
    assert "No data-partition-id in headers" in body["errors"]


def test_compositional_negative_missing_content_type_header(
    api,
    tests_data,
    record_id,
    fluid_model_type,
):
    """Reject Compositional data upload without Content-Type header with 400 Bad Request."""
    data_payload = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    data_payload["data"][0][0] = f"{record_id}:"

    response = api.fluid_model.post_data(
        record_id=record_id,
        body=data_payload,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={CONTENT_TYPE: None},
        allowed_codes=[status.HTTP_400_BAD_REQUEST],
        raw=True,
    )

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert "Content-Type header is required, but was not provided" in body["reason"]


@pytest.mark.parametrize(
    "unsupported_content_type",
    [
        "application/parquet",
        "application/xml",
    ],
)
def test_compositional_negative_unsupported_content_type_header(
    api,
    tests_data,
    record_id,
    fluid_model_type,
    unsupported_content_type,
):
    """Reject unsupported Compositional payload format with 415 Unsupported Media Type."""
    data_payload = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    data_payload["data"][0][0] = f"{record_id}:"

    response = api.fluid_model.post_data(
        record_id=record_id,
        body=data_payload,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={CONTENT_TYPE: unsupported_content_type},
        allowed_codes=[status.HTTP_415_UNSUPPORTED_MEDIA_TYPE],
        raw=True,
    )

    # Assert
    assert response.status_code == 415
    body = response.json()
    assert "The provided content-type is not supported." in body["reason"]


def test_compositional_negative_get_data_unsupported_accept_header(api, record_id, dataset_id, fluid_model_type):
    """Reject unsupported Compositional response format with 406 Not Acceptable."""
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={ACCEPT: "application/xml"},
        allowed_codes=[status.HTTP_406_NOT_ACCEPTABLE],
        raw=True,
    )

    # Assert
    assert response.status_code == 406
