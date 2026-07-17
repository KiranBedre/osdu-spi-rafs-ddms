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

from contextlib import contextmanager
from unittest.mock import create_autospec, patch

import pytest
from httpx import AsyncClient, HTTPStatusError, Response
from starlette import status

from app.api.dependencies.services import (
    get_async_schema_service,
    get_async_storage_service,
)
from app.main import app
from app.resources.paths import RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR
from app.services.schema import SchemaService
from app.services.storage import StorageService
from tests.test_api.api_version import API_VERSION_V2
from tests.test_api.test_routes import dependencies
from tests.test_api.test_routes.osdu import storage_mock_objects
from tests.test_api.test_routes.osdu.storage_mock_objects import (
    EXPECTED_200_CREATED_RESPONSE,
    EXPECTED_200_VERSIONS_RESPONSE,
    EXPECTED_404_RESPONSE,
    EXPECTED_422_INVALID_KIND_REASON,
    EXPECTED_422_TYPER_ERROR_LIST,
    OSDU_GENERIC_RECORD,
    STORAGE_SERVICE_200_RESPONSE,
    STORAGE_SERVICE_200_VERSIONS_RESPONSE,
    TEST_HEADERS,
    TEST_HEADERS_NO_AUTH,
    TEST_SERVER,
    TEST_WRONG_ID,
)

storage_record_service_mock = create_autospec(StorageService, spec_set=True, instance=True)
schema_service_mock = create_autospec(SchemaService, spec_set=True, instance=True)


async def mock_get_async_storage_service():
    yield storage_record_service_mock


async def mock_get_async_schema_service():
    yield schema_service_mock


@contextmanager
def storage_override():
    overrides = {
        get_async_storage_service: mock_get_async_storage_service,
    }
    with dependencies.DependencyOverrider(app, overrides) as mock_dependencies:
        yield mock_dependencies


@contextmanager
def storage_schema_override():
    overrides = {
        get_async_storage_service: mock_get_async_storage_service,
        get_async_schema_service: mock_get_async_schema_service,
    }
    with dependencies.DependencyOverrider(app, overrides) as mock_dependencies:
        yield mock_dependencies


@pytest.fixture
def with_patched_storage_raises_404(storage_method):
    """Patch storage to raise 404."""
    response = Response(
        status_code=status.HTTP_404_NOT_FOUND,
        content=b"test content",
    )

    with patch.object(
        storage_record_service_mock,
        storage_method,
        side_effect=HTTPStatusError("test", response=response, request=None),
    ):
        yield


@pytest.fixture
def with_patched_storage_created_200(storage_method, osdu_record):
    """Patch storage to 200 created."""
    with patch.object(
        storage_record_service_mock,
        storage_method,
        return_value=STORAGE_SERVICE_200_RESPONSE,
    ):
        with patch.object(
            storage_record_service_mock,
            "query_records",
            return_value={
                "records": [OSDU_GENERIC_RECORD.dict()],
                "invalidRecords": [],
                "retryRecords": [],
            },
        ):
            yield


@pytest.fixture
def with_patched_storage_pvt_link_200(created_responses: list, get_response: dict):
    """Patch storage to 200 created."""
    with patch.object(
        storage_record_service_mock,
        "upsert_records",
        side_effect=created_responses,
    ):
        with patch.object(storage_record_service_mock, "get_record", return_value=get_response):
            yield


@pytest.fixture
def with_patched_storage_raises_40x(storage_method, api_status_code):
    """Patch storage to raise 40x."""
    response = Response(
        status_code=api_status_code,
        content=b"test content",
    )

    with patch.object(
        storage_record_service_mock,
        storage_method,
        side_effect=HTTPStatusError("test", response=response, request=None),
    ):
        with patch.object(
            storage_record_service_mock,
            "query_records",
            side_effect=HTTPStatusError("test", response=response, request=None),
        ):
            yield


@pytest.fixture
def with_patched_storage_get_success_200(storage_method, osdu_record):
    """Patch storage to 200 success."""
    with patch.object(storage_record_service_mock, storage_method, return_value=osdu_record):
        yield


@pytest.fixture
def with_patched_storage_get_mismatched_version():
    """Patch storage to return a record with a mismatched version (simulating fuzzy match)."""
    with patch.object(
        storage_record_service_mock,
        "get_record",
        return_value={"id": "test:id", "version": 999},
    ):
        yield


@pytest.fixture
def with_patched_schema_validate_success():
    """Patch schema with mock to validate success."""
    with patch.object(schema_service_mock, "validate", return_value={}):
        yield


@pytest.fixture
def with_patched_schema_get_success(schema):
    """Patch  get_schema to provided schema."""
    with patch.object(SchemaService, "get_schema", return_value=schema):
        yield


@pytest.fixture
def with_patched_storage_get_versions_success_200(storage_method):
    """Patch storage to 200 success."""
    with patch.object(
        storage_record_service_mock,
        storage_method,
        return_value=STORAGE_SERVICE_200_VERSIONS_RESPONSE,
    ):
        yield


@pytest.fixture()
def with_patched_storage_samplesanalysis_missing_reference():
    """Patch storage to return missing SamplesAnalysesReport record ID."""
    return_value = {
        "records": [],
        "invalidRecords": [storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID],
        "retryRecords": [],
    }
    with patch.object(
        storage_record_service_mock,
        "query_records",
        return_value=return_value,
    ):
        yield


