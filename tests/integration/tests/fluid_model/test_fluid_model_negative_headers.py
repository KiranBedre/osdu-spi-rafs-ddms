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

from app.resources.common_headers import AUTHORIZATION, CONTENT_TYPE, DATA_PARTITION_ID
from tests.integration.config import (
    DataFiles,
)

ALL_ENDPOINTS_ARGS = [
        ("post_record", ()),
        ("get_record", ("record_id",)),
        ("get_record_versions", ("record_id",)),
        ("get_record_version", ("record_id", "version")),
        ("soft_delete_record", ("record_id",)),
    ]


@pytest.mark.parametrize("endpoint,args", ALL_ENDPOINTS_ARGS)
def test_fluid_negative_missing_authorization_header(api, tests_data, endpoint, args, record_id, version):
    """Reject requests missing Authorization header with 403 Forbidden."""
    method = getattr(api.fluid_model, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "headers": {AUTHORIZATION: None},
        "allowed_codes": [status.HTTP_403_FORBIDDEN],
        "raw": True,
    }

    if endpoint == "post_record":
        kwargs["body"] = [copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))]

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 403
    body = response.json()
    assert "Not authenticated" in body["reason"]


@pytest.mark.parametrize("endpoint,args", ALL_ENDPOINTS_ARGS)
def test_fluid_negative_invalid_authorization_header(api, tests_data, endpoint, args, record_id, version):
    """Reject malformed Authorization header with 403 Forbidden."""
    method = getattr(api.fluid_model, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "headers": {AUTHORIZATION: "dummy"},
        "allowed_codes": [status.HTTP_403_FORBIDDEN],
        "raw": True,
    }

    if endpoint == "post_record":
        kwargs["body"] = [copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))]

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 403
    body = response.json()
    assert "Not authenticated" in body["reason"]


@pytest.mark.parametrize("endpoint,args", ALL_ENDPOINTS_ARGS)
def test_fluid_negative_invalid_access_token_authorization_header(api, tests_data, endpoint, args, record_id, version):
    """Reject invalid Bearer token with 401 Unauthorized."""
    method = getattr(api.fluid_model, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "headers": {AUTHORIZATION: "Bearer dummy"},
        "allowed_codes": [status.HTTP_401_UNAUTHORIZED],
        "raw": True,
    }

    if endpoint == "post_record":
        kwargs["body"] = [copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))]

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 401
    body = response.json()
    assert "Access denied" in body["reason"]
    assert "The user is not authorized to perform this action" in body["message"]


@pytest.mark.parametrize("endpoint,args", ALL_ENDPOINTS_ARGS)
def test_fluid_negative_missing_data_partition_id_header(api, tests_data, endpoint, args, record_id, version):
    """Reject requests missing Data-Partition-ID header with 400 Bad Request."""
    method = getattr(api.fluid_model, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "headers": {DATA_PARTITION_ID: None},
        "allowed_codes": [status.HTTP_400_BAD_REQUEST],
        "raw": True,
    }

    if endpoint == "post_record":
        kwargs["body"] = [copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))]

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert len(body["errors"]) == 1, f"Expected errors list length 1, got {len(body['errors'])}"
    assert "No data-partition-id in headers" in body["errors"]


def test_fluid_negative_missing_content_type_header(api, tests_data, record_id):
    """Skip: Reject requests missing Content-Type header with 400 Bad Request."""
    kwargs = {
        "headers": {CONTENT_TYPE: None},
        "allowed_codes": [status.HTTP_400_BAD_REQUEST],
        "raw": True,
    }

    body = [copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))]

    response = api.fluid_model.post_record(body=body, **kwargs)

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert "Content-Type header is required, but was not provided" in body["reason"]


def test_fluid_negative_unsupported_content_type_header(api, tests_data, record_id):
    """Reject unsupported content types (only JSON accepted) with 415 Unsupported Media Type."""
    kwargs = {
        "headers": {CONTENT_TYPE: "application/xml"},
        "allowed_codes": [status.HTTP_415_UNSUPPORTED_MEDIA_TYPE],
        "raw": True,
    }

    body = [copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))]

    response = api.fluid_model.post_record(body=body, **kwargs)

    # Assert
    assert response.status_code == 415
    body = response.json()
    assert (
        "The provided content-type is not supported. Please provide one of the next supported content types: "
        "['application/json'"
    ) in body["reason"]