#  Copyright 2023 ExxonMobil Technology and Engineering Company
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


import re

import pytest
from httpx import AsyncClient
from starlette import status

from app.main import app
from app.models.data_schemas.base import (
    ALL_PATHS_TO_SA_DATA_MODEL,
    MAPS_TO_DATA_MODEL,
)
from app.resources.paths import (
    FLUID_MODEL_STR,
    SATURATION_FUNCTION_SET_STR,
)
from tests.test_api.test_routes.data.data_mock_objects import (
    TEST_SCHEMA_VERSION,
)
from tests.test_api.test_routes.data.data_v2_test import services_overrides
from tests.test_api.test_routes.osdu.storage_mock_objects import (
    FLUID_MODEL_ENDPOINT_PATH_V2,
    PREFIX_TO_STRIP,
    SAMPLESANALYSIS_ENDPOINT_PATH_V2,
    SATURATION_FUNCTION_SET_ENDPOINT_PATH_V2,
    TEST_HEADERS,
    TEST_SERVER,
    VALID_ANALYSIS_TYPES_V1_0_0,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("analysistype", VALID_ANALYSIS_TYPES_V1_0_0)
async def test_samplesanalysis_content_schema_success(analysistype):
    """Tests successful retrieval of the schema for each valid analysis_type with version 1.0.0"""
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        with services_overrides():
            response = await client.get(
                f"{SAMPLESANALYSIS_ENDPOINT_PATH_V2}/{analysistype}/data/schema",
                headers={
                    **TEST_HEADERS,
                    "Accept": "application/json;version=1.0.0",
                },
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/json"
    assert response.headers.get("Deprecation") == "true"

    model_key = f"{PREFIX_TO_STRIP}{analysistype}"

    expected_schema = ALL_PATHS_TO_SA_DATA_MODEL[model_key]["1.0.0"].model_json_schema()
    assert response.json() == expected_schema


@pytest.mark.asyncio
@pytest.mark.parametrize("analysistype", VALID_ANALYSIS_TYPES_V1_0_0)
async def test_samplesanalysis_content_schema_wrong_version(analysistype):
    """Tests 404 error when requesting a non-existent version for a valid analysis_type"""
    invalid_version = "0.0.0"
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        with services_overrides():
            response = await client.get(
                f"{SAMPLESANALYSIS_ENDPOINT_PATH_V2}/{analysistype}/data/schema",
                headers={**TEST_HEADERS, "Accept": f"application/json;version={invalid_version}"},
            )

    assert response.status_code == status.HTTP_404_NOT_FOUND

    model_key = f"{PREFIX_TO_STRIP}{analysistype}"
    available_versions = set(ALL_PATHS_TO_SA_DATA_MODEL[model_key].keys())

    assert response.json()["reason"] == (
        f"Model not found for type '{analysistype}',  "
        f"version '{invalid_version}'. "
        f"Available versions: {available_versions}."
    )


@pytest.mark.asyncio
async def test_samplesanalysis_content_schema_wrong_type():
    """Tests 404 error when requesting a non-existent analysistype"""
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        with services_overrides():
            response = await client.get(
                f"{SAMPLESANALYSIS_ENDPOINT_PATH_V2}/wrong-type-name/data/schema",
                headers={**TEST_HEADERS, "Accept": "application/json;version=1.0.0"},
            )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["reason"] == "Model not found for type 'wrong-type-name',  version '1.0.0'."


VALID_ANALYSIS_TYPES_V2_0_0 = [
    path.replace(PREFIX_TO_STRIP, "")
    for path, versions in ALL_PATHS_TO_SA_DATA_MODEL.items()
    if path.startswith(PREFIX_TO_STRIP) and "2.0.0" in versions
]


@pytest.mark.asyncio
@pytest.mark.parametrize("analysistype", VALID_ANALYSIS_TYPES_V2_0_0)
async def test_samplesanalysis_content_schema_v2_success(analysistype):
    """Tests successful retrieval of the schema for each valid analysis_type with version 2.0.0"""
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        with services_overrides():
            response = await client.get(
                f"{SAMPLESANALYSIS_ENDPOINT_PATH_V2}/{analysistype}/data/schema",
                headers={**TEST_HEADERS, "Accept": "application/json;version=2.0.0"},
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/json"

    model_key = f"{PREFIX_TO_STRIP}{analysistype}"

    expected_schema = ALL_PATHS_TO_SA_DATA_MODEL[model_key]["2.0.0"].model_json_schema()
    assert response.json() == expected_schema


@pytest.mark.asyncio
@pytest.mark.parametrize("analysistype", VALID_ANALYSIS_TYPES_V1_0_0[:1])
async def test_samplesanalysis_content_schema_via_content_schema_version_param(analysistype):
    """Tests schema retrieval using ?content_schema_version= query parameter"""
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        with services_overrides():
            response = await client.get(
                f"{SAMPLESANALYSIS_ENDPOINT_PATH_V2}/{analysistype}/data/schema?content_schema_version=1.0.0",
                headers={**TEST_HEADERS},
            )

    assert response.status_code == status.HTTP_200_OK
    assert "Deprecation" not in response.headers

    model_key = f"{PREFIX_TO_STRIP}{analysistype}"

    expected_schema = ALL_PATHS_TO_SA_DATA_MODEL[model_key]["1.0.0"].model_json_schema()
    assert response.json() == expected_schema


@pytest.mark.asyncio
@pytest.mark.parametrize("analysistype", VALID_ANALYSIS_TYPES_V2_0_0)
async def test_samplesanalysis_content_schema_v2_via_content_schema_version_param(analysistype):
    """Tests v2.0.0 schema retrieval using ?content_schema_version= query parameter"""
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        with services_overrides():
            response = await client.get(
                f"{SAMPLESANALYSIS_ENDPOINT_PATH_V2}/{analysistype}/data/schema?content_schema_version=2.0.0",
                headers={**TEST_HEADERS},
            )

    assert response.status_code == status.HTTP_200_OK
    assert "Deprecation" not in response.headers

    model_key = f"{PREFIX_TO_STRIP}{analysistype}"

    expected_schema = ALL_PATHS_TO_SA_DATA_MODEL[model_key]["2.0.0"].model_json_schema()
    assert response.json() == expected_schema


@pytest.mark.asyncio
@pytest.mark.parametrize("analysistype", VALID_ANALYSIS_TYPES_V1_0_0[:1])
async def test_content_schema_version_param_takes_precedence_over_accept_header(analysistype):
    """Tests that ?content_schema_version= takes precedence over the deprecated Accept header"""
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        with services_overrides():
            response = await client.get(
                f"{SAMPLESANALYSIS_ENDPOINT_PATH_V2}/{analysistype}/data/schema?content_schema_version=1.0.0",
                headers={**TEST_HEADERS, "Accept": "application/json;version=0.0.0"},
            )

    assert response.status_code == status.HTTP_200_OK
    assert "Deprecation" not in response.headers

    model_key = f"{PREFIX_TO_STRIP}{analysistype}"

    expected_schema = ALL_PATHS_TO_SA_DATA_MODEL[model_key]["1.0.0"].model_json_schema()
    assert response.json() == expected_schema


SINGLE_CONTENT_TYPE_SCHEMA_ENDPOINTS = [
    (
        SATURATION_FUNCTION_SET_ENDPOINT_PATH_V2,
        SATURATION_FUNCTION_SET_STR,
        SATURATION_FUNCTION_SET_STR,
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint_path, model_key, _",
    SINGLE_CONTENT_TYPE_SCHEMA_ENDPOINTS,
)
async def test_single_content_type_schema_success(endpoint_path, model_key, _):
    """
    Test for successful retrieval of the schema for single content type endpoints.
    """
    versions_dict = MAPS_TO_DATA_MODEL["v2"][model_key][model_key]
    expected_schema = versions_dict[TEST_SCHEMA_VERSION].model_json_schema()

    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        with services_overrides():
            response = await client.get(
                f"{endpoint_path}/data/schema",
                headers={**TEST_HEADERS, "Accept": f"application/json;version={TEST_SCHEMA_VERSION}"},
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == expected_schema


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint_path, _, expected_content_type_in_error",
    SINGLE_CONTENT_TYPE_SCHEMA_ENDPOINTS,
)
async def test_single_content_type_schema_wrong_version(endpoint_path, _, expected_content_type_in_error):
    """
    Test for 404 error for single content type endpoints with an incorrect version.
    """
    invalid_version = "0.0.0"

    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        with services_overrides():
            response = await client.get(
                f"{endpoint_path}/data/schema",
                headers={**TEST_HEADERS, "Accept": f"application/json;version={invalid_version}"},
            )
    print(f"DEBUG RESPONSE: {response.json()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert (
        response.json()["reason"]
        == f"Model not found for type '{expected_content_type_in_error}',  version '{invalid_version}'. Available versions: {{'1.0.0'}}."
    )


TEST_MULTIPLE_CONTENT_TYPE_SCHEMA_FLUID_MODEL = [
    (
        model_key,
        endpoint_path_v2,
        relative_path,
    )
    for model_key, endpoint_path_v2, relative_paths in [
        (FLUID_MODEL_STR, FLUID_MODEL_ENDPOINT_PATH_V2, MAPS_TO_DATA_MODEL["v2"][FLUID_MODEL_STR].keys()),
    ]
    for relative_path in relative_paths
]


TEST_MULTIPLE_CONTENT_TYPE_SCHEMA_FLUID_MODEL_WITH_VERSIONS = [
    (model_key, endpoint_path_v2, relative_path, content_schema_version)
    for model_key, endpoint_path_v2, relative_paths_and_content_schema_versions in [
        (FLUID_MODEL_STR, FLUID_MODEL_ENDPOINT_PATH_V2, MAPS_TO_DATA_MODEL["v2"][FLUID_MODEL_STR].items()),
    ]
    for relative_path, content_schema_versions in relative_paths_and_content_schema_versions
    for content_schema_version in content_schema_versions.keys()
]


@pytest.mark.parametrize(
    "model_key, endpoint_path_v2, relative_path, content_schema_version",
    TEST_MULTIPLE_CONTENT_TYPE_SCHEMA_FLUID_MODEL_WITH_VERSIONS,
)
@pytest.mark.asyncio
async def test_multiple_content_type_schema_success(model_key, endpoint_path_v2, relative_path, content_schema_version):
    """
    Test successful schema retrieval for multiple content type endpoints
    """
    content_type = relative_path.replace(PREFIX_TO_STRIP, "")
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        with services_overrides():
            response = await client.get(
                f"{endpoint_path_v2}/{content_type}/data/schema",
                headers={**TEST_HEADERS, "Accept": f"application/json;version={content_schema_version}"},
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/json"
    assert response.headers.get("Deprecation") == "true"

    expected_schema = MAPS_TO_DATA_MODEL["v2"][model_key][relative_path][content_schema_version].schema()
    assert response.json() == expected_schema


@pytest.mark.parametrize(
    "model_key, endpoint_path_v2, relative_path",
    TEST_MULTIPLE_CONTENT_TYPE_SCHEMA_FLUID_MODEL,
)
@pytest.mark.asyncio
async def test_multiple_content_type_schema_invalid_version(model_key, endpoint_path_v2, relative_path):
    """
    Test 404 error for multiple content type endpoints
    when requesting a schema with wrong version
    """
    invalid_version = "0.0.0"
    content_type = relative_path.replace(PREFIX_TO_STRIP, "")
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        with services_overrides():
            response = await client.get(
                f"{endpoint_path_v2}/{content_type}/data/schema",
                headers={**TEST_HEADERS, "Accept": f"application/json;version={invalid_version}"},
            )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.headers["content-type"] == "application/json"

    reason = response.json()["reason"]
    reason_available_versions = set(re.findall(r"Available versions:.*?'(\d+\.\d+\.\d+)'", reason))
    actual_available_versions = set(MAPS_TO_DATA_MODEL["v2"][model_key][relative_path].keys())

    assert reason.startswith(
        f"Model not found for type '{content_type}',  " f"version '{invalid_version}'. Available versions: "
    )
    assert reason_available_versions == actual_available_versions


@pytest.mark.parametrize(
    "endpoint_path_v2",
    [FLUID_MODEL_ENDPOINT_PATH_V2],
)
@pytest.mark.asyncio
async def test_multiple_content_type_schema_non_existent_type(endpoint_path_v2):
    """
    Test 404 error for multiple content type endpoints
    when requesting a non-existent content type
    """
    non_existent_type = "nonexistenttype"
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        with services_overrides():
            response = await client.get(
                f"{endpoint_path_v2}/{non_existent_type}/data/schema",
                headers={**TEST_HEADERS, "Accept": "application/json;version=1.0.0"},
            )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.headers["content-type"] == "application/json"
    assert response.json()["reason"] == f"Model not found for type '{non_existent_type}',  version '1.0.0'."


@pytest.mark.parametrize(
    "model_key, endpoint_path_v2, relative_path, content_schema_version",
    TEST_MULTIPLE_CONTENT_TYPE_SCHEMA_FLUID_MODEL_WITH_VERSIONS,
)
@pytest.mark.asyncio
async def test_multiple_content_type_schema_success_via_version_param(
    model_key, endpoint_path_v2, relative_path, content_schema_version
):
    """
    Test successful schema retrieval for multiple content type endpoints
    when using ?content_schema_version= query parameter
    """
    content_type = relative_path.replace(PREFIX_TO_STRIP, "")
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        with services_overrides():
            response = await client.get(
                f"{endpoint_path_v2}/{content_type}/data/schema?content_schema_version={content_schema_version}",
                headers={**TEST_HEADERS},
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/json"
    assert "Deprecation" not in response.headers

    expected_schema = MAPS_TO_DATA_MODEL["v2"][model_key][relative_path][content_schema_version].schema()
    assert response.json() == expected_schema


@pytest.mark.parametrize(
    "endpoint_path_v2, relative_path",
    [(params[1], params[2]) for params in TEST_MULTIPLE_CONTENT_TYPE_SCHEMA_FLUID_MODEL],
)
@pytest.mark.asyncio
async def test_multiple_content_type_schema_no_version(endpoint_path_v2, relative_path):
    """
    Test 406 error for multiple content type endpoints
    when requesting schema without a version
    """
    content_type = relative_path.replace(PREFIX_TO_STRIP, "")
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        with services_overrides():
            response = await client.get(
                f"{endpoint_path_v2}/{content_type}/data/schema",
                headers={**TEST_HEADERS, "Accept": f"application/json"},
            )

    assert response.status_code == status.HTTP_406_NOT_ACCEPTABLE
    assert response.headers["content-type"] == "application/json"
    assert response.json()["reason"] == (
        "No schema version specified or invalid schema format."
        " Use the content_schema_version query parameter (e.g. ?content_schema_version=1.0.0)."
        " The deprecated Accept header versioning is also still accepted"
        " (e.g. Accept: */*;version=1.0.0)."
    )


@pytest.mark.parametrize(
    "endpoint_path_v2, relative_path",
    [(params[1], params[2]) for params in TEST_MULTIPLE_CONTENT_TYPE_SCHEMA_FLUID_MODEL],
)
@pytest.mark.asyncio
async def test_multiple_content_type_schema_malformed_version(endpoint_path_v2, relative_path):
    """
    Test 422 error for multiple content type endpoints
    when requesting schema with a malformed version
    """
    malformed_version = "1.x"
    content_type = relative_path.replace(PREFIX_TO_STRIP, "")
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        with services_overrides():
            response = await client.get(
                f"{endpoint_path_v2}/{content_type}/data/schema?content_schema_version={malformed_version}",
                headers={**TEST_HEADERS, "Accept": f"application/json"},
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.headers["content-type"] == "application/json"
    assert response.json()["reason"] == (
        f"Invalid version format in content_schema_version: '{malformed_version}'."
        " Expected format: major.minor.patch (e.g. 1.0.0)"
    )


@pytest.mark.parametrize(
    "model_key, endpoint_path_v2, relative_path, content_schema_version",
    TEST_MULTIPLE_CONTENT_TYPE_SCHEMA_FLUID_MODEL_WITH_VERSIONS,
)
@pytest.mark.asyncio
async def test_multiple_content_type_schema_version_param_takes_precedence_over_accept_header(
    model_key, endpoint_path_v2, relative_path, content_schema_version
):
    """
    Test for multiple content type endpoints that ?content_schema_version=
    takes precedence over the deprecated Accept header
    """
    invalid_version = "0.0.0"
    content_type = relative_path.replace(PREFIX_TO_STRIP, "")
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        with services_overrides():
            response = await client.get(
                f"{endpoint_path_v2}/{content_type}/data/schema?content_schema_version={content_schema_version}",
                headers={**TEST_HEADERS, "Accept": f"application/json;version={invalid_version}"},
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/json"
    assert "Deprecation" not in response.headers

    expected_schema = MAPS_TO_DATA_MODEL["v2"][model_key][relative_path][content_schema_version].schema()
    assert response.json() == expected_schema