@pytest.fixture()
def with_patched_storage_samplesanalysis_existing_parent():
    """Patch storage to return existing SamplesAnalysesReport record ID."""
    return_value = {
        "records": [storage_mock_objects.SAMPLESANALYSIS_RECORD_V2],
        "invalidRecords": [],
        "retryRecords": [],
    }
    with patch.object(
        storage_record_service_mock,
        "query_records",
        return_value=return_value,
    ):
        yield


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_method,path,record_id",
    [
        (
            "get_record",
            f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}",
            storage_mock_objects.TEST_RESERVOIR_SIMULATION_ROCK_PHYSICS_ID,
        ),
        ("get_record", f"{API_VERSION_V2}/samplesanalysesreport", storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID),
        ("get_record", f"{API_VERSION_V2}/samplesanalysis", storage_mock_objects.TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION_V2}/saturationfunctionset", storage_mock_objects.TEST_SATURATION_FUNCTION_SET_ID),
        ("get_record", f"{API_VERSION_V2}/fluidmodel", storage_mock_objects.TEST_FLUID_MODEL_ID),
        ("get_record", f"{API_VERSION_V2}/depthshift", storage_mock_objects.TEST_DEPTH_SHIFT_ID),
        ("get_record", f"{API_VERSION_V2}/masterdata", storage_mock_objects.TEST_SAMPLE_ID),
    ],
)
async def test_get_record_not_found(storage_method, path, record_id, with_patched_storage_raises_404):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"/api/os-rafs-ddms/{path}/{record_id}",
                headers=TEST_HEADERS,
            )
    assert all((response.json().get(k) == v for k, v in EXPECTED_404_RESPONSE.items()))
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_method,path,record_id",
    [
        (
            "get_record",
            f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}",
            storage_mock_objects.TEST_RESERVOIR_SIMULATION_ROCK_PHYSICS_ID,
        ),
        ("get_record", f"{API_VERSION_V2}/samplesanalysesreport", storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID),
        ("get_record", f"{API_VERSION_V2}/samplesanalysis", storage_mock_objects.TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION_V2}/saturationfunctionset", storage_mock_objects.TEST_SATURATION_FUNCTION_SET_ID),
        ("get_record", f"{API_VERSION_V2}/fluidmodel", storage_mock_objects.TEST_FLUID_MODEL_ID),
        ("get_record", f"{API_VERSION_V2}/depthshift", storage_mock_objects.TEST_DEPTH_SHIFT_ID),
        ("get_record", f"{API_VERSION_V2}/masterdata", storage_mock_objects.TEST_SAMPLE_ID),
    ],
)
async def test_get_record_version_not_found(storage_method, path, record_id, with_patched_storage_raises_404):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"/api/os-rafs-ddms/{path}/{record_id}/versions/1234",
                headers=TEST_HEADERS,
            )

    assert response.json() == EXPECTED_404_RESPONSE
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,record_id",
    [
        (
            f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}",
            storage_mock_objects.TEST_RESERVOIR_SIMULATION_ROCK_PHYSICS_ID,
        ),
        (f"{API_VERSION_V2}/samplesanalysesreport", storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID),
        (f"{API_VERSION_V2}/samplesanalysis", storage_mock_objects.TEST_SAMPLESANALYSIS_ID),
        (f"{API_VERSION_V2}/saturationfunctionset", storage_mock_objects.TEST_SATURATION_FUNCTION_SET_ID),
        (f"{API_VERSION_V2}/fluidmodel", storage_mock_objects.TEST_FLUID_MODEL_ID),
        (f"{API_VERSION_V2}/depthshift", storage_mock_objects.TEST_DEPTH_SHIFT_ID),
        (f"{API_VERSION_V2}/masterdata", storage_mock_objects.TEST_SAMPLE_ID),
    ],
)
async def test_get_record_version_mismatch(path, record_id, with_patched_storage_get_mismatched_version):
    """Test that requesting a version that results in a fuzzy match returns a 404."""
    with storage_override():
        requested_version = 123
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"/api/os-rafs-ddms/{path}/{record_id}/versions/{requested_version}",
                headers=TEST_HEADERS,
            )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    # Relax detail check to avoid KeyError if standard FastAPI handler is overridden.
    assert f"{requested_version} not found" in response.text.lower()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,record_id,version",
    [
        (
            f"{API_VERSION_V2}/samplesanalysis",
            storage_mock_objects.TEST_SAMPLESANALYSIS_ID,
            12345678901234567890,
        ),
        (
            f"{API_VERSION_V2}/samplesanalysis",
            storage_mock_objects.TEST_SAMPLESANALYSIS_ID,
            0,
        ),
        (
            f"{API_VERSION_V2}/saturationfunctionset",
            storage_mock_objects.TEST_SATURATION_FUNCTION_SET_ID,
            12345678901234567890,
        ),
        (
            f"{API_VERSION_V2}/saturationfunctionset",
            storage_mock_objects.TEST_SATURATION_FUNCTION_SET_ID,
            0,
        ),
    ],
)
async def test_get_record_version_invalid_version(path, record_id, version):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"/api/os-rafs-ddms/{path}/{record_id}/versions/{version}",
                headers=TEST_HEADERS,
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    storage_record_service_mock.get_record.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_method,path,record_id",
    [
        (
            "get_record_versions",
            f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}",
            storage_mock_objects.TEST_RESERVOIR_SIMULATION_ROCK_PHYSICS_ID,
        ),
        (
            "get_record_versions",
            f"{API_VERSION_V2}/samplesanalysesreport",
            storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID,
        ),
        ("get_record_versions", f"{API_VERSION_V2}/samplesanalysis", storage_mock_objects.TEST_SAMPLESANALYSIS_ID),
        (
            "get_record_versions",
            f"{API_VERSION_V2}/saturationfunctionset",
            storage_mock_objects.TEST_SATURATION_FUNCTION_SET_ID,
        ),
        ("get_record_versions", f"{API_VERSION_V2}/fluidmodel", storage_mock_objects.TEST_FLUID_MODEL_ID),
        ("get_record_versions", f"{API_VERSION_V2}/depthshift", storage_mock_objects.TEST_DEPTH_SHIFT_ID),
        ("get_record_versions", f"{API_VERSION_V2}/masterdata", storage_mock_objects.TEST_SAMPLE_ID),
    ],
)
async def test_get_record_versions_not_found(
    storage_method,
    path,
    record_id,
    with_patched_storage_raises_404,
):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"/api/os-rafs-ddms/{path}/{record_id}/versions",
                headers=TEST_HEADERS,
            )

    assert response.json() == EXPECTED_404_RESPONSE
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_method,path,record_id",
    [
        (
            "soft_delete_record",
            f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}",
            storage_mock_objects.TEST_RESERVOIR_SIMULATION_ROCK_PHYSICS_ID,
        ),
        (
            "soft_delete_record",
            f"{API_VERSION_V2}/samplesanalysesreport",
            storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID,
        ),
        ("soft_delete_record", f"{API_VERSION_V2}/samplesanalysis", storage_mock_objects.TEST_SAMPLESANALYSIS_ID),
        (
            "soft_delete_record",
            f"{API_VERSION_V2}/saturationfunctionset",
            storage_mock_objects.TEST_SATURATION_FUNCTION_SET_ID,
        ),
        ("soft_delete_record", f"{API_VERSION_V2}/fluidmodel", storage_mock_objects.TEST_FLUID_MODEL_ID),
        ("soft_delete_record", f"{API_VERSION_V2}/depthshift", storage_mock_objects.TEST_DEPTH_SHIFT_ID),
        ("soft_delete_record", f"{API_VERSION_V2}/masterdata", storage_mock_objects.TEST_SAMPLE_ID),
    ],
)
async def test_delete_record_not_found(
    storage_method,
    path,
    record_id,
    with_patched_storage_raises_404,
):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.delete(
                f"/api/os-rafs-ddms/{path}/{record_id}",
                headers=TEST_HEADERS,
            )

    assert response.json() == EXPECTED_404_RESPONSE
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        (f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}"),
        (f"{API_VERSION_V2}/samplesanalysesreport"),
        (f"{API_VERSION_V2}/samplesanalysis"),
        (f"{API_VERSION_V2}/saturationfunctionset"),
        (f"{API_VERSION_V2}/fluidmodel"),
        (f"{API_VERSION_V2}/depthshift"),
        (f"{API_VERSION_V2}/masterdata"),
    ],
)
async def test_post_record_no_kind(path):
    osdu_generic_record = OSDU_GENERIC_RECORD.dict()
    osdu_generic_record.pop("kind")

    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                f"/api/os-rafs-ddms/{path}",
                headers=TEST_HEADERS,
                json=[osdu_generic_record],
            )

    response_json = response.json()
    assert response_json["code"] == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert storage_mock_objects.EXPECTED_422_NO_KIND_RESPONSE == response_json


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        (f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}"),
        (f"{API_VERSION_V2}/samplesanalysesreport"),
        (f"{API_VERSION_V2}/samplesanalysis"),
        (f"{API_VERSION_V2}/saturationfunctionset"),
        (f"{API_VERSION_V2}/fluidmodel"),
        (f"{API_VERSION_V2}/depthshift"),
        (f"{API_VERSION_V2}/masterdata"),
    ],
)
async def test_post_record_invalid_payload_type(path):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(f"/api/os-rafs-ddms/{path}", headers=TEST_HEADERS, json={})

    assert response.json()["code"] == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["errors"][0] == EXPECTED_422_TYPER_ERROR_LIST


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_method,path,osdu_record,schema",
    [
        (
            "upsert_records",
            f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}",
            storage_mock_objects.RESERVOIR_SIMULATION_ROCK_PHYSICS_RECORD,
            storage_mock_objects.RESERVOIR_SIMULATION_ROCK_PHYSICS_SCHEMA,
        ),
        (
            "upsert_records",
            f"{API_VERSION_V2}/samplesanalysesreport",
            storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V2,
            storage_mock_objects.SAMPLES_ANALYSES_REPORT_SCHEMA,
        ),
        (
            "upsert_records",
            f"{API_VERSION_V2}/samplesanalysis",
            storage_mock_objects.SAMPLESANALYSIS_RECORD_V2,
            storage_mock_objects.SAMPLES_ANALYSIS_SCHEMA,
        ),
        (
            "upsert_records",
            f"{API_VERSION_V2}/saturationfunctionset",
            storage_mock_objects.SATURATION_FUNCTION_SET_RECORD,
            storage_mock_objects.SATURATION_FUNCTION_SET_SCHEMA,
        ),
        (
            "upsert_records",
            f"{API_VERSION_V2}/fluidmodel",
            storage_mock_objects.FLUID_MODEL_RECORD,
            storage_mock_objects.FLUID_MODEL_SCHEMA,
        ),
        (
            "upsert_records",
            f"{API_VERSION_V2}/depthshift",
            storage_mock_objects.DEPTH_SHIFT_RECORD,
            storage_mock_objects.DEPTH_SHIFT_SCHEMA,
        ),
        (
            "upsert_records",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_RECORD,
            storage_mock_objects.SAMPLE_SCHEMA,
        ),
        (
            "upsert_records",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.GENERIC_FACILITY_RECORD,
            storage_mock_objects.GENERIC_FACILITY_RECORD.schema(),
        ),
        (
            "upsert_records",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_ACQUISITION_JOB_RECORD,
            storage_mock_objects.SAMPLE_ACQUISITION_JOB_SCHEMA,
        ),
        (
            "upsert_records",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CHAIN_OF_CUSTODY_EVENT_RECORD,
            storage_mock_objects.SAMPLE_CHAIN_OF_CUSTODY_EVENT_SCHEMA,
        ),
        (
            "upsert_records",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CONTAINER_RECORD,
            storage_mock_objects.SAMPLE_CONTAINER_SCHEMA,
        ),
    ],
)
async def test_post_record_success_with_jsonschema(
    storage_method,
    path,
    osdu_record,
    schema,
    with_patched_storage_created_200,
    with_patched_schema_get_success,
):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                f"/api/os-rafs-ddms/{path}",
                headers=TEST_HEADERS,
                json=[osdu_record.dict(exclude_none=True)],
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == EXPECTED_200_CREATED_RESPONSE
    storage_record_service_mock.upsert_records.assert_called_once_with(
        [osdu_record.dict(exclude_none=True)],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,osdu_record,checked_fields",
    [
        (
            f"{API_VERSION_V2}/samplesanalysis",
            storage_mock_objects.SAMPLESANALYSIS_RECORD_V2,
            ["ParentSamplesAnalysesReports", "SampleAnalysisTypeIDs"],
        ),
        (
            f"{API_VERSION_V2}/samplesanalysesreport",
            storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V2,
            ["SampleAnalysisTypeIDs"],
        ),
    ],
)
async def test_post_samplesanalysis_with_missing_reference(
    path,
    osdu_record,
    checked_fields,
    with_patched_storage_samplesanalysis_missing_reference,
    with_patched_schema_validate_success,
):
    with storage_schema_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                f"/api/os-rafs-ddms/{path}",
                headers=TEST_HEADERS,
                json=[osdu_record.dict(exclude_none=True)],
            )

    title = "Request can't be processed due to missing referenced records."
    detail = f"Records not found: ['{storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID}']"
    expected_response = {
        "code": 422,
        "reason": f"{title} {detail}",
    }

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    result_json = response.json()
    assert result_json == expected_response


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_method,path,osdu_record",
    [
        (
            "upsert_records",
            f"{API_VERSION_V2}/samplesanalysis",
            storage_mock_objects.SAMPLESANALYSIS_RECORD_V2,
        ),
        (
            "upsert_records",
            f"{API_VERSION_V2}/samplesanalysis",
            storage_mock_objects.SAMPLESANALYSIS_RECORD_WITHOUT_PARENT_V2,
        ),
    ],
)
async def test_post_samplesanalysis_success(
    storage_method,
    path,
    osdu_record,
    with_patched_storage_created_200,
    with_patched_storage_samplesanalysis_existing_parent,
    with_patched_schema_validate_success,
):
    with storage_schema_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                f"/api/os-rafs-ddms/{path}",
                headers=TEST_HEADERS,
                json=[osdu_record.dict(exclude_none=True)],
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == EXPECTED_200_CREATED_RESPONSE
    storage_record_service_mock.upsert_records.assert_called_once_with(
        [osdu_record.dict(exclude_none=True)],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_method,path,osdu_record",
    [
        (
            "upsert_records",
            f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}",
            storage_mock_objects.RESERVOIR_SIMULATION_ROCK_PHYSICS_RECORD,
        ),
        (
            "upsert_records",
            f"{API_VERSION_V2}/samplesanalysesreport",
            storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V2,
        ),
        ("upsert_records", f"{API_VERSION_V2}/samplesanalysis", storage_mock_objects.SAMPLESANALYSIS_RECORD_V2),
        (
            "upsert_records",
            f"{API_VERSION_V2}/saturationfunctionset",
            storage_mock_objects.SATURATION_FUNCTION_SET_RECORD,
        ),
        (
            "upsert_records",
            f"{API_VERSION_V2}/fluidmodel",
            storage_mock_objects.FLUID_MODEL_RECORD,
        ),
        (
            "upsert_records",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_RECORD,
        ),
        (
            "upsert_records",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_ACQUISITION_JOB_RECORD,
        ),
        (
            "upsert_records",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CHAIN_OF_CUSTODY_EVENT_RECORD,
        ),
        (
            "upsert_records",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CONTAINER_RECORD,
        ),
        (
            "upsert_records",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.GENERIC_FACILITY_RECORD,
        ),
        (
            "upsert_records",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.GENERIC_SITE_RECORD,
        ),
    ],
)
async def test_post_record_no_id(
    storage_method,
    path,
    osdu_record,
    with_patched_storage_created_200,
    with_patched_schema_validate_success,
):
    osdu_record_json = osdu_record.dict(
        exclude={"id"},
        exclude_none=True,
    )
    with storage_schema_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                f"/api/os-rafs-ddms/{path}",
                headers=TEST_HEADERS,
                json=[osdu_record_json],
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == EXPECTED_200_CREATED_RESPONSE
    storage_record_service_mock.upsert_records.assert_called_once_with([osdu_record_json])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_method,path,osdu_record,record_id",
    [
        (
            "get_record",
            f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}",
            storage_mock_objects.RESERVOIR_SIMULATION_ROCK_PHYSICS_RECORD,
            storage_mock_objects.TEST_RESERVOIR_SIMULATION_ROCK_PHYSICS_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/samplesanalysesreport",
            storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V2,
            storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/samplesanalysis",
            storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V2,
            storage_mock_objects.TEST_SAMPLESANALYSIS_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/saturationfunctionset",
            storage_mock_objects.SATURATION_FUNCTION_SET_RECORD,
            storage_mock_objects.TEST_SATURATION_FUNCTION_SET_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/fluidmodel",
            storage_mock_objects.FLUID_MODEL_RECORD,
            storage_mock_objects.TEST_FLUID_MODEL_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_RECORD,
            storage_mock_objects.TEST_SAMPLE_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_ACQUISITION_JOB_RECORD,
            storage_mock_objects.TEST_SAMPLE_ACQUISITION_JOB_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CHAIN_OF_CUSTODY_EVENT_RECORD,
            storage_mock_objects.TEST_SAMPLE_CHAIN_OF_CUSTODY_EVENT_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CONTAINER_RECORD,
            storage_mock_objects.TEST_SAMPLE_CONTAINER_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.GENERIC_FACILITY_RECORD,
            storage_mock_objects.TEST_GENERIC_FACILITY_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.GENERIC_SITE_RECORD,
            storage_mock_objects.TEST_GENERIC_SITE_ID,
        ),
    ],
)
async def test_get_record_success(
    storage_method,
    path,
    osdu_record,
    record_id,
    with_patched_storage_get_success_200,
):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(f"/api/os-rafs-ddms/{path}/{record_id}", headers=TEST_HEADERS)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == osdu_record.dict()
    storage_record_service_mock.get_record.assert_called_once_with(record_id)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_method,path,osdu_record,record_id",
    [
        (
            "get_record",
            f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}",
            storage_mock_objects.RESERVOIR_SIMULATION_ROCK_PHYSICS_RECORD,
            storage_mock_objects.TEST_RESERVOIR_SIMULATION_ROCK_PHYSICS_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/samplesanalysesreport",
            storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V2,
            storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/samplesanalysis",
            storage_mock_objects.SAMPLESANALYSIS_RECORD_V2,
            storage_mock_objects.TEST_SAMPLESANALYSIS_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/saturationfunctionset",
            storage_mock_objects.SATURATION_FUNCTION_SET_RECORD,
            storage_mock_objects.TEST_SATURATION_FUNCTION_SET_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/fluidmodel",
            storage_mock_objects.FLUID_MODEL_RECORD,
            storage_mock_objects.TEST_FLUID_MODEL_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_RECORD,
            storage_mock_objects.TEST_SAMPLE_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_ACQUISITION_JOB_RECORD,
            storage_mock_objects.TEST_SAMPLE_ACQUISITION_JOB_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CHAIN_OF_CUSTODY_EVENT_RECORD,
            storage_mock_objects.TEST_SAMPLE_CHAIN_OF_CUSTODY_EVENT_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CONTAINER_RECORD,
            storage_mock_objects.TEST_SAMPLE_CONTAINER_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.GENERIC_FACILITY_RECORD,
            storage_mock_objects.TEST_GENERIC_FACILITY_ID,
        ),
        (
            "get_record",
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.GENERIC_SITE_RECORD,
            storage_mock_objects.TEST_GENERIC_SITE_ID,
        ),
    ],
)
async def test_get_record_version_success(
    storage_method,
    path,
    osdu_record,
    record_id,
    with_patched_storage_get_success_200,
):
    with storage_override():
        test_version = 1234
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"/api/os-rafs-ddms/{path}/{record_id}/versions/{test_version}",
                headers=TEST_HEADERS,
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == osdu_record.dict()
    storage_record_service_mock.get_record.assert_called_once_with(record_id, test_version)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_method,path,record_id",
    [
        (
            "get_record_versions",
            f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}",
            storage_mock_objects.TEST_RESERVOIR_SIMULATION_ROCK_PHYSICS_ID,
        ),
        (
            "get_record_versions",
            f"{API_VERSION_V2}/samplesanalysesreport",
            storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID,
        ),
        ("get_record_versions", f"{API_VERSION_V2}/samplesanalysis", storage_mock_objects.TEST_SAMPLESANALYSIS_ID),
        (
            "get_record_versions",
            f"{API_VERSION_V2}/saturationfunctionset",
            storage_mock_objects.TEST_SATURATION_FUNCTION_SET_ID,
        ),
        ("get_record_versions", f"{API_VERSION_V2}/fluidmodel", storage_mock_objects.TEST_FLUID_MODEL_ID),
        ("get_record_versions", f"{API_VERSION_V2}/masterdata", storage_mock_objects.TEST_SAMPLE_ID),
    ],
)
async def test_get_record_versions_success(
    storage_method,
    path,
    record_id,
    with_patched_storage_get_versions_success_200,
):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(f"/api/os-rafs-ddms/{path}/{record_id}/versions", headers=TEST_HEADERS)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == EXPECTED_200_VERSIONS_RESPONSE
    storage_record_service_mock.get_record_versions.assert_called_once_with(record_id)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_method,api_status_code,path",
    [
        (
            "get_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}/{storage_mock_objects.TEST_RESERVOIR_SIMULATION_ROCK_PHYSICS_ID}",
        ),
        (
            "get_record_versions",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}/{storage_mock_objects.TEST_RESERVOIR_SIMULATION_ROCK_PHYSICS_ID}/versions",
        ),
        (
            "get_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}/{storage_mock_objects.TEST_RESERVOIR_SIMULATION_ROCK_PHYSICS_ID}/versions/1234",
        ),
        (
            "get_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/samplesanalysesreport/{storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID}",
        ),
        (
            "get_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/samplesanalysis/{storage_mock_objects.TEST_SAMPLESANALYSIS_ID}",
        ),
        (
            "get_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/saturationfunctionset/{storage_mock_objects.TEST_SATURATION_FUNCTION_SET_ID}",
        ),
        (
            "get_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/fluidmodel/{storage_mock_objects.TEST_FLUID_MODEL_ID}",
        ),
        (
            "get_record_versions",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/samplesanalysesreport/{storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID}/versions",
        ),
        (
            "get_record_versions",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/samplesanalysis/{storage_mock_objects.TEST_SAMPLESANALYSIS_ID}/versions",
        ),
        (
            "get_record_versions",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/saturationfunctionset/{storage_mock_objects.TEST_SATURATION_FUNCTION_SET_ID}/versions",
        ),
        (
            "get_record_versions",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/fluidmodel/{storage_mock_objects.TEST_FLUID_MODEL_ID}/versions",
        ),
        (
            "get_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/samplesanalysesreport/{storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID}/versions/1234",
        ),
        (
            "get_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/samplesanalysis/{storage_mock_objects.TEST_SAMPLESANALYSIS_ID}/versions/1234",
        ),
        (
            "get_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/saturationfunctionset/{storage_mock_objects.TEST_SATURATION_FUNCTION_SET_ID}/versions/1234",
        ),
        (
            "get_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/fluidmodel/{storage_mock_objects.TEST_FLUID_MODEL_ID}/versions/1234",
        ),
        (
            "get_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/masterdata/{storage_mock_objects.TEST_SAMPLE_ID}",
        ),
        (
            "get_record_versions",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/masterdata/{storage_mock_objects.TEST_SAMPLE_ID}/versions",
        ),
        (
            "get_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/masterdata/{storage_mock_objects.TEST_SAMPLE_ID}/versions/1234",
        ),
    ],
)
async def test_get_record_auth_errors_from_storage(
    storage_method,
    api_status_code,
    path,
    with_patched_storage_raises_40x,
):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(f"/api/os-rafs-ddms/{path}", headers=TEST_HEADERS)

    assert response.status_code == api_status_code


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        (f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}/record_id"),
        (f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}/record_id/versions"),
        (f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}/record_id/versions/1234"),
        (f"{API_VERSION_V2}/samplesanalysesreport/record_id"),
        (f"{API_VERSION_V2}/samplesanalysesreport/record_id/versions"),
        (f"{API_VERSION_V2}/samplesanalysesreport/record_id/versions/1234"),
        (f"{API_VERSION_V2}/samplesanalysis/record_id"),
        (f"{API_VERSION_V2}/samplesanalysis/record_id/versions"),
        (f"{API_VERSION_V2}/samplesanalysis/record_id/versions/1234"),
        (f"{API_VERSION_V2}/saturationfunctionset/record_id"),
        (f"{API_VERSION_V2}/saturationfunctionset/record_id/versions"),
        (f"{API_VERSION_V2}/saturationfunctionset/record_id/versions/1234"),
        (f"{API_VERSION_V2}/fluidmodel/record_id"),
        (f"{API_VERSION_V2}/fluidmodel/record_id/versions"),
        (f"{API_VERSION_V2}/fluidmodel/record_id/versions/1234"),
        (f"{API_VERSION_V2}/masterdata/record_id"),
        (f"{API_VERSION_V2}/masterdata/record_id/versions"),
        (f"{API_VERSION_V2}/masterdata/record_id/versions/1234"),
    ],
)
async def test_get_record_auth_errors(
    path,
):
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        response = await client.get(f"/api/os-rafs-ddms/{path}", headers=TEST_HEADERS_NO_AUTH)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_method,api_status_code,path",
    [
        (
            "soft_delete_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}/{storage_mock_objects.TEST_RESERVOIR_SIMULATION_ROCK_PHYSICS_ID}",
        ),
        (
            "soft_delete_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/samplesanalysesreport/{storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID}",
        ),
        (
            "soft_delete_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/samplesanalysis/{storage_mock_objects.TEST_SAMPLESANALYSIS_ID}",
        ),
        (
            "soft_delete_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/saturationfunctionset/{storage_mock_objects.TEST_SATURATION_FUNCTION_SET_ID}",
        ),
        (
            "soft_delete_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/fluidmodel/{storage_mock_objects.TEST_FLUID_MODEL_ID}",
        ),
        (
            "soft_delete_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/masterdata/{storage_mock_objects.TEST_SAMPLE_ID}",
        ),
    ],
)
async def test_delete_record_auth_errors_from_storage(
    storage_method,
    api_status_code,
    path,
    with_patched_storage_raises_40x,
):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.delete(f"/api/os-rafs-ddms/{path}", headers=TEST_HEADERS)

    assert response.status_code == api_status_code


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        (f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}/record_id"),
        (f"{API_VERSION_V2}/samplesanalysesreport/record_id"),
        (f"{API_VERSION_V2}/samplesanalysis/record_id"),
        (f"{API_VERSION_V2}/saturationfunctionset/record_id"),
        (f"{API_VERSION_V2}/fluidmodel/record_id"),
        (f"{API_VERSION_V2}/masterdata/record_id"),
    ],
)
async def test_delete_record_auth_errors(
    path,
):
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        response = await client.delete(f"/api/os-rafs-ddms/{path}", headers=TEST_HEADERS_NO_AUTH)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_method,api_status_code,path,osdu_record",
    [
        (
            "upsert_records",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}",
            storage_mock_objects.RESERVOIR_SIMULATION_ROCK_PHYSICS_RECORD,
        ),
        (
            "upsert_records",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/samplesanalysesreport",
            storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V2,
        ),
        (
            "upsert_records",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/samplesanalysis",
            storage_mock_objects.SAMPLESANALYSIS_RECORD_V2,
        ),
        (
            "upsert_records",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/saturationfunctionset",
            storage_mock_objects.SATURATION_FUNCTION_SET_RECORD,
        ),
        (
            "upsert_records",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/fluidmodel",
            storage_mock_objects.FLUID_MODEL_RECORD,
        ),
        (
            "upsert_records",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_RECORD,
        ),
        (
            "upsert_records",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_ACQUISITION_JOB_RECORD,
        ),
        (
            "upsert_records",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CHAIN_OF_CUSTODY_EVENT_RECORD,
        ),
        (
            "upsert_records",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CONTAINER_RECORD,
        ),
        (
            "upsert_records",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.GENERIC_FACILITY_RECORD,
        ),
        (
            "upsert_records",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.GENERIC_SITE_RECORD,
        ),
    ],
)
async def test_post_record_auth_errors_from_storage(
    storage_method,
    api_status_code,
    path,
    osdu_record,
    with_patched_storage_raises_40x,
    with_patched_schema_validate_success,
):
    with storage_schema_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                f"/api/os-rafs-ddms/{path}",
                headers=TEST_HEADERS,
                json=[osdu_record.dict(exclude_none=True)],
            )

    assert response.status_code == api_status_code


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,osdu_record",
    [
        (
            f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}",
            storage_mock_objects.RESERVOIR_SIMULATION_ROCK_PHYSICS_RECORD,
        ),
        (f"{API_VERSION_V2}/samplesanalysesreport", storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V2),
        (f"{API_VERSION_V2}/samplesanalysis", storage_mock_objects.SAMPLESANALYSIS_RECORD_V2),
        (f"{API_VERSION_V2}/saturationfunctionset", storage_mock_objects.SATURATION_FUNCTION_SET_RECORD),
        (f"{API_VERSION_V2}/fluidmodel", storage_mock_objects.FLUID_MODEL_RECORD),
        (
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_RECORD,
        ),
        (
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_ACQUISITION_JOB_RECORD,
        ),
        (
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CHAIN_OF_CUSTODY_EVENT_RECORD,
        ),
        (
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CONTAINER_RECORD,
        ),
        (
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.GENERIC_FACILITY_RECORD,
        ),
        (
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.GENERIC_SITE_RECORD,
        ),
    ],
)
async def test_post_record_auth_errors(
    path,
    osdu_record,
):
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        response = await client.post(
            f"/api/os-rafs-ddms/{path}",
            headers=TEST_HEADERS_NO_AUTH,
            json=[osdu_record.dict(exclude_none=True)],
        )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint,record_id",
    [
        (storage_mock_objects.SAMPLESANALYSES_REPORT_ENDPOINT_PATH_V2, TEST_WRONG_ID),
        (storage_mock_objects.SAMPLESANALYSIS_ENDPOINT_PATH_V2, TEST_WRONG_ID),
        (storage_mock_objects.FLUID_MODEL_ENDPOINT_PATH_V2, TEST_WRONG_ID),
        (storage_mock_objects.MASTER_DATA_ENDPOINT_PATH_V2, TEST_WRONG_ID),
    ],
)
async def test_get_record_wrong_id_pattern(endpoint, record_id):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"{endpoint}/{record_id}",
                headers=TEST_HEADERS,
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint,manifest",
    [
        (storage_mock_objects.SAMPLESANALYSES_REPORT_ENDPOINT_PATH_V2, OSDU_GENERIC_RECORD.dict()),
        (storage_mock_objects.SAMPLESANALYSIS_ENDPOINT_PATH_V2, OSDU_GENERIC_RECORD.dict()),
        (storage_mock_objects.FLUID_MODEL_ENDPOINT_PATH_V2, OSDU_GENERIC_RECORD.dict()),
        (storage_mock_objects.MASTER_DATA_ENDPOINT_PATH_V2, OSDU_GENERIC_RECORD.dict()),
    ],
)
async def test_post_record_wrong_kind(endpoint, manifest):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                endpoint,
                headers=TEST_HEADERS,
                json=[manifest],
            )

    response_json = response.json()
    assert response_json["code"] == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert EXPECTED_422_INVALID_KIND_REASON.format(manifest["kind"]) in response_json["reason"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint,osdu_record,schema,new_version",
    [
        (
            storage_mock_objects.MASTER_DATA_ENDPOINT_PATH_V2,
            storage_mock_objects.SAMPLE_RECORD,
            storage_mock_objects.SAMPLE_SCHEMA,
            "3.0.0",
        ),
        (
            storage_mock_objects.MASTER_DATA_ENDPOINT_PATH_V2,
            storage_mock_objects.SAMPLE_RECORD,
            storage_mock_objects.SAMPLE_SCHEMA,
            "1.2.3",
        ),
        (
            storage_mock_objects.SAMPLESANALYSIS_ENDPOINT_PATH_V2,
            storage_mock_objects.SAMPLESANALYSIS_RECORD_V2,
            storage_mock_objects.SAMPLES_ANALYSIS_SCHEMA,
            "2.0.0",
        ),
    ],
)
async def test_post_record_new_semver_passes_kind_validation(endpoint, osdu_record, schema, new_version):
    record_dict = osdu_record.dict(exclude_none=True)
    kind_base = ":".join(record_dict["kind"].split(":")[:3])
    record_dict["kind"] = f"{kind_base}:{new_version}"

    with storage_schema_override():
        with patch.object(
            storage_record_service_mock,
            "upsert_records",
            return_value=STORAGE_SERVICE_200_RESPONSE,
        ):
            with patch.object(
                storage_record_service_mock,
                "query_records",
                return_value={"records": [], "invalidRecords": [], "retryRecords": []},
            ):
                with patch.object(SchemaService, "get_schema", return_value=schema):
                    with patch.object(schema_service_mock, "validate", return_value={}):
                        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                            response = await client.post(
                                endpoint,
                                headers=TEST_HEADERS,
                                json=[record_dict],
                            )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint,record_id",
    [
        (storage_mock_objects.SAMPLESANALYSES_REPORT_ENDPOINT_PATH_V2, TEST_WRONG_ID),
        (storage_mock_objects.SAMPLESANALYSIS_ENDPOINT_PATH_V2, TEST_WRONG_ID),
        (storage_mock_objects.FLUID_MODEL_ENDPOINT_PATH_V2, TEST_WRONG_ID),
        (storage_mock_objects.MASTER_DATA_ENDPOINT_PATH_V2, TEST_WRONG_ID),
    ],
)
async def test_delete_record_wrong_id_pattern(endpoint, record_id):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.delete(
                f"{endpoint}/{record_id}",
                headers=TEST_HEADERS,
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,osdu_record,field,schema",
    [
        (
            f"{API_VERSION_V2}/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}",
            storage_mock_objects.RESERVOIR_SIMULATION_ROCK_PHYSICS_RECORD,
            "ResourceHomeRegionID",
            storage_mock_objects.RESERVOIR_SIMULATION_ROCK_PHYSICS_SCHEMA,
        ),
        (
            f"{API_VERSION_V2}/samplesanalysesreport",
            storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V2,
            "ResourceHomeRegionID",
            storage_mock_objects.SAMPLES_ANALYSES_REPORT_SCHEMA,
        ),
        (
            f"{API_VERSION_V2}/samplesanalysis",
            storage_mock_objects.SAMPLESANALYSIS_RECORD_V2,
            "ResourceHomeRegionID",
            storage_mock_objects.SAMPLES_ANALYSIS_SCHEMA,
        ),
        (
            f"{API_VERSION_V2}/saturationfunctionset",
            storage_mock_objects.SATURATION_FUNCTION_SET_RECORD,
            "ResourceHomeRegionID",
            storage_mock_objects.SATURATION_FUNCTION_SET_SCHEMA,
        ),
        (
            f"{API_VERSION_V2}/fluidmodel",
            storage_mock_objects.FLUID_MODEL_RECORD,
            "ResourceHomeRegionID",
            storage_mock_objects.FLUID_MODEL_SCHEMA,
        ),
        (
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_RECORD,
            "ResourceHomeRegionID",
            storage_mock_objects.SAMPLE_SCHEMA,
        ),
    ],
)
async def test_post_record_invalid_field_type_jsonschema(
    path, osdu_record, field, schema, with_patched_schema_get_success
):
    osdu_record_wrong_field_type = osdu_record.dict(exclude_none=True)
    osdu_record_wrong_field_type.update(
        {
            "data": {
                field: "wrong_pattern",
                "Parameters": [],
            },
        }
    )

    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                f"/api/os-rafs-ddms/{path}",
                headers=TEST_HEADERS,
                json=[osdu_record_wrong_field_type],
            )
    from loguru import logger

    logger.warning(response.json())
    assert response.json()["code"] == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "'wrong_pattern' does not match" in response.json()["reason"][0]["errors"][0]
