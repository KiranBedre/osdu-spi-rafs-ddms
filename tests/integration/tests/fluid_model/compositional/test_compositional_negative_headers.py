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


def test_compositional_negative_missing_content_type_header(
    api,
    tests_data,
    record_id,
    fluid_model_type,
):
    """Reject Compositional data upload without Content-Type header with 400 Bad Request."""
    data_payload = copy.deepcopy(
        tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1)
    )
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
    data_payload = copy.deepcopy(
        tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1)
    )
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
