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
from email.utils import parsedate_to_datetime

import pytest
from starlette import status

from app.resources.common_headers import ACCEPT
from tests.integration.config import DataFiles, FluidModelTypes, SchemaVersions

FLUID_MODEL_SCHEMAS = (
    (FluidModelTypes.BLACK_OIL_FLUID_MODEL, DataFiles.BLACK_OIL_FLUID_MODEL_SCHEMA_V1),
    (
        FluidModelTypes.COMPOSITIONAL_FLUID_MODEL,
        DataFiles.COMPOSITIONAL_FLUID_MODEL_SCHEMA_V1,
    ),
    (
        FluidModelTypes.THERMAL_COMPOSITIONAL_FLUID_MODEL,
        DataFiles.THERMAL_COMPOSITIONAL_FLUID_MODEL_SCHEMA_V1,
    ),
)

REPRESENTATIVE_FLUID_MODEL_TYPE = FluidModelTypes.THERMAL_COMPOSITIONAL_FLUID_MODEL
REPRESENTATIVE_SCHEMA_FILE = DataFiles.THERMAL_COMPOSITIONAL_FLUID_MODEL_SCHEMA_V1


@pytest.mark.parametrize("fluid_model_type,schema_file", FLUID_MODEL_SCHEMAS)
def test_fluid_model_get_schema_v1(
    api, helper, tests_data, fluid_model_type, schema_file
):
    """Return the registered JSON schema for each Fluid Model type."""
    response = api.fluid_model.get_schema(
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        raw=True,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("application/json")
    helper.compare_responses(
        response.json(), copy.deepcopy(tests_data(schema_file)), response_type="json"
    )


@pytest.mark.parametrize("fluid_model_type,_", FLUID_MODEL_SCHEMAS)
def test_fluid_model_get_schema_unsupported_schema_version(api, fluid_model_type, _):
    """Reject an unavailable but well-formed schema version."""
    response = api.fluid_model.get_schema(
        fluid_model_type=fluid_model_type,
        schema_version="9.9.9",
        allowed_codes=[status.HTTP_404_NOT_FOUND],
        raw=True,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.headers["content-type"].startswith("application/json")
    reason = response.json()["reason"]
    assert reason.startswith(
        f"Model not found for type '{fluid_model_type}',  version '9.9.9'. Available versions: "
    )
    assert set(
        re.findall(r"'(\d+\.\d+\.\d+)'", reason.split("Available versions:", 1)[1])
    ) == {"1.0.0"}


@pytest.mark.parametrize("malformed_schema_version", ("abc", "1.x"))
def test_fluid_model_get_schema_malformed_schema_version(api, malformed_schema_version):
    """Reject malformed content_schema_version values."""
    response = api.fluid_model.get_schema(
        fluid_model_type=REPRESENTATIVE_FLUID_MODEL_TYPE,
        schema_version=malformed_schema_version,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.headers["content-type"].startswith("application/json")
    assert (
        f"Invalid version format in content_schema_version: '{malformed_schema_version}'. "
        "Expected format: major.minor.patch (e.g. 1.0.0)"
    ) in response.json()["reason"]


def test_fluid_model_get_schema_missing_schema_version(api):
    """Reject schema retrieval without query or Accept-header versioning."""
    response = api.fluid_model.get_schema(
        fluid_model_type=REPRESENTATIVE_FLUID_MODEL_TYPE,
        schema_version=None,
        headers={ACCEPT: None},
        allowed_codes=[status.HTTP_406_NOT_ACCEPTABLE],
        raw=True,
    )

    assert response.status_code == status.HTTP_406_NOT_ACCEPTABLE
    assert response.headers["content-type"].startswith("application/json")


@pytest.mark.parametrize("fluid_model_type,schema_file", FLUID_MODEL_SCHEMAS)
def test_fluid_model_get_schema_accept_header_schema_version_v1(
    api, helper, tests_data, fluid_model_type, schema_file
):
    """Support deprecated Accept-header schema versioning with deprecation metadata."""
    response = api.fluid_model.get_schema(
        fluid_model_type=fluid_model_type,
        schema_version=None,
        headers={ACCEPT: "application/json;version=1.0.0"},
        raw=True,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers.get("Deprecation") == "true"
    parsedate_to_datetime(response.headers["Sunset"])
    deprecation_notice = response.headers["X-Deprecation-Notice"].lower()
    assert "accept header" in deprecation_notice
    assert "deprecated" in deprecation_notice
    helper.compare_responses(
        response.json(), copy.deepcopy(tests_data(schema_file)), response_type="json"
    )


def test_fluid_model_get_schema_query_schema_version_takes_priority_over_accept_header(
    api, helper, tests_data
):
    """Prefer content_schema_version over a conflicting Accept-header version."""
    response = api.fluid_model.get_schema(
        fluid_model_type=REPRESENTATIVE_FLUID_MODEL_TYPE,
        schema_version=SchemaVersions.V1_0_0,
        headers={ACCEPT: "application/json;version=9.9.9"},
        raw=True,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"].startswith("application/json")
    assert "Deprecation" not in response.headers
    helper.compare_responses(
        response.json(),
        copy.deepcopy(tests_data(REPRESENTATIVE_SCHEMA_FILE)),
        response_type="json",
    )
