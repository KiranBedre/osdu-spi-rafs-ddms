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
    SamplesAnalysisEndpoints,
)


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.ALL_ENDPOINTS_ARGS)
def test_saturation_test_negative_missing_authorization_header(
    api, tests_data, endpoint, args, record_id, version, dataset_id_v1, analysis_type
):
    """Reject requests missing Authorization header with 403 Forbidden (401 for get_schema)."""
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    local_vars["dataset_id"] = local_vars["dataset_id_v1"]
    call_args = [local_vars[name] for name in args]

    # get_schema has no record/entitlements dependency ahead of auth, so FastAPI's
    # own HTTPBearer rejects a missing header with 401 before RAFS's 403 logic runs.
    expected_code = status.HTTP_401_UNAUTHORIZED if endpoint == "get_schema" else status.HTTP_403_FORBIDDEN
    kwargs = {
        "headers": {AUTHORIZATION: None},
        "allowed_codes": [expected_code],
        "raw": True,
    }

    if endpoint == "post_record":
        kwargs["body"] = [copy.deepcopy(tests_data(DataFiles.SAMPLE_ANALYSIS))]
    elif endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_TEST_DATA_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        # post_data(record_id, body, analysis_type) — body is positional index 1
        call_args = [local_vars["record_id"], data_payload, local_vars["analysis_type"]]

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == expected_code
    body = response.json()
    assert "Not authenticated" in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.ALL_ENDPOINTS_ARGS)
def test_saturation_test_negative_invalid_authorization_header(
    api, tests_data, endpoint, args, record_id, version, dataset_id_v1, analysis_type
):
    """Reject malformed Authorization header with 403 Forbidden (401 for get_schema)."""
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    local_vars["dataset_id"] = local_vars["dataset_id_v1"]
    call_args = [local_vars[name] for name in args]

    # get_schema has no record/entitlements dependency ahead of auth, so FastAPI's
    # own HTTPBearer rejects a malformed header with 401 before RAFS's 403 logic runs.
    expected_code = status.HTTP_401_UNAUTHORIZED if endpoint == "get_schema" else status.HTTP_403_FORBIDDEN
    kwargs = {
        "headers": {AUTHORIZATION: "dummy"},
        "allowed_codes": [expected_code],
        "raw": True,
    }

    if endpoint == "post_record":
        kwargs["body"] = [copy.deepcopy(tests_data(DataFiles.SAMPLE_ANALYSIS))]
    elif endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_TEST_DATA_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        # post_data(record_id, body, analysis_type) — body is positional index 1
        call_args = [local_vars["record_id"], data_payload, local_vars["analysis_type"]]

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == expected_code
    body = response.json()
    assert "Not authenticated" in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.ALL_ENDPOINTS_ARGS)
def test_saturation_test_negative_invalid_access_token_authorization_header(
    api, tests_data, endpoint, args, record_id, version, dataset_id_v1, analysis_type
):
    """Reject invalid Bearer token with 401 Unauthorized."""
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    local_vars["dataset_id"] = local_vars["dataset_id_v1"]
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "headers": {AUTHORIZATION: "Bearer dummy"},
        "allowed_codes": [status.HTTP_401_UNAUTHORIZED],
        "raw": True,
    }

    if endpoint == "post_record":
        kwargs["body"] = [copy.deepcopy(tests_data(DataFiles.SAMPLE_ANALYSIS))]
    elif endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_TEST_DATA_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        # post_data(record_id, body, analysis_type) — body is positional index 1
        call_args = [local_vars["record_id"], data_payload, local_vars["analysis_type"]]

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 401
    body = response.json()
    assert "Access denied" in body["reason"]
    assert "The user is not authorized to perform this action" in body["message"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.ALL_ENDPOINTS_ARGS)
def test_saturation_test_negative_missing_data_partition_id_header(
    api, tests_data, endpoint, args, record_id, version, dataset_id_v1, analysis_type
):
    """Reject requests missing Data-Partition-ID header with 400 Bad Request.

    The error response must contain a human-readable string list in 'errors',
    not raw pydantic validation dicts. This is a regression guard for the
    pydantic v2 migration: if format_errors() stops normalising RequestValidationError
    dicts the 'errors' list would contain dicts instead of strings.
    """
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    local_vars["dataset_id"] = local_vars["dataset_id_v1"]
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "headers": {DATA_PARTITION_ID: None},
        "allowed_codes": [status.HTTP_400_BAD_REQUEST],
        "raw": True,
    }

    if endpoint == "post_record":
        kwargs["body"] = [copy.deepcopy(tests_data(DataFiles.SAMPLE_ANALYSIS))]
    elif endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_TEST_DATA_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        # post_data(record_id, body, analysis_type) — body is positional index 1
        call_args = [local_vars["record_id"], data_payload, local_vars["analysis_type"]]

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert body.get("reason") == "Bad request."
    errors = body.get("errors")
    assert isinstance(errors, list), f"'errors' must be a list, got {type(errors)}"
    assert len(errors) == 1, f"Expected 1 error, got {len(errors)}"
    assert all(
        isinstance(e, str) for e in errors
    ), f"Each error must be a human-readable string, not a dict. Got: {errors}"
    assert "No data-partition-id in headers" in errors


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.CONTENT_TYPE_ENDPOINTS_ARGS)
def test_saturation_test_negative_missing_content_type_header(
    api, tests_data, endpoint, args, record_id, dataset_id_v1, analysis_type
):
    """Reject requests missing Content-Type header with 400 Bad Request."""
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    local_vars["dataset_id"] = local_vars["dataset_id_v1"]
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "headers": {CONTENT_TYPE: None},
        "allowed_codes": [status.HTTP_400_BAD_REQUEST],
        "raw": True,
    }

    if endpoint == "post_record":
        kwargs["body"] = [copy.deepcopy(tests_data(DataFiles.SAMPLE_ANALYSIS))]
    elif endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_TEST_DATA_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        # post_data(record_id, body, analysis_type) — body is positional index 1
        call_args = [local_vars["record_id"], data_payload, local_vars["analysis_type"]]

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert "Content-Type header is required, but was not provided" in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.CONTENT_TYPE_ENDPOINTS_ARGS)
def test_saturation_test_negative_unsupported_content_type_header(
    api, tests_data, endpoint, args, record_id, dataset_id_v1, analysis_type
):
    """Reject unsupported content types with 415 Unsupported Media Type."""
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    local_vars["dataset_id"] = local_vars["dataset_id_v1"]
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "headers": {CONTENT_TYPE: "application/xml"},
        "allowed_codes": [status.HTTP_415_UNSUPPORTED_MEDIA_TYPE],
        "raw": True,
    }

    if endpoint == "post_record":
        kwargs["body"] = [copy.deepcopy(tests_data(DataFiles.SAMPLE_ANALYSIS))]
    elif endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_TEST_DATA_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        # post_data(record_id, body, analysis_type) — body is positional index 1
        call_args = [local_vars["record_id"], data_payload, local_vars["analysis_type"]]

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 415
    body = response.json()
    assert (
        "The provided content-type is not supported. Please provide one of the next supported content types: "
        "['application/json'"
    ) in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.ACCEPT_ENDPOINTS_ARGS)
def test_saturation_test_negative_unsupported_application_accept_header(
    api, tests_data, endpoint, args, record_id, dataset_id_v1, analysis_type
):
    """Reject unsupported media types in Accept header with 406 Not Acceptable."""
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    local_vars["dataset_id"] = local_vars["dataset_id_v1"]
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
