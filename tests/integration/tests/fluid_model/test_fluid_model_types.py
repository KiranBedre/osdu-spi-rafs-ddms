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

from app.resources.common_headers import AUTHORIZATION
from tests.integration.config import DataFiles


def test_get_fluid_model_types(api, tests_data, helper):
    """Verify retrieve Fluid Model types unchanged via GET."""

    # Retrieve Fluid Model types
    gotten_response = api.fluid_model.get_fluid_model_types()

    # Prepare baseline
    baseline = copy.deepcopy(tests_data(DataFiles.FLUID_MODEL_TYPES))

    # Response should contain the same business fields as the original POST body
    helper.compare_responses(gotten_response, baseline, response_type="json")


def test_fluid_model_types_preserves_public_route(api, tests_data, helper):
    """Verify the configured route remains the public FluidModelTypes endpoint."""
    response = api.fluid_model.get_fluid_model_types(raw=True)

    assert response.status_code == status.HTTP_200_OK
    assert (
        urlparse(response.url).path.rstrip("/").endswith("/fluidmodel/fluidmodeltypes")
    )

    helper.compare_responses(
        response.json(),
        copy.deepcopy(tests_data(DataFiles.FLUID_MODEL_TYPES)),
        response_type="json",
    )


def test_fluid_model_types_response_contract(api):
    """Return a JSON map of Fluid Model types to unique semantic versions."""
    response = api.fluid_model.get_fluid_model_types(raw=True)

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("application/json")

    body = response.json()
    assert isinstance(body, dict)
    assert set(body) == {
        "blackoilfluidmodel",
        "compositionalfluidmodel",
        "thermalcompositionalfluidmodel",
    }

    for fluid_model_type, versions in body.items():
        assert isinstance(fluid_model_type, str)
        assert fluid_model_type
        assert isinstance(versions, list)
        assert versions == ["1.0.0"]
        assert len(versions) == len(
            set(versions)
        ), f"Duplicate versions for {fluid_model_type}"
        assert all(
            isinstance(version, str) and re.fullmatch(r"\d+\.\d+\.\d+", version)
            for version in versions
        ), f"Invalid schema version for {fluid_model_type}: {versions}"


def test_fluid_model_types_negative_missing_authorization_header(api):
    """Reject requests missing Authorization header with 401 Unauthorized."""

    kwargs = {
        "headers": {AUTHORIZATION: None},
        "allowed_codes": [status.HTTP_401_UNAUTHORIZED],
        "raw": True,
    }

    response = api.fluid_model.get_fluid_model_types(**kwargs)

    # Assert
    assert response.status_code == 401
    body = response.json()
    assert "Not authenticated" in body["reason"]


def test_fluid_model_types_negative_invalid_authorization_header(api):
    """Reject malformed Authorization header with 401 Unauthorized."""

    kwargs = {
        "headers": {AUTHORIZATION: "dummy"},
        "allowed_codes": [status.HTTP_401_UNAUTHORIZED],
        "raw": True,
    }

    response = api.fluid_model.get_fluid_model_types(**kwargs)

    # Assert
    assert response.status_code == 401
    body = response.json()
    assert "Not authenticated" in body["reason"]
