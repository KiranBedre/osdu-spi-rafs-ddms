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

from app.resources.common_headers import ACCEPT, CONTENT_TYPE
from tests.integration.config import DataFiles, SchemaVersions


def _thermal_payload(tests_data, record_id):
    payload = copy.deepcopy(tests_data(DataFiles.THERMAL_COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    payload["data"][0][0] = f"{record_id}:"
    return payload


def test_thermal_compositional_negative_missing_content_type_header(api, tests_data, record_id, fluid_model_type):
    """Reject Thermal Compositional upload without Content-Type with 400."""
    response = api.fluid_model.post_data(
        record_id=record_id,
        body=_thermal_payload(tests_data, record_id),
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={CONTENT_TYPE: None},
        allowed_codes=[status.HTTP_400_BAD_REQUEST],
        raw=True,
    )

    assert response.status_code == 400
    assert "Content-Type header is required, but was not provided" in response.json()["reason"]


@pytest.mark.parametrize(
    "unsupported_content_type",
    ["application/parquet", "application/xml"],
)
def test_thermal_compositional_negative_unsupported_content_type_header(
    api, tests_data, record_id, fluid_model_type, unsupported_content_type
):
    """Reject unsupported Thermal Compositional payload formats with 415."""
    response = api.fluid_model.post_data(
        record_id=record_id,
        body=_thermal_payload(tests_data, record_id),
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={CONTENT_TYPE: unsupported_content_type},
        allowed_codes=[status.HTTP_415_UNSUPPORTED_MEDIA_TYPE],
        raw=True,
    )

    assert response.status_code == 415
    assert "The provided content-type is not supported." in response.json()["reason"]


def test_thermal_compositional_negative_get_data_unsupported_accept_header(
    api, record_id, dataset_id, fluid_model_type
):
    """Reject unsupported Thermal Compositional response formats with 406."""
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={ACCEPT: "application/xml"},
        allowed_codes=[status.HTTP_406_NOT_ACCEPTABLE],
        raw=True,
    )

    assert response.status_code == 406
