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
import re
from urllib.parse import urlparse

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


def test_samples_analysis_types_preserves_public_route(api, tests_data, helper):
    """Verify the configured route remains the public AnalysisTypes endpoint."""
    response = api.sample_analysis.get_analysis_types(raw=True)

    assert response.status_code == status.HTTP_200_OK
    assert urlparse(response.url).path.rstrip("/").endswith("/samplesanalysis/analysistypes")

    helper.compare_responses(
        response.json(),
        copy.deepcopy(tests_data(DataFiles.SAMPLE_ANALYSIS_TYPES)),
        response_type="json",
    )


def test_samples_analysis_types_response_contract(api):
    """Return a JSON map of analysis types to unique semantic versions."""
    response = api.sample_analysis.get_analysis_types(raw=True)

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("application/json")

    body = response.json()
    assert isinstance(body, dict)
    assert body

    for analysis_type, versions in body.items():
        assert isinstance(analysis_type, str)
        assert analysis_type
        assert isinstance(versions, list)
        assert versions
        assert len(versions) == len(set(versions)), f"Duplicate versions for {analysis_type}"
        assert all(
            isinstance(version, str) and re.fullmatch(r"\d+\.\d+\.\d+", version) for version in versions
        ), f"Invalid schema version for {analysis_type}: {versions}"


def test_samples_analysis_types_rejects_post_method(api):
    """Reject POST because the analysis types endpoint is read-only."""
    response = api.sample_analysis.post(
        path="/samplesanalysis/analysistypes",
        allowed_codes=[status.HTTP_405_METHOD_NOT_ALLOWED],
    )

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_samples_analysis_types_negative_missing_authorization_header(api):
    """Reject requests missing Authorization header with 403 Forbidden."""

    kwargs = {
        "headers": {AUTHORIZATION: None},
        "allowed_codes": [status.HTTP_403_FORBIDDEN],
        "raw": True,
    }

    response = api.sample_analysis.get_analysis_types(**kwargs)

    # Assert
    assert response.status_code == 403
    body = response.json()
    assert "Not authenticated" in body["reason"]


def test_samples_analysis_types_negative_invalid_authorization_header(api):
    """Reject malformed Authorization header with 403 Forbidden."""

    kwargs = {
        "headers": {AUTHORIZATION: "dummy"},
        "allowed_codes": [status.HTTP_403_FORBIDDEN],
        "raw": True,
    }

    response = api.sample_analysis.get_analysis_types(**kwargs)

    # Assert
    assert response.status_code == 403
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


def test_samples_analysis_types_negative_empty_data_partition_id_header(api):
    """Reject requests with an empty Data-Partition-ID header with 403 Request."""
    response = api.sample_analysis.get_analysis_types(
        headers={DATA_PARTITION_ID: ""},
        allowed_codes=[status.HTTP_403_FORBIDDEN],
        raw=True,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    body = response.json()
    assert "Invalid data partition id" in body["message"]


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
