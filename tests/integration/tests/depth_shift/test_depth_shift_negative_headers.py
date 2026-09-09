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

from app.resources.common_headers import ACCEPT, AUTHORIZATION, CONTENT_TYPE, DATA_PARTITION_ID
from tests.integration.config import (
    DataFiles,
    Endpoints,
)


@pytest.mark.parametrize("endpoint,args", Endpoints.ALL_ENDPOINTS_ARGS)
def test_depth_shift_negative_missing_authorization_header(
    api, tests_data, endpoint, args, record_id, version, dataset_id
):
    """Reject requests missing Authorization header with 401 Unauthorized."""
    method = getattr(api.depth_shift, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "headers": {AUTHORIZATION: None},
        "allowed_codes": [status.HTTP_401_UNAUTHORIZED],
        "raw": True,
    }

    if endpoint == "post_record":
        kwargs["body"] = [copy.deepcopy(tests_data(DataFiles.DEPTH_SHIFT))]
    elif endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA))
        data_payload["data"][0][0] = f"{record_id}:"
        kwargs["body"] = data_payload

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 401
    body = response.json()
    assert "Not authenticated" in body["reason"]


@pytest.mark.parametrize("endpoint,args", Endpoints.ALL_ENDPOINTS_ARGS)
def test_depth_shift_negative_invalid_authorization_header(
    api, tests_data, endpoint, args, record_id, version, dataset_id
):
    """Reject malformed Authorization header with 401 Unauthorized."""
    method = getattr(api.depth_shift, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "headers": {AUTHORIZATION: "dummy"},
        "allowed_codes": [status.HTTP_401_UNAUTHORIZED],
        "raw": True,
    }

    if endpoint == "post_record":
        kwargs["body"] = [copy.deepcopy(tests_data(DataFiles.DEPTH_SHIFT))]
    elif endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA))
        data_payload["data"][0][0] = f"{record_id}:"
        kwargs["body"] = data_payload

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 401
    body = response.json()
    assert "Not authenticated" in body["reason"]


@pytest.mark.parametrize("endpoint,args", Endpoints.ALL_ENDPOINTS_ARGS)
def test_depth_shift_negative_invalid_access_token_authorization_header(
    api, tests_data, endpoint, args, record_id, version, dataset_id
):
    """Reject invalid Bearer token with 401 Unauthorized."""
    method = getattr(api.depth_shift, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "headers": {AUTHORIZATION: "Bearer dummy"},
        "allowed_codes": [status.HTTP_401_UNAUTHORIZED],
        "raw": True,
    }

    if endpoint == "post_record":
        kwargs["body"] = [copy.deepcopy(tests_data(DataFiles.DEPTH_SHIFT))]
    elif endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA))
        data_payload["data"][0][0] = f"{record_id}:"
        kwargs["body"] = data_payload

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 401
    body = response.json()
    assert "Access denied" in body["reason"]
    assert "The user is not authorized to perform this action" in body["message"]


@pytest.mark.parametrize("endpoint,args", Endpoints.ALL_ENDPOINTS_ARGS)
def test_depth_shift_negative_missing_data_partition_id_header(
    api, tests_data, endpoint, args, record_id, version, dataset_id
):
    """Reject requests missing Data-Partition-ID header with 400 Bad Request."""
    method = getattr(api.depth_shift, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "headers": {DATA_PARTITION_ID: None},
        "allowed_codes": [status.HTTP_400_BAD_REQUEST],
        "raw": True,
    }

    if endpoint == "post_record":
        kwargs["body"] = [copy.deepcopy(tests_data(DataFiles.DEPTH_SHIFT))]
    elif endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA))
        data_payload["data"][0][0] = f"{record_id}:"
        kwargs["body"] = data_payload

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert len(body["errors"]) == 1, f"Expected errors list length 1, got {len(body['errors'])}"
    assert "No data-partition-id in headers" in body["errors"]


@pytest.mark.parametrize("endpoint,args", Endpoints.CONTENT_TYPE_ENDPOINTS_ARGS)
def test_depth_shift_negative_missing_content_type_header(api, tests_data, endpoint, args, record_id, dataset_id):
    """Reject requests missing Content-Type header with 400 Bad Request."""
    method = getattr(api.depth_shift, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "allowed_codes": [status.HTTP_400_BAD_REQUEST],
        "raw": True,
        "headers": {CONTENT_TYPE: None},
    }

    if endpoint == "post_record":
        kwargs["body"] = [copy.deepcopy(tests_data(DataFiles.DEPTH_SHIFT))]
    elif endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA))
        data_payload["data"][0][0] = f"{record_id}:"
        kwargs["body"] = data_payload

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert "Content-Type header is required, but was not provided" in body["reason"]


@pytest.mark.parametrize("endpoint,args", Endpoints.CONTENT_TYPE_ENDPOINTS_ARGS)
def test_depth_shift_negative_unsupported_content_type_header(api, tests_data, endpoint, args, record_id, dataset_id):
    """Reject unsupported content types (only JSON accepted) with 415 Unsupported Media Type."""
    method = getattr(api.depth_shift, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "headers": {CONTENT_TYPE: "application/xml"},
        "allowed_codes": [status.HTTP_415_UNSUPPORTED_MEDIA_TYPE],
        "raw": True,
    }

    if endpoint == "post_record":
        kwargs["body"] = [copy.deepcopy(tests_data(DataFiles.DEPTH_SHIFT))]
    elif endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA))
        data_payload["data"][0][0] = f"{record_id}:"
        kwargs["body"] = data_payload

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 415
    body = response.json()
    assert (
        "The provided content-type is not supported. Please provide one of the next supported content types: "
        "['application/json'"
    ) in body["reason"]


@pytest.mark.parametrize("endpoint,args", Endpoints.ACCEPT_ENDPOINTS_ARGS)
def test_depth_shift_negative_unsupported_application_accept_header(
    api, tests_data, endpoint, args, record_id, dataset_id
):
    """Reject unsupported media types in Accept header with 406 Not Acceptable."""
    method = getattr(api.depth_shift, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "allowed_codes": [status.HTTP_406_NOT_ACCEPTABLE],
        "raw": True,
        "headers": {ACCEPT: "application/xml"},
    }

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 406
    body = response.json()
    assert (
        "Not Acceptable. The requested media type 'application/xml' is not supported. "
        "Supported types are: ('application/json', 'application/x-parquet', '*/*')."
    ) in body["reason"]
