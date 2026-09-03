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

from app.resources.common_headers import AUTHORIZATION, DATA_PARTITION_ID
from tests.integration.config import (
    DataFiles,
)


def test_get_samples_analysis_types(api, tests_data, helper):
    """Verify retrieve samples analysis types unchanged via GET."""

    # Retrieve sample analysis types
    gotten_response = api.sample_analysis.get_analysis_types()

    # Prepare baseline
    baseline = copy.deepcopy(tests_data(DataFiles.SAMPLE_ANALYSIS_TYPES))

    # Response should contain the same business fields as the original POST body
    helper.compare_responses(gotten_response, baseline, response_type="json")


def test_samples_analysis_types_negative_missing_authorization_header(api):
    """Reject requests missing Authorization header with 401 or 403.

    Accepts either code: which one a given deployment returns depends on
    which layer enforces authentication there (app vs. gateway), and that
    has not been isolated per environment. The observed 401 body
    ({"code": 401, "reason": "Not authenticated"}) matches FastAPI's own
    app-level behavior for a missing bearer token.
    """

    kwargs = {
        "headers": {AUTHORIZATION: None},
        "allowed_codes": [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED],
        "raw": True,
    }

    response = api.sample_analysis.get_analysis_types(**kwargs)

    # Assert
    assert response.status_code in (403, 401)
    body = response.json()
    assert "Not authenticated" in body["reason"]


def test_samples_analysis_types_negative_invalid_authorization_header(api):
    """Reject malformed Authorization header with 401 or 403.

    Accepts either code: which one a given deployment returns depends on
    which layer enforces authentication there (app vs. gateway), and that
    has not been isolated per environment. The observed 401 body
    ({"code": 401, "reason": "Not authenticated"}) matches FastAPI's own
    app-level behavior for a malformed bearer token.
    """

    kwargs = {
        "headers": {AUTHORIZATION: "dummy"},
        "allowed_codes": [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED],
        "raw": True,
    }

    response = api.sample_analysis.get_analysis_types(**kwargs)

    # Assert
    assert response.status_code in (403, 401)
    body = response.json()
    assert "Not authenticated" in body["reason"]


def test_samples_analysis_types_negative_invalid_access_token_authorization_header(api):
    """Reject invalid Bearer token with 401 Unauthorized."""

    kwargs = {
        "headers": {AUTHORIZATION: "Bearer dummy"},
        "allowed_codes": [status.HTTP_401_UNAUTHORIZED],
        "raw": True,
    }

    response = api.sample_analysis.get_analysis_types(**kwargs)

    # Assert
    assert response.status_code == 401
    body = response.json()
    assert "Access denied" in body["reason"]
    assert "The user is not authorized to perform this action" in body["message"]


def test_samples_analysis_types_negative_missing_data_partition_id_header(api):
    """Reject requests missing Data-Partition-ID header with 400 Bad Request."""

    kwargs = {
        "headers": {DATA_PARTITION_ID: None},
        "allowed_codes": [status.HTTP_400_BAD_REQUEST],
        "raw": True,
    }

    response = api.sample_analysis.get_analysis_types(**kwargs)

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert len(body["errors"]) == 1, f"Expected errors list length 1, got {len(body['errors'])}"
    assert "No data-partition-id in headers" in body["errors"]


def test_samples_analysis_types_negative_invalid_data_partition_id_header(api):
    """Reject requests invalid Data-Partition-ID header with 401 Unauthorized."""

    kwargs = {
        "headers": {DATA_PARTITION_ID: "Dummy"},
        "allowed_codes": [status.HTTP_401_UNAUTHORIZED],
        "raw": True,
    }

    response = api.sample_analysis.get_analysis_types(**kwargs)

    # Assert
    assert response.status_code == 401
    body = response.json()
    assert "Access denied" in body["reason"]
    assert "The user is not authorized to perform this action" in body["message"]
