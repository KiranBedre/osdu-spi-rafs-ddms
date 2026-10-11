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

import pytest
from starlette import status

from tests.integration.config import CONFIG

DATA_PARTITION_ID = CONFIG["DATA_PARTITION"]

RECORD_ID_ENDPOINTS_ARGS = [
    ("get_record", ("record_id",)),
    ("get_record_versions", ("record_id",)),
    ("get_record_version", ("record_id", "version")),
    ("soft_delete_record", ("record_id",)),
]


@pytest.mark.parametrize("endpoint,args", RECORD_ID_ENDPOINTS_ARGS)
def test_fluid_negative_invalid_regex_record_id_in_url(api, tests_data, endpoint, args, version):
    """Reject record IDs not matching OSDU pattern with 422 Unprocessable Content."""
    method = getattr(api.fluid_model, endpoint)
    record_id = "invalid_id"
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert (
        "work-product-component--FluidModel ID is not provided in expected OSDU pattern "
        '"^[\\w\\-\\.]+:work-product-component--FluidModel:[\\w\\-\\.\\:\\%]+$"'
    ) in body["errors"]


@pytest.mark.parametrize("endpoint,args", RECORD_ID_ENDPOINTS_ARGS)
def test_fluid_negative_invalid_data_partition_id_record_id_in_url(api, tests_data, endpoint, args, version):
    """Reject record ID with wrong partition prefix with 400 Bad Request."""
    method = getattr(api.fluid_model, endpoint)
    record_id = "WrongID:work-product-component--FluidModel:Test123"
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "allowed_codes": [status.HTTP_400_BAD_REQUEST],
        "raw": True,
    }

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert f"Invalid record ID" in body["reason"]
    assert f"The record '{record_id}' does not belong to account '{DATA_PARTITION_ID}'" in body["message"]


@pytest.mark.parametrize("endpoint,args", RECORD_ID_ENDPOINTS_ARGS)
def test_fluid_negative_non_existing_record_id_in_url(api, tests_data, endpoint, args, version):
    """Reject non-existent record ID with 404 Not Found."""
    method = getattr(api.fluid_model, endpoint)
    record_id = f"{DATA_PARTITION_ID}:work-product-component--FluidModel:NonExistingID"
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "allowed_codes": [status.HTTP_404_NOT_FOUND],
        "raw": True,
    }

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert "Record not found" in body["reason"]
    assert (
        f"The record '{record_id}' was not found" in body["message"]
        or f"Record with id '{record_id}' does not exist" in body["message"]
    )


def test_fluid_negative_non_existing_version_in_url(api, tests_data, record_id):
    """Reject non-existent version number with 404 Not Found."""
    version = 10000001
    kwargs = {
        "allowed_codes": [status.HTTP_404_NOT_FOUND],
        "raw": True,
    }

    response = api.fluid_model.get_record_version(record_id, version, **kwargs)

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert body["reason"] == "Version not found"
    assert body["message"] == f"The version {version} can't be found for record {record_id}"


def test_fluid_negative_edge_max_version_in_url(api, tests_data, record_id):
    """Reject extreme version number - boundary testing."""
    version = 12345678901234567890
    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = api.fluid_model.get_record_version(record_id, version, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert "version Input should be less than or equal to 9223372036854775807" in body["errors"]


def test_fluid_negative_edge_min_version_in_url(api, tests_data, record_id):
    """Reject zero/negative version numbers boundary testing."""
    version = 0
    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = api.fluid_model.get_record_version(record_id, version, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert "version Input should be greater than or equal to 1" in body["errors"]
