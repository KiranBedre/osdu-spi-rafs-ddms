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
import copy
from contextlib import contextmanager
from unittest.mock import call, create_autospec, patch

import pytest
from httpx import AsyncClient, HTTPStatusError
from starlette import status

from app.api.dependencies.services import get_async_storage_service
from app.main import app
from app.services.storage import StorageService
from tests.test_api.api_version import API_VERSION, API_VERSION_V2
from tests.test_api.test_routes import dependencies
from tests.test_api.test_routes.osdu import storage_mock_objects
from tests.test_api.test_routes.osdu.storage_mock_objects import (
    CAP_PRESSURE_ENDPOINT_PATH,
    CCE_ENDPOINT_PATH,
    CCE_RECORD,
    COMPOSITIONALANALYSIS_ENDPOINT_PATH,
    COMPOSITIONALANALYSIS_RECORD,
    CORING_ENDPOINT_PATH,
    CORING_RECORD,
    CVD_ENDPOINT_PATH,
    CVD_RECORD,
    DIF_LIB_ENDPOINT_PATH,
    DL_RECORD,
    ELECTRICAL_PROPERTIES_ENDPOINT_PATH,
    EXPECTED_200_CREATED_PVT_UPDATED_RESPONSE,
    EXPECTED_200_CREATED_RESPONSE,
    EXPECTED_200_VERSIONS_RESPONSE,
    EXPECTED_400_RESPONSE_ON_INVALID_PARENT_PVT,
    EXPECTED_404_RESPONSE,
    EXPECTED_422_INVALID_KIND_REASON,
    EXPECTED_422_RESPONSE_ON_MISSING_SAMPLESANALYSESREPORT,
    EXPECTED_422_TYPER_ERROR_LIST,
    EXPECTED_422_WRONG_PATTERN,
    EXTRACTION_ENDPOINT_PATH,
    FORMATION_RESISTIVITY_INDEX_ENDPOINT_PATH,
    FRACTIONATION_ENDPOINT_PATH,
    INTERFACIAL_TENSION_ENDPOINT_PATH,
    INTERFACIAL_TENSION_RECORD,
    MCM_ENDPOINT_PATH,
    MCM_RECORD,
    MSS_ENDPOINT_PATH,
    MULTISTAGESEPARATOR_RECORD,
    OSDU_GENERIC_RECORD,
    PHYS_CHEM_ENDPOINT_PATH,
    PVT_ENDPOINT_PATH,
    PVT_QUERY_STORAGE_SERVICE_200_RESPONSE,
    PVT_RECORD,
    PVT_STORAGE_SERVICE_200_RESPONSE,
    RELATIVE_PERMEABILITY_ENDPOINT_PATH,
    ROCK_COMPRESSIBILITY_ENDPOINT_PATH,
    ROCKSAMPLE_ENDPOINT_PATH,
    ROCKSAMPLE_RECORD,
    ROCKSAMPLEANALYSIS_ENDPOINT_PATH,
    ROCKSAMPLEANALYSIS_RECORD,
    SAMPLESANALYSIS_RECORD_V1,
    SAMPLESANALYSIS_RECORD_WITHOUT_PARENT_V1,
    SLIMTUBETEST_ENDPOINT_PATH,
    SLIMTUBETEST_RECORD,
    STO_ENDPOINT_PATH,
    STO_RECORD,
    STORAGE_SERVICE_200_RESPONSE,
    STORAGE_SERVICE_200_VERSIONS_RESPONSE,
    SWELLING_ENDPOINT_PATH,
    SWELLING_RECORD,
    TEST_CCE_ID,
    TEST_COMPOSITIONALANALYSIS_ID,
    TEST_CORING_ID,
    TEST_CVD_ID,
    TEST_DL_ID,
    TEST_HEADERS,
    TEST_HEADERS_NO_AUTH,
    TEST_INTERFACIAL_TENSION_ID,
    TEST_MCM_ID,
    TEST_MSS_ID,
    TEST_PVT_ID,
    TEST_ROCKSAMPLE_ID,
    TEST_ROCKSAMPLEANALYSIS_ID,
    TEST_SAMPLESANALYSESREPORT_ID,
    TEST_SAMPLESANALYSIS_ID,
    TEST_SERVER,
    TEST_SLIMTUBETEST_ID,
    TEST_STO_ID,
    TEST_SWELLING_ID,
    TEST_TRANSPORT_ID,
    TEST_VLE_ID,
    TEST_WATERANALYSIS_ID,
    TEST_WRONG_ID,
    TRANSPORT_ENDPOINT_PATH,
    TRANSPORT_RECORD,
    VLE_ENDPOINT_PATH,
    VLE_RECORD,
    WATER_GAS_RELATIVE_PERMEABILITY_ENDPOINT_PATH,
    WATERANALYSIS_ENDPOINT_PATH,
    WATERANALYSIS_RECORD,
    build_storage_service_response_200,
)

storage_record_service_mock = create_autospec(StorageService, spec_set=True, instance=True)


async def query_records_mock(_):
    record_data = PVT_RECORD.dict(exclude_none=True)
    return {
        "records": [
            record_data,
        ],
        "invalidRecords": [],
        "retryRecords": [],
    }


async def mock_get_async_storage_service():
    yield storage_record_service_mock


@contextmanager
def storage_override():
    overrides = {
        get_async_storage_service: mock_get_async_storage_service,
    }
    with dependencies.DependencyOverrider(app, overrides) as mock_dependencies:
        yield mock_dependencies


@pytest.fixture
def with_patched_storage_raises_404(storage_method):
    """Patch storage to raise 404."""
    class Response(object):
        status_code = status.HTTP_404_NOT_FOUND
        content = b"test reason"
        text = "test txt"

    with patch.object(
        storage_record_service_mock,
        storage_method,
        side_effect=HTTPStatusError("test", response=Response(), request=None),
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
    class Response(object):
        status_code = api_status_code
        content = b"test reason"
        text = "test txt"

    with patch.object(
        storage_record_service_mock,
        storage_method,
        side_effect=HTTPStatusError("test", response=Response(), request=None),
    ):
        with patch.object(
            storage_record_service_mock,
            "query_records",
            side_effect=HTTPStatusError("test", response=Response(), request=None),
        ):
            yield


@pytest.fixture
def with_patched_storage_get_success_200(storage_method, osdu_record):
    """Patch storage to 200 success."""
    with patch.object(storage_record_service_mock, storage_method, return_value=osdu_record):
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


@pytest.fixture
def with_patched_storage_query_pvt_200():
    """Patch storage to return pvt record."""
    with patch.object(
        storage_record_service_mock,
        "query_records",
        return_value=PVT_QUERY_STORAGE_SERVICE_200_RESPONSE,
    ):
        yield


@pytest.fixture
def with_patched_storage_query_pvt_invalid_200():
    """Patch storage to return invalid pvt record."""
    record = copy.deepcopy(PVT_QUERY_STORAGE_SERVICE_200_RESPONSE["records"][0])
    invalid_pvt_tests_value = [test_id for test_id in record["data"]["PVTTests"].values()]
    record["data"]["PVTTests"] = invalid_pvt_tests_value
    return_value = {
        "records": [
            record,
        ],
        "invalidRecords": [],
        "retryRecords": [],
    }
    with patch.object(
        storage_record_service_mock,
        "query_records",
        return_value=return_value,
    ):
        yield


@pytest.fixture()
def with_patched_storage_samplesanalysis_missing_parent():
    """Patch storage to return missing SamplesAnalysesReport record ID."""
    return_value = {
        "records": [],
        "invalidRecords": [TEST_SAMPLESANALYSESREPORT_ID],
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
        "records": [SAMPLESANALYSIS_RECORD_V1],
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
    "storage_method,path,record_id", [
        ("get_record", f"{API_VERSION}/rocksamples", TEST_ROCKSAMPLE_ID),
        ("get_record", f"{API_VERSION}/coringreports", TEST_CORING_ID),
        ("get_record", f"{API_VERSION}/pvtreports", TEST_PVT_ID),
        ("get_record", f"{API_VERSION}/rocksampleanalyses", TEST_ROCKSAMPLEANALYSIS_ID),
        ("get_record", f"{API_VERSION}/ccereports", TEST_CCE_ID),
        ("get_record", f"{API_VERSION}/difflibreports", TEST_DL_ID),
        ("get_record", f"{API_VERSION}/transporttests", TEST_TRANSPORT_ID),
        ("get_record", f"{API_VERSION}/compositionalanalysisreports", TEST_COMPOSITIONALANALYSIS_ID),
        ("get_record", f"{API_VERSION}/multistageseparatortests", TEST_MSS_ID),
        ("get_record", f"{API_VERSION}/swellingtests", TEST_SWELLING_ID),
        ("get_record", f"{API_VERSION}/constantvolumedepletiontests", TEST_CVD_ID),
        ("get_record", f"{API_VERSION}/wateranalysisreports", TEST_WATERANALYSIS_ID),
        ("get_record", f"{API_VERSION}/stocktankoilanalysisreports", TEST_STO_ID),
        ("get_record", f"{API_VERSION}/interfacialtensiontests", TEST_INTERFACIAL_TENSION_ID),
        ("get_record", f"{API_VERSION}/vaporliquidequilibriumtests", TEST_VLE_ID),
        ("get_record", f"{API_VERSION}/multiplecontactmiscibilitytests", TEST_MCM_ID),
        ("get_record", f"{API_VERSION}/slimtubetests", TEST_SLIMTUBETEST_ID),
        ("get_record", f"{API_VERSION}/samplesanalysesreport", storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID),
        ("get_record", f"{API_VERSION}/capillarypressuretests", TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/relativepermeabilitytests", TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/fractionationtests", TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/extractiontests", TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/physicalchemistrytests", TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/electricalproperties", TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/rockcompressibilities", TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/watergasrelativepermeabilities", TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/formationresistivityindexes", TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION_V2}/samplesanalysesreport", storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID),
        ("get_record", f"{API_VERSION_V2}/samplesanalysis", storage_mock_objects.TEST_SAMPLESANALYSIS_ID),
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
    "storage_method,path,record_id", [
        ("get_record", f"{API_VERSION}/rocksamples", TEST_ROCKSAMPLE_ID),
        ("get_record", f"{API_VERSION}/coringreports", TEST_CORING_ID),
        ("get_record", f"{API_VERSION}/pvtreports", TEST_PVT_ID),
        ("get_record", f"{API_VERSION}/rocksampleanalyses", TEST_ROCKSAMPLEANALYSIS_ID),
        ("get_record", f"{API_VERSION}/ccereports", TEST_CCE_ID),
        ("get_record", f"{API_VERSION}/difflibreports", TEST_DL_ID),
        ("get_record", f"{API_VERSION}/transporttests", TEST_TRANSPORT_ID),
        ("get_record", f"{API_VERSION}/compositionalanalysisreports", TEST_COMPOSITIONALANALYSIS_ID),
        ("get_record", f"{API_VERSION}/multistageseparatortests", TEST_MSS_ID),
        ("get_record", f"{API_VERSION}/swellingtests", TEST_SWELLING_ID),
        ("get_record", f"{API_VERSION}/constantvolumedepletiontests", TEST_CVD_ID),
        ("get_record", f"{API_VERSION}/wateranalysisreports", TEST_WATERANALYSIS_ID),
        ("get_record", f"{API_VERSION}/stocktankoilanalysisreports", TEST_STO_ID),
        ("get_record", f"{API_VERSION}/interfacialtensiontests", TEST_INTERFACIAL_TENSION_ID),
        ("get_record", f"{API_VERSION}/vaporliquidequilibriumtests", TEST_VLE_ID),
        ("get_record", f"{API_VERSION}/multiplecontactmiscibilitytests", TEST_MCM_ID),
        ("get_record", f"{API_VERSION}/slimtubetests", TEST_SLIMTUBETEST_ID),
        ("get_record", f"{API_VERSION}/samplesanalysesreport", storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID),
        ("get_record", f"{API_VERSION}/capillarypressuretests", TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/relativepermeabilitytests", TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/fractionationtests", TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/extractiontests", TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/physicalchemistrytests", TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/electricalproperties", TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/rockcompressibilities", TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/watergasrelativepermeabilities", TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/formationresistivityindexes", TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION_V2}/samplesanalysesreport", storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID),
        ("get_record", f"{API_VERSION_V2}/samplesanalysis", storage_mock_objects.TEST_SAMPLESANALYSIS_ID),
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
    "storage_method,path,record_id", [
        ("get_record_versions", f"{API_VERSION}/rocksamples", TEST_ROCKSAMPLE_ID),
        ("get_record_versions", f"{API_VERSION}/coringreports", TEST_CORING_ID),
        ("get_record_versions", f"{API_VERSION}/pvtreports", TEST_PVT_ID),
        ("get_record_versions", f"{API_VERSION}/rocksampleanalyses", TEST_ROCKSAMPLEANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/ccereports", TEST_CCE_ID),
        ("get_record_versions", f"{API_VERSION}/difflibreports", TEST_DL_ID),
        ("get_record_versions", f"{API_VERSION}/transporttests", TEST_TRANSPORT_ID),
        ("get_record_versions", f"{API_VERSION}/compositionalanalysisreports", TEST_COMPOSITIONALANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/multistageseparatortests", TEST_MSS_ID),
        ("get_record_versions", f"{API_VERSION}/swellingtests", TEST_SWELLING_ID),
        ("get_record_versions", f"{API_VERSION}/constantvolumedepletiontests", TEST_CVD_ID),
        ("get_record_versions", f"{API_VERSION}/wateranalysisreports", TEST_WATERANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/stocktankoilanalysisreports", TEST_STO_ID),
        ("get_record_versions", f"{API_VERSION}/interfacialtensiontests", TEST_INTERFACIAL_TENSION_ID),
        ("get_record_versions", f"{API_VERSION}/vaporliquidequilibriumtests", TEST_VLE_ID),
        ("get_record_versions", f"{API_VERSION}/multiplecontactmiscibilitytests", TEST_MCM_ID),
        ("get_record_versions", f"{API_VERSION}/slimtubetests", TEST_SLIMTUBETEST_ID),
        (
            "get_record_versions", f"{API_VERSION}/samplesanalysesreport",
            storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID,
        ),
        ("get_record_versions", f"{API_VERSION}/capillarypressuretests", TEST_SAMPLESANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/relativepermeabilitytests", TEST_SAMPLESANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/fractionationtests", TEST_SAMPLESANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/extractiontests", TEST_SAMPLESANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/physicalchemistrytests", TEST_SAMPLESANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/electricalproperties", TEST_SAMPLESANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/rockcompressibilities", TEST_SAMPLESANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/watergasrelativepermeabilities", TEST_SAMPLESANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/formationresistivityindexes", TEST_SAMPLESANALYSIS_ID),
        (
            "get_record_versions", f"{API_VERSION_V2}/samplesanalysesreport",
            storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID,
        ),
        ("get_record_versions", f"{API_VERSION_V2}/samplesanalysis", storage_mock_objects.TEST_SAMPLESANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION_V2}/masterdata", storage_mock_objects.TEST_SAMPLE_ID),
    ],
)
async def test_get_record_versions_not_found(
    storage_method, path, record_id,
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
    "storage_method,path,record_id", [
        ("soft_delete_record", f"{API_VERSION}/rocksamples", TEST_ROCKSAMPLE_ID),
        ("soft_delete_record", f"{API_VERSION}/coringreports", TEST_CORING_ID),
        ("soft_delete_record", f"{API_VERSION}/pvtreports", TEST_PVT_ID),
        ("soft_delete_record", f"{API_VERSION}/rocksampleanalyses", TEST_ROCKSAMPLEANALYSIS_ID),
        ("soft_delete_record", f"{API_VERSION}/ccereports", TEST_CCE_ID),
        ("soft_delete_record", f"{API_VERSION}/difflibreports", TEST_DL_ID),
        ("soft_delete_record", f"{API_VERSION}/transporttests", TEST_TRANSPORT_ID),
        ("soft_delete_record", f"{API_VERSION}/compositionalanalysisreports", TEST_COMPOSITIONALANALYSIS_ID),
        ("soft_delete_record", f"{API_VERSION}/multistageseparatortests", TEST_MSS_ID),
        ("soft_delete_record", f"{API_VERSION}/swellingtests", TEST_SWELLING_ID),
        ("soft_delete_record", f"{API_VERSION}/constantvolumedepletiontests", TEST_CVD_ID),
        ("soft_delete_record", f"{API_VERSION}/wateranalysisreports", TEST_WATERANALYSIS_ID),
        ("soft_delete_record", f"{API_VERSION}/stocktankoilanalysisreports", TEST_STO_ID),
        ("soft_delete_record", f"{API_VERSION}/interfacialtensiontests", TEST_INTERFACIAL_TENSION_ID),
        ("soft_delete_record", f"{API_VERSION}/vaporliquidequilibriumtests", TEST_VLE_ID),
        ("soft_delete_record", f"{API_VERSION}/multiplecontactmiscibilitytests", TEST_MCM_ID),
        ("soft_delete_record", f"{API_VERSION}/slimtubetests", TEST_SLIMTUBETEST_ID),
        (
            "soft_delete_record", f"{API_VERSION}/samplesanalysesreport",
            storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID,
        ),
        ("soft_delete_record", f"{API_VERSION}/capillarypressuretests", TEST_SAMPLESANALYSIS_ID),
        ("soft_delete_record", f"{API_VERSION}/relativepermeabilitytests", TEST_SAMPLESANALYSIS_ID),
        ("soft_delete_record", f"{API_VERSION}/fractionationtests", TEST_SAMPLESANALYSIS_ID),
        ("soft_delete_record", f"{API_VERSION}/extractiontests", TEST_SAMPLESANALYSIS_ID),
        ("soft_delete_record", f"{API_VERSION}/physicalchemistrytests", TEST_SAMPLESANALYSIS_ID),
        ("soft_delete_record", f"{API_VERSION}/electricalproperties", TEST_SAMPLESANALYSIS_ID),
        ("soft_delete_record", f"{API_VERSION}/rockcompressibilities", TEST_SAMPLESANALYSIS_ID),
        ("soft_delete_record", f"{API_VERSION}/watergasrelativepermeabilities", TEST_SAMPLESANALYSIS_ID),
        ("soft_delete_record", f"{API_VERSION}/formationresistivityindexes", TEST_SAMPLESANALYSIS_ID),
        (
            "soft_delete_record", f"{API_VERSION_V2}/samplesanalysesreport",
            storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID,
        ),
        ("soft_delete_record", f"{API_VERSION_V2}/samplesanalysis", storage_mock_objects.TEST_SAMPLESANALYSIS_ID),
        ("soft_delete_record", f"{API_VERSION_V2}/masterdata", storage_mock_objects.TEST_SAMPLE_ID),
    ],
)
async def test_delete_record_not_found(
    storage_method, path, record_id,
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
    "path", [
        (f"{API_VERSION}/rocksamples"),
        (f"{API_VERSION}/coringreports"),
        (f"{API_VERSION}/pvtreports"),
        (f"{API_VERSION}/rocksampleanalyses"),
        (f"{API_VERSION}/ccereports"),
        (f"{API_VERSION}/difflibreports"),
        (f"{API_VERSION}/transporttests"),
        (f"{API_VERSION}/compositionalanalysisreports"),
        (f"{API_VERSION}/multistageseparatortests"),
        (f"{API_VERSION}/swellingtests"),
        (f"{API_VERSION}/constantvolumedepletiontests"),
        (f"{API_VERSION}/wateranalysisreports"),
        (f"{API_VERSION}/stocktankoilanalysisreports"),
        (f"{API_VERSION}/interfacialtensiontests"),
        (f"{API_VERSION}/vaporliquidequilibriumtests"),
        (f"{API_VERSION}/multiplecontactmiscibilitytests"),
        (f"{API_VERSION}/slimtubetests"),
        (f"{API_VERSION}/samplesanalysesreport"),
        (f"{API_VERSION}/capillarypressuretests"),
        (f"{API_VERSION}/relativepermeabilitytests"),
        (f"{API_VERSION}/fractionationtests"),
        (f"{API_VERSION}/extractiontests"),
        (f"{API_VERSION}/physicalchemistrytests"),
        (f"{API_VERSION}/electricalproperties"),
        (f"{API_VERSION}/rockcompressibilities"),
        (f"{API_VERSION}/watergasrelativepermeabilities"),
        (f"{API_VERSION}/formationresistivityindexes"),
        (f"{API_VERSION_V2}/samplesanalysesreport"),
        (f"{API_VERSION_V2}/samplesanalysis"),
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
    assert response_json["code"] == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert storage_mock_objects.EXPECTED_422_NO_KIND_RESPONSE == response_json


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path", [
        (f"{API_VERSION}/rocksamples"),
        (f"{API_VERSION}/coringreports"),
        (f"{API_VERSION}/pvtreports"),
        (f"{API_VERSION}/rocksampleanalyses"),
        (f"{API_VERSION}/ccereports"),
        (f"{API_VERSION}/difflibreports"),
        (f"{API_VERSION}/transporttests"),
        (f"{API_VERSION}/compositionalanalysisreports"),
        (f"{API_VERSION}/multistageseparatortests"),
        (f"{API_VERSION}/swellingtests"),
        (f"{API_VERSION}/constantvolumedepletiontests"),
        (f"{API_VERSION}/wateranalysisreports"),
        (f"{API_VERSION}/stocktankoilanalysisreports"),
        (f"{API_VERSION}/interfacialtensiontests"),
        (f"{API_VERSION}/vaporliquidequilibriumtests"),
        (f"{API_VERSION}/multiplecontactmiscibilitytests"),
        (f"{API_VERSION}/slimtubetests"),
        (f"{API_VERSION}/samplesanalysesreport"),
        (f"{API_VERSION}/capillarypressuretests"),
        (f"{API_VERSION}/relativepermeabilitytests"),
        (f"{API_VERSION}/fractionationtests"),
        (f"{API_VERSION}/extractiontests"),
        (f"{API_VERSION}/physicalchemistrytests"),
        (f"{API_VERSION}/electricalproperties"),
        (f"{API_VERSION}/rockcompressibilities"),
        (f"{API_VERSION}/watergasrelativepermeabilities"),
        (f"{API_VERSION}/formationresistivityindexes"),
        (f"{API_VERSION_V2}/samplesanalysesreport"),
        (f"{API_VERSION_V2}/samplesanalysis"),
        (f"{API_VERSION_V2}/masterdata"),
    ],
)
async def test_post_record_invalid_payload_type(path):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(f"/api/os-rafs-ddms/{path}", headers=TEST_HEADERS, json={})

    assert response.json()["code"] == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json()["errors"][0] == EXPECTED_422_TYPER_ERROR_LIST


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,osdu_record,field",
    [
        (f"{API_VERSION}/rocksamples", ROCKSAMPLE_RECORD, "WellboreID"),
        (f"{API_VERSION}/coringreports", CORING_RECORD, "WellboreID"),
        (f"{API_VERSION}/pvtreports", PVT_RECORD, "FluidSampleID"),
        (f"{API_VERSION}/rocksampleanalyses", ROCKSAMPLEANALYSIS_RECORD, "WellboreID"),
        (f"{API_VERSION}/ccereports", CCE_RECORD, "FluidSampleID"),
        (f"{API_VERSION}/difflibreports", DL_RECORD, "FluidSampleID"),
        (f"{API_VERSION}/transporttests", TRANSPORT_RECORD, "FluidSampleID"),
        (f"{API_VERSION}/compositionalanalysisreports", COMPOSITIONALANALYSIS_RECORD, "FluidSampleID"),
        (f"{API_VERSION}/multistageseparatortests", MULTISTAGESEPARATOR_RECORD, "FluidSampleID"),
        (f"{API_VERSION}/swellingtests", SWELLING_RECORD, "FluidSampleID"),
        (f"{API_VERSION}/constantvolumedepletiontests", CVD_RECORD, "FluidSampleID"),
        (f"{API_VERSION}/wateranalysisreports", WATERANALYSIS_RECORD, "FluidSampleID"),
        (f"{API_VERSION}/stocktankoilanalysisreports", STO_RECORD, "FluidSampleID"),
        (f"{API_VERSION}/interfacialtensiontests", INTERFACIAL_TENSION_RECORD, "FluidSampleID"),
        (f"{API_VERSION}/vaporliquidequilibriumtests", VLE_RECORD, "FluidSampleID"),
        (f"{API_VERSION}/multiplecontactmiscibilitytests", MCM_RECORD, "FluidSampleID"),
        (f"{API_VERSION}/slimtubetests", SLIMTUBETEST_RECORD, "FluidSampleID"),
        (f"{API_VERSION}/samplesanalysesreport", storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V1, "DocumentTypeID"),
        (f"{API_VERSION}/capillarypressuretests", SAMPLESANALYSIS_RECORD_V1, "DepthShiftsID"),
        (f"{API_VERSION}/relativepermeabilitytests", SAMPLESANALYSIS_RECORD_V1, "DepthShiftsID"),
        (f"{API_VERSION}/fractionationtests", SAMPLESANALYSIS_RECORD_V1, "DepthShiftsID"),
        (f"{API_VERSION}/extractiontests", SAMPLESANALYSIS_RECORD_V1, "DepthShiftsID"),
        (f"{API_VERSION}/physicalchemistrytests", SAMPLESANALYSIS_RECORD_V1, "DepthShiftsID"),
        (f"{API_VERSION}/electricalproperties", SAMPLESANALYSIS_RECORD_V1, "DepthShiftsID"),
        (f"{API_VERSION}/rockcompressibilities", SAMPLESANALYSIS_RECORD_V1, "DepthShiftsID"),
        (f"{API_VERSION}/watergasrelativepermeabilities", SAMPLESANALYSIS_RECORD_V1, "DepthShiftsID"),
        (f"{API_VERSION}/formationresistivityindexes", SAMPLESANALYSIS_RECORD_V1, "DepthShiftsID"),
        (f"{API_VERSION_V2}/samplesanalysesreport", storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V2, "DocumentTypeID"),
        (f"{API_VERSION_V2}/samplesanalysis", storage_mock_objects.SAMPLESANALYSIS_RECORD_V2, "ResourceHomeRegionID"),
        (
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_RECORD, "ResourceHomeRegionID",
        ),
        (
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_ACQUISITION_JOB_RECORD, "ResourceHomeRegionID",
        ),
        (
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CHAIN_OF_CUSTODY_EVENT_RECORD, "ResourceHomeRegionID",
        ),
        (
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CONTAINER_RECORD, "ResourceHomeRegionID",
        ),
        (
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.GENERIC_FACILITY_RECORD, "ResourceHomeRegionID",
        ),
        (
            f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.GENERIC_SITE_RECORD, "ResourceHomeRegionID",
        ),
    ],
)
async def test_post_record_invalid_field_type(path, osdu_record, field):
    osdu_record_wrong_field_type = osdu_record.dict()
    osdu_record_wrong_field_type.update({"data": {field: "wrong_pattern"}})

    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                f"/api/os-rafs-ddms/{path}",
                headers=TEST_HEADERS,
                json=[osdu_record_wrong_field_type],
            )

    assert response.json()["code"] == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert field in response.json()["reason"]
    assert all([s in response.json()["reason"] for s in EXPECTED_422_WRONG_PATTERN])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_method,path,osdu_record",
    [
        ("upsert_records", f"{API_VERSION}/rocksamples", ROCKSAMPLE_RECORD),
        ("upsert_records", f"{API_VERSION}/coringreports", CORING_RECORD),
        ("upsert_records", f"{API_VERSION}/pvtreports", PVT_RECORD),
        ("upsert_records", f"{API_VERSION}/rocksampleanalyses", ROCKSAMPLEANALYSIS_RECORD),
        (
            "upsert_records", f"{API_VERSION}/samplesanalysesreport",
            storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V1,
        ),
        (
            "upsert_records", f"{API_VERSION_V2}/samplesanalysesreport",
            storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V2,
        ),
        ("upsert_records", f"{API_VERSION_V2}/samplesanalysis", storage_mock_objects.SAMPLESANALYSIS_RECORD_V2),
        (
            "upsert_records", f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_RECORD,
        ),
        (
            "upsert_records", f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_ACQUISITION_JOB_RECORD,
        ),
        (
            "upsert_records", f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CHAIN_OF_CUSTODY_EVENT_RECORD,
        ),
        (
            "upsert_records", f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CONTAINER_RECORD,
        ),
        (
            "upsert_records", f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.GENERIC_FACILITY_RECORD,
        ),
        (
            "upsert_records", f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.GENERIC_SITE_RECORD,
        ),
    ],
)
async def test_post_record_success(
    storage_method, path, osdu_record,
    with_patched_storage_created_200,
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
    "path,osdu_record",
    [
        (
            "ccereports",
            CCE_RECORD,
        ),
        (
            "difflibreports",
            DL_RECORD,
        ),
        (
            "transporttests",
            TRANSPORT_RECORD,
        ),
        (
            "compositionalanalysisreports",
            COMPOSITIONALANALYSIS_RECORD,
        ),
        (
            "multistageseparatortests",
            MULTISTAGESEPARATOR_RECORD,
        ),
        (
            "swellingtests",
            SWELLING_RECORD,
        ),
        (
            "constantvolumedepletiontests",
            CVD_RECORD,
        ),
        (
            "wateranalysisreports",
            WATERANALYSIS_RECORD,
        ),
        (
            "stocktankoilanalysisreports",
            STO_RECORD,
        ),
        (
            "interfacialtensiontests",
            INTERFACIAL_TENSION_RECORD,
        ),
        (
            "vaporliquidequilibriumtests",
            VLE_RECORD,
        ),
        (
            "multiplecontactmiscibilitytests",
            MCM_RECORD,
        ),
        (
            "slimtubetests",
            SLIMTUBETEST_RECORD,
        ),
    ],
)
async def test_post_record_with_invalid_pvt_parent(
    path,
    osdu_record,
    with_patched_storage_query_pvt_invalid_200,
):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                f"/api/os-rafs-ddms/{API_VERSION}/{path}",
                headers=TEST_HEADERS,
                json=[osdu_record.dict(exclude_none=True)],
            )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    result_json = response.json()
    assert result_json == EXPECTED_400_RESPONSE_ON_INVALID_PARENT_PVT


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,osdu_record,created_responses,get_response",
    [
        (
            "ccereports",
            CCE_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_CCE_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_CCE_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "difflibreports",
            DL_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_DL_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_DL_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "transporttests",
            TRANSPORT_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_TRANSPORT_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_TRANSPORT_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "compositionalanalysisreports",
            COMPOSITIONALANALYSIS_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_COMPOSITIONALANALYSIS_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_COMPOSITIONALANALYSIS_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "swellingtests",
            SWELLING_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_SWELLING_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_SWELLING_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "multistageseparatortests",
            MULTISTAGESEPARATOR_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_MSS_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_MSS_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "constantvolumedepletiontests",
            CVD_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_CVD_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_CVD_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "wateranalysisreports",
            WATERANALYSIS_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_WATERANALYSIS_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_WATERANALYSIS_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "stocktankoilanalysisreports",
            STO_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_STO_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_STO_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "interfacialtensiontests",
            INTERFACIAL_TENSION_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_INTERFACIAL_TENSION_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_INTERFACIAL_TENSION_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "vaporliquidequilibriumtests",
            VLE_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_VLE_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_VLE_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "multiplecontactmiscibilitytests",
            MCM_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_MCM_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_MCM_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "slimtubetests",
            SLIMTUBETEST_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_SLIMTUBETEST_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_SLIMTUBETEST_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
    ],
)
async def test_post_record_success_update_pvt_parent(
    path,
    osdu_record,
    created_responses,
    get_response,
    with_patched_storage_pvt_link_200,
    with_patched_storage_query_pvt_200,
):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                f"/api/os-rafs-ddms/{API_VERSION}/{path}",
                headers=TEST_HEADERS,
                json=[osdu_record.dict(exclude_none=True)],
            )
            result_json = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert result_json["recordCount"] == EXPECTED_200_CREATED_PVT_UPDATED_RESPONSE["recordCount"]
    assert set(result_json["recordIdVersions"]) == {f"{osdu_record.id}:1", f"{osdu_record.data.PVTReportID}1"}
    assert result_json["skippedRecordCount"] == EXPECTED_200_CREATED_PVT_UPDATED_RESPONSE["skippedRecordCount"]
    assert storage_record_service_mock.upsert_records.call_args_list[0] == call([osdu_record.dict(exclude_none=True)])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,osdu_record",
    [
        (
            f"{API_VERSION}/capillarypressuretests",
            SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            f"{API_VERSION}/relativepermeabilitytests",
            SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            f"{API_VERSION}/fractionationtests",
            SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            f"{API_VERSION}/extractiontests",
            SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            f"{API_VERSION}/physicalchemistrytests",
            SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            f"{API_VERSION}/electricalproperties",
            SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            f"{API_VERSION}/rockcompressibilities",
            SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            f"{API_VERSION}/watergasrelativepermeabilities",
            SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            f"{API_VERSION}/formationresistivityindexes",
            SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            f"{API_VERSION_V2}/samplesanalysis",
            storage_mock_objects.SAMPLESANALYSIS_RECORD_V2,
        ),
    ],
)
async def test_post_samplesanalysis_with_missing_parent(
    path,
    osdu_record,
    with_patched_storage_samplesanalysis_missing_parent,
):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                f"/api/os-rafs-ddms/{path}",
                headers=TEST_HEADERS,
                json=[osdu_record.dict(exclude_none=True)],
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    result_json = response.json()
    assert result_json == EXPECTED_422_RESPONSE_ON_MISSING_SAMPLESANALYSESREPORT


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_method,path,osdu_record",
    [
        (
            "upsert_records",
            f"{API_VERSION}/capillarypressuretests",
            SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            "upsert_records",
            f"{API_VERSION}/capillarypressuretests",
            SAMPLESANALYSIS_RECORD_WITHOUT_PARENT_V1,
        ),
        (
            "upsert_records",
            f"{API_VERSION}/relativepermeabilitytests",
            SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            "upsert_records",
            f"{API_VERSION}/relativepermeabilitytests",
            SAMPLESANALYSIS_RECORD_WITHOUT_PARENT_V1,
        ),
        (
            "upsert_records",
            f"{API_VERSION}/fractionationtests",
            SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            "upsert_records",
            f"{API_VERSION}/fractionationtests",
            SAMPLESANALYSIS_RECORD_WITHOUT_PARENT_V1,
        ),
        (
            "upsert_records",
            f"{API_VERSION}/physicalchemistrytests",
            SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            "upsert_records",
            f"{API_VERSION}/physicalchemistrytests",
            SAMPLESANALYSIS_RECORD_WITHOUT_PARENT_V1,
        ),
        (
            "upsert_records",
            f"{API_VERSION}/extractiontests",
            SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            "upsert_records",
            f"{API_VERSION}/extractiontests",
            SAMPLESANALYSIS_RECORD_WITHOUT_PARENT_V1,
        ),
        (
            "upsert_records",
            f"{API_VERSION}/electricalproperties",
            SAMPLESANALYSIS_RECORD_WITHOUT_PARENT_V1,
        ),
        (
            "upsert_records",
            f"{API_VERSION}/rockcompressibilities",
            SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            "upsert_records",
            f"{API_VERSION}/rockcompressibilities",
            SAMPLESANALYSIS_RECORD_WITHOUT_PARENT_V1,
        ),
        (
            "upsert_records",
            f"{API_VERSION}/watergasrelativepermeabilities",
            SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            "upsert_records",
            f"{API_VERSION}/watergasrelativepermeabilities",
            SAMPLESANALYSIS_RECORD_WITHOUT_PARENT_V1,
        ),
        (
            "upsert_records",
            f"{API_VERSION}/formationresistivityindexes",
            SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            "upsert_records",
            f"{API_VERSION}/formationresistivityindexes",
            SAMPLESANALYSIS_RECORD_WITHOUT_PARENT_V1,
        ),
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
    "storage_method,path,osdu_record",
    [
        ("upsert_records", f"{API_VERSION}/rocksamples", ROCKSAMPLE_RECORD),
        ("upsert_records", f"{API_VERSION}/coringreports", CORING_RECORD),
        ("upsert_records", f"{API_VERSION}/pvtreports", PVT_RECORD),
        ("upsert_records", f"{API_VERSION}/rocksampleanalyses", ROCKSAMPLEANALYSIS_RECORD),
        (
            "upsert_records", f"{API_VERSION}/samplesanalysesreport",
            storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V1,
        ),
        (
            "upsert_records", f"{API_VERSION_V2}/samplesanalysesreport",
            storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V2,
        ),
        ("upsert_records", f"{API_VERSION_V2}/samplesanalysis", storage_mock_objects.SAMPLESANALYSIS_RECORD_V2),
        (
            "upsert_records", f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_RECORD,
        ),
        (
            "upsert_records", f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_ACQUISITION_JOB_RECORD,
        ),
        (
            "upsert_records", f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CHAIN_OF_CUSTODY_EVENT_RECORD,
        ),
        (
            "upsert_records", f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CONTAINER_RECORD,
        ),
        (
            "upsert_records", f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.GENERIC_FACILITY_RECORD,
        ),
        (
            "upsert_records", f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.GENERIC_SITE_RECORD,
        ),
    ],
)
async def test_post_record_no_id(
    storage_method,
    path,
    osdu_record,
    with_patched_storage_created_200,
):
    osdu_record_json = osdu_record.dict(
        exclude={"id"},
        exclude_none=True,
    )
    with storage_override():
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
    "path,osdu_record,created_responses,get_response",
    [
        (
            "ccereports",
            CCE_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_CCE_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_CCE_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "difflibreports",
            DL_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_DL_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_DL_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "transporttests",
            TRANSPORT_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_TRANSPORT_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_TRANSPORT_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "compositionalanalysisreports",
            COMPOSITIONALANALYSIS_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_COMPOSITIONALANALYSIS_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_COMPOSITIONALANALYSIS_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "swellingtests",
            SWELLING_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_SWELLING_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_SWELLING_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "multistageseparatortests",
            MULTISTAGESEPARATOR_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_MSS_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_MSS_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "constantvolumedepletiontests",
            CVD_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_CVD_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_CVD_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "wateranalysisreports",
            WATERANALYSIS_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_WATERANALYSIS_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_WATERANALYSIS_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "stocktankoilanalysisreports",
            STO_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_STO_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_STO_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "interfacialtensiontests",
            INTERFACIAL_TENSION_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_INTERFACIAL_TENSION_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_INTERFACIAL_TENSION_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "vaporliquidequilibriumtests",
            VLE_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_VLE_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_VLE_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "multiplecontactmiscibilitytests",
            MCM_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_MCM_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_MCM_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
        (
            "slimtubetests",
            SLIMTUBETEST_RECORD,
            [
                build_storage_service_response_200(
                    record_count=1,
                    record_ids=[TEST_SLIMTUBETEST_ID],
                    skipped_record_ids=[],
                    record_id_versions=[f"{TEST_SLIMTUBETEST_ID}:1"],
                ),
                PVT_STORAGE_SERVICE_200_RESPONSE,
            ],
            PVT_RECORD.dict(exclude_none=True),
        ),
    ],
)
async def test_post_record_with_linking_no_id(
    path,
    osdu_record,
    created_responses,
    get_response,
    with_patched_storage_pvt_link_200,
    with_patched_storage_query_pvt_200,
):
    osdu_record_json = osdu_record.dict(
        exclude={"id"},
        exclude_none=True,
    )
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.post(
                f"/api/os-rafs-ddms/{API_VERSION}/{path}",
                headers=TEST_HEADERS,
                json=[osdu_record_json],
            )
            result_json = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert result_json["recordCount"] == EXPECTED_200_CREATED_PVT_UPDATED_RESPONSE["recordCount"]
    assert set(result_json["recordIdVersions"]) == {f"{osdu_record.id}:1", f"{osdu_record.data.PVTReportID}1"}
    assert result_json["skippedRecordCount"] == EXPECTED_200_CREATED_PVT_UPDATED_RESPONSE["skippedRecordCount"]
    assert storage_record_service_mock.upsert_records.call_args_list[0] == call([osdu_record_json])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_method,path,osdu_record,record_id",
    [
        ("get_record", f"{API_VERSION}/rocksamples", ROCKSAMPLE_RECORD, TEST_ROCKSAMPLE_ID),
        ("get_record", f"{API_VERSION}/coringreports", CORING_RECORD, TEST_CORING_ID),
        ("get_record", f"{API_VERSION}/pvtreports", PVT_RECORD, TEST_PVT_ID),
        ("get_record", f"{API_VERSION}/rocksampleanalyses", ROCKSAMPLEANALYSIS_RECORD, TEST_ROCKSAMPLEANALYSIS_ID),
        ("get_record", f"{API_VERSION}/ccereports", CCE_RECORD, TEST_CCE_ID),
        ("get_record", f"{API_VERSION}/difflibreports", DL_RECORD, TEST_DL_ID),
        ("get_record", f"{API_VERSION}/transporttests", TRANSPORT_RECORD, TEST_TRANSPORT_ID),
        (
            "get_record", f"{API_VERSION}/compositionalanalysisreports",
            COMPOSITIONALANALYSIS_RECORD, TEST_COMPOSITIONALANALYSIS_ID,
        ),
        ("get_record", f"{API_VERSION}/multistageseparatortests", MULTISTAGESEPARATOR_RECORD, TEST_MSS_ID),
        ("get_record", f"{API_VERSION}/swellingtests", SWELLING_RECORD, TEST_SWELLING_ID),
        ("get_record", f"{API_VERSION}/constantvolumedepletiontests", CVD_RECORD, TEST_CVD_ID),
        ("get_record", f"{API_VERSION}/wateranalysisreports", WATERANALYSIS_RECORD, TEST_WATERANALYSIS_ID),
        ("get_record", f"{API_VERSION}/stocktankoilanalysisreports", STO_RECORD, TEST_STO_ID),
        (
            "get_record", f"{API_VERSION}/interfacialtensiontests",
            INTERFACIAL_TENSION_RECORD, TEST_INTERFACIAL_TENSION_ID,
        ),
        ("get_record", f"{API_VERSION}/vaporliquidequilibriumtests", VLE_RECORD, TEST_VLE_ID),
        ("get_record", f"{API_VERSION}/multiplecontactmiscibilitytests", MCM_RECORD, TEST_MCM_ID),
        ("get_record", f"{API_VERSION}/slimtubetests", SLIMTUBETEST_RECORD, TEST_SLIMTUBETEST_ID),
        (
            "get_record", f"{API_VERSION}/samplesanalysesreport", storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V1,
            storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID,
        ),
        ("get_record", f"{API_VERSION}/capillarypressuretests", SAMPLESANALYSIS_RECORD_V1, TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/relativepermeabilitytests", SAMPLESANALYSIS_RECORD_V1, TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/fractionationtests", SAMPLESANALYSIS_RECORD_V1, TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/extractiontests", SAMPLESANALYSIS_RECORD_V1, TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/physicalchemistrytests", SAMPLESANALYSIS_RECORD_V1, TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/electricalproperties", SAMPLESANALYSIS_RECORD_V1, TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/rockcompressibilities", SAMPLESANALYSIS_RECORD_V1, TEST_SAMPLESANALYSIS_ID),
        (
            "get_record", f"{API_VERSION}/watergasrelativepermeabilities",
            SAMPLESANALYSIS_RECORD_V1, TEST_SAMPLESANALYSIS_ID,
        ),
        (
            "get_record", f"{API_VERSION}/formationresistivityindexes",
            SAMPLESANALYSIS_RECORD_V1, TEST_SAMPLESANALYSIS_ID,
        ),
        (
            "get_record", f"{API_VERSION_V2}/samplesanalysesreport", storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V2,
            storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID,
        ),
        (
            "get_record", f"{API_VERSION_V2}/samplesanalysis", storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V2,
            storage_mock_objects.TEST_SAMPLESANALYSIS_ID,
        ),
        (
            "get_record", f"{API_VERSION_V2}/masterdata", storage_mock_objects.SAMPLE_RECORD,
            storage_mock_objects.TEST_SAMPLE_ID,
        ),
        (
            "get_record", f"{API_VERSION_V2}/masterdata", storage_mock_objects.SAMPLE_ACQUISITION_JOB_RECORD,
            storage_mock_objects.TEST_SAMPLE_ACQUISITION_JOB_ID,
        ),
        (
            "get_record", f"{API_VERSION_V2}/masterdata", storage_mock_objects.SAMPLE_CHAIN_OF_CUSTODY_EVENT_RECORD,
            storage_mock_objects.TEST_SAMPLE_CHAIN_OF_CUSTODY_EVENT_ID,
        ),
        (
            "get_record", f"{API_VERSION_V2}/masterdata", storage_mock_objects.SAMPLE_CONTAINER_RECORD,
            storage_mock_objects.TEST_SAMPLE_CONTAINER_ID,
        ),
        (
            "get_record", f"{API_VERSION_V2}/masterdata", storage_mock_objects.GENERIC_FACILITY_RECORD,
            storage_mock_objects.TEST_GENERIC_FACILITY_ID,
        ),
        (
            "get_record", f"{API_VERSION_V2}/masterdata", storage_mock_objects.GENERIC_SITE_RECORD,
            storage_mock_objects.TEST_GENERIC_SITE_ID,
        ),
    ],
)
async def test_get_record_success(
    storage_method, path, osdu_record, record_id,
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
        ("get_record", f"{API_VERSION}/rocksamples", ROCKSAMPLE_RECORD, TEST_ROCKSAMPLE_ID),
        ("get_record", f"{API_VERSION}/coringreports", CORING_RECORD, TEST_CORING_ID),
        ("get_record", f"{API_VERSION}/pvtreports", PVT_RECORD, TEST_PVT_ID),
        ("get_record", f"{API_VERSION}/rocksampleanalyses", ROCKSAMPLEANALYSIS_RECORD, TEST_ROCKSAMPLEANALYSIS_ID),
        ("get_record", f"{API_VERSION}/ccereports", CCE_RECORD, TEST_CCE_ID),
        ("get_record", f"{API_VERSION}/difflibreports", DL_RECORD, TEST_DL_ID),
        ("get_record", f"{API_VERSION}/transporttests", TRANSPORT_RECORD, TEST_TRANSPORT_ID),
        (
            "get_record", f"{API_VERSION}/compositionalanalysisreports",
            COMPOSITIONALANALYSIS_RECORD, TEST_COMPOSITIONALANALYSIS_ID,
        ),
        ("get_record", f"{API_VERSION}/multistageseparatortests", MULTISTAGESEPARATOR_RECORD, TEST_MSS_ID),
        ("get_record", f"{API_VERSION}/swellingtests", SWELLING_RECORD, TEST_SWELLING_ID),
        ("get_record", f"{API_VERSION}/constantvolumedepletiontests", CVD_RECORD, TEST_CVD_ID),
        ("get_record", f"{API_VERSION}/wateranalysisreports", WATERANALYSIS_RECORD, TEST_WATERANALYSIS_ID),
        ("get_record", f"{API_VERSION}/stocktankoilanalysisreports", STO_RECORD, TEST_STO_ID),
        (
            "get_record", f"{API_VERSION}/interfacialtensiontests",
            INTERFACIAL_TENSION_RECORD, TEST_INTERFACIAL_TENSION_ID,
        ),
        ("get_record", f"{API_VERSION}/vaporliquidequilibriumtests", VLE_RECORD, TEST_VLE_ID),
        ("get_record", f"{API_VERSION}/multiplecontactmiscibilitytests", MCM_RECORD, TEST_MCM_ID),
        ("get_record", f"{API_VERSION}/slimtubetests", SLIMTUBETEST_RECORD, TEST_SLIMTUBETEST_ID),
        (
            "get_record", f"{API_VERSION}/samplesanalysesreport", storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V1,
            storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID,
        ),
        ("get_record", f"{API_VERSION}/capillarypressuretests", SAMPLESANALYSIS_RECORD_V1, TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/relativepermeabilitytests", SAMPLESANALYSIS_RECORD_V1, TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/fractionationtests", SAMPLESANALYSIS_RECORD_V1, TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/extractiontests", SAMPLESANALYSIS_RECORD_V1, TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/physicalchemistrytests", SAMPLESANALYSIS_RECORD_V1, TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/electricalproperties", SAMPLESANALYSIS_RECORD_V1, TEST_SAMPLESANALYSIS_ID),
        ("get_record", f"{API_VERSION}/rockcompressibilities", SAMPLESANALYSIS_RECORD_V1, TEST_SAMPLESANALYSIS_ID),
        (
            "get_record", f"{API_VERSION}/watergasrelativepermeabilities",
            SAMPLESANALYSIS_RECORD_V1, TEST_SAMPLESANALYSIS_ID,
        ),
        (
            "get_record", f"{API_VERSION}/formationresistivityindexes",
            SAMPLESANALYSIS_RECORD_V1, TEST_SAMPLESANALYSIS_ID,
        ),
        (
            "get_record", f"{API_VERSION_V2}/samplesanalysesreport", storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V2,
            storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID,
        ),
        (
            "get_record", f"{API_VERSION_V2}/samplesanalysis", storage_mock_objects.SAMPLESANALYSIS_RECORD_V1,
            storage_mock_objects.TEST_SAMPLESANALYSIS_ID,
        ),
        (
            "get_record", f"{API_VERSION_V2}/masterdata", storage_mock_objects.SAMPLE_RECORD,
            storage_mock_objects.TEST_SAMPLE_ID,
        ),
        (
            "get_record", f"{API_VERSION_V2}/masterdata", storage_mock_objects.SAMPLE_ACQUISITION_JOB_RECORD,
            storage_mock_objects.TEST_SAMPLE_ACQUISITION_JOB_ID,
        ),
        (
            "get_record", f"{API_VERSION_V2}/masterdata", storage_mock_objects.SAMPLE_CHAIN_OF_CUSTODY_EVENT_RECORD,
            storage_mock_objects.TEST_SAMPLE_CHAIN_OF_CUSTODY_EVENT_ID,
        ),
        (
            "get_record", f"{API_VERSION_V2}/masterdata", storage_mock_objects.SAMPLE_CONTAINER_RECORD,
            storage_mock_objects.TEST_SAMPLE_CONTAINER_ID,
        ),
        (
            "get_record", f"{API_VERSION_V2}/masterdata", storage_mock_objects.GENERIC_FACILITY_RECORD,
            storage_mock_objects.TEST_GENERIC_FACILITY_ID,
        ),
        (
            "get_record", f"{API_VERSION_V2}/masterdata", storage_mock_objects.GENERIC_SITE_RECORD,
            storage_mock_objects.TEST_GENERIC_SITE_ID,
        ),
    ],
)
async def test_get_record_version_success(
    storage_method, path, osdu_record, record_id,
    with_patched_storage_get_success_200,
):
    with storage_override():
        test_version = 1234
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"/api/os-rafs-ddms/{path}/{record_id}/versions/{test_version}", headers=TEST_HEADERS,
            )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == osdu_record.dict()
    storage_record_service_mock.get_record.assert_called_once_with(record_id, test_version)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "storage_method,path,record_id", [
        ("get_record_versions", f"{API_VERSION}/rocksamples", TEST_ROCKSAMPLE_ID),
        ("get_record_versions", f"{API_VERSION}/coringreports", TEST_CORING_ID),
        ("get_record_versions", f"{API_VERSION}/pvtreports", TEST_PVT_ID),
        ("get_record_versions", f"{API_VERSION}/rocksampleanalyses", TEST_ROCKSAMPLEANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/ccereports", TEST_CCE_ID),
        ("get_record_versions", f"{API_VERSION}/difflibreports", TEST_DL_ID),
        ("get_record_versions", f"{API_VERSION}/transporttests", TEST_TRANSPORT_ID),
        ("get_record_versions", f"{API_VERSION}/compositionalanalysisreports", TEST_COMPOSITIONALANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/multistageseparatortests", TEST_MSS_ID),
        ("get_record_versions", f"{API_VERSION}/swellingtests", TEST_SWELLING_ID),
        ("get_record_versions", f"{API_VERSION}/constantvolumedepletiontests", TEST_CVD_ID),
        ("get_record_versions", f"{API_VERSION}/wateranalysisreports", TEST_WATERANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/stocktankoilanalysisreports", TEST_STO_ID),
        ("get_record_versions", f"{API_VERSION}/interfacialtensiontests", TEST_INTERFACIAL_TENSION_ID),
        ("get_record_versions", f"{API_VERSION}/vaporliquidequilibriumtests", TEST_VLE_ID),
        ("get_record_versions", f"{API_VERSION}/multiplecontactmiscibilitytests", TEST_MCM_ID),
        ("get_record_versions", f"{API_VERSION}/slimtubetests", TEST_SLIMTUBETEST_ID),
        (
            "get_record_versions", f"{API_VERSION}/samplesanalysesreport",
            storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID,
        ),
        ("get_record_versions", f"{API_VERSION}/capillarypressuretests", TEST_SAMPLESANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/relativepermeabilitytests", TEST_SAMPLESANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/fractionationtests", TEST_SAMPLESANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/physicalchemistrytests", TEST_SAMPLESANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/electricalproperties", TEST_SAMPLESANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/rockcompressibilities", TEST_SAMPLESANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/watergasrelativepermeabilities", TEST_SAMPLESANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION}/formationresistivityindexes", TEST_SAMPLESANALYSIS_ID),
        (
            "get_record_versions", f"{API_VERSION_V2}/samplesanalysesreport",
            storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID,
        ),
        ("get_record_versions", f"{API_VERSION_V2}/samplesanalysis", storage_mock_objects.TEST_SAMPLESANALYSIS_ID),
        ("get_record_versions", f"{API_VERSION_V2}/masterdata", storage_mock_objects.TEST_SAMPLE_ID),

    ],
)
async def test_get_record_versions_success(
    storage_method, path, record_id,
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
    "storage_method,api_status_code,path", [
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/rocksamples/{TEST_ROCKSAMPLE_ID}"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/coringreports/{TEST_CORING_ID}"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/pvtreports/{TEST_PVT_ID}"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/rocksampleanalyses/{TEST_ROCKSAMPLEANALYSIS_ID}"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/ccereports/{TEST_CCE_ID}"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/difflibreports/{TEST_DL_ID}"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/transporttests/{TEST_TRANSPORT_ID}"),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/compositionalanalysisreports/{TEST_COMPOSITIONALANALYSIS_ID}",
        ),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/multistageseparatortests/{TEST_MSS_ID}"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/swellingtests/{TEST_SWELLING_ID}"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/constantvolumedepletiontests/{TEST_CVD_ID}"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/wateranalysisreports/{TEST_WATERANALYSIS_ID}"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/stocktankoilanalysisreports/{TEST_STO_ID}"),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/interfacialtensiontests/{TEST_INTERFACIAL_TENSION_ID}",
        ),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/vaporliquidequilibriumtests/{TEST_VLE_ID}"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/multiplecontactmiscibilitytests/{TEST_MCM_ID}"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/slimtubetests/{TEST_SLIMTUBETEST_ID}"),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/samplesanalysesreport/{storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID}",
        ),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/capillarypressuretests/{TEST_SAMPLESANALYSIS_ID}"),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/relativepermeabilitytests/{TEST_SAMPLESANALYSIS_ID}",
        ),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/fractionationtests/{TEST_SAMPLESANALYSIS_ID}"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/extractiontests/{TEST_SAMPLESANALYSIS_ID}"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/physicalchemistrytests/{TEST_SAMPLESANALYSIS_ID}"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/electricalproperties/{TEST_SAMPLESANALYSIS_ID}"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/rockcompressibilities/{TEST_SAMPLESANALYSIS_ID}"),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/watergasrelativepermeabilities/{TEST_SAMPLESANALYSIS_ID}",
        ),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/formationresistivityindexes/{TEST_SAMPLESANALYSIS_ID}",
        ),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/rocksamples/{TEST_ROCKSAMPLE_ID}/versions/1234"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/coringreports/{TEST_CORING_ID}/versions/1234"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/pvtreports/{TEST_PVT_ID}/versions/1234"),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/rocksampleanalyses/{TEST_ROCKSAMPLEANALYSIS_ID}/versions/1234",
        ),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/ccereports/{TEST_CCE_ID}/versions/1234"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/difflibreports/{TEST_DL_ID}/versions/1234"),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/transporttests/{TEST_TRANSPORT_ID}/versions/1234"),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/compositionalanalysisreports/{TEST_COMPOSITIONALANALYSIS_ID}/versions/1234",
        ),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/multistageseparatortests/{TEST_MSS_ID}/versions/1234",
        ),
        ("get_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/swellingtests/{TEST_SWELLING_ID}/versions/1234"),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/constantvolumedepletiontests/{TEST_CVD_ID}/versions/1234",
        ),
        (
            "get_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/wateranalysisreports/{TEST_WATERANALYSIS_ID}/versions/1234",
        ),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/stocktankoilanalysisreports/{TEST_STO_ID}/versions/1234",
        ),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/interfacialtensiontests/{TEST_INTERFACIAL_TENSION_ID}/versions/1234",
        ),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/vaporliquidequilibriumtests/{TEST_VLE_ID}/versions/1234",
        ),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/multiplecontactmiscibilitytests/{TEST_MCM_ID}/versions/1234",
        ),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/slimtubetests/{TEST_SLIMTUBETEST_ID}/versions/1234",
        ),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/samplesanalysesreport/{storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID}/versions/1234",
        ),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/capillarypressuretests/{TEST_SAMPLESANALYSIS_ID}/versions/1234",
        ),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/relativepermeabilitytests/{TEST_SAMPLESANALYSIS_ID}/versions/1234",
        ),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/fractionationtests/{TEST_SAMPLESANALYSIS_ID}/versions/1234",
        ),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/extractiontests/{TEST_SAMPLESANALYSIS_ID}/versions/1234",
        ),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/physicalchemistrytests/{TEST_SAMPLESANALYSIS_ID}/versions/1234",
        ),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/electricalproperties/{TEST_SAMPLESANALYSIS_ID}/versions/1234",
        ),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/rockcompressibilities/{TEST_SAMPLESANALYSIS_ID}/versions/1234",
        ),
        (
            "get_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/watergasrelativepermeabilities/{TEST_SAMPLESANALYSIS_ID}/versions/1234",
        ),
        (
            "get_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/formationresistivityindexes/{TEST_SAMPLESANALYSIS_ID}/versions/1234",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/rocksamples/{TEST_ROCKSAMPLE_ID}/versions",
        ),
        ("get_record_versions", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/coringreports/{TEST_CORING_ID}/versions"),
        ("get_record_versions", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/pvtreports/{TEST_PVT_ID}/versions"),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/rocksampleanalyses/{TEST_ROCKSAMPLEANALYSIS_ID}/versions",
        ),
        ("get_record_versions", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/ccereports/{TEST_CCE_ID}/versions"),
        ("get_record_versions", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/difflibreports/{TEST_DL_ID}/versions"),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/transporttests/{TEST_TRANSPORT_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/compositionalanalysisreports/{TEST_COMPOSITIONALANALYSIS_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/multistageseparatortests/{TEST_MSS_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/swellingtests/{TEST_SWELLING_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/constantvolumedepletiontests/{TEST_CVD_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/wateranalysisreports/{TEST_WATERANALYSIS_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/stocktankoilanalysisreports/{TEST_STO_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/interfacialtensiontests/{TEST_INTERFACIAL_TENSION_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/vaporliquidequilibriumtests/{TEST_VLE_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/multiplecontactmiscibilitytests/{TEST_MCM_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/slimtubetests/{TEST_SLIMTUBETEST_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/samplesanalysesreport/{storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/capillarypressuretests/{TEST_SAMPLESANALYSIS_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/relativepermeabilitytests/{TEST_SAMPLESANALYSIS_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/fractionationtests/{TEST_SAMPLESANALYSIS_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/extractiontests/{TEST_SAMPLESANALYSIS_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/physicalchemistrytests/{TEST_SAMPLESANALYSIS_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/electricalproperties/{TEST_SAMPLESANALYSIS_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/rockcompressibilities/{TEST_SAMPLESANALYSIS_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/watergasrelativepermeabilities/{TEST_SAMPLESANALYSIS_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/formationresistivityindexes/{TEST_SAMPLESANALYSIS_ID}/versions",
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
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/samplesanalysesreport/{storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID}/versions",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/samplesanalysis/{storage_mock_objects.TEST_SAMPLESANALYSIS_ID}/versions",
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
            f"{API_VERSION_V2}/masterdata/{storage_mock_objects.TEST_SAMPLE_ID}",
        ),
        (
            "get_record_versions", status.HTTP_401_UNAUTHORIZED,
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
    storage_method, api_status_code, path,
    with_patched_storage_raises_40x,
):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(f"/api/os-rafs-ddms/{path}", headers=TEST_HEADERS)

    assert response.status_code == api_status_code


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path", [
        (f"{API_VERSION}/rocksamples/record_id"),
        (f"{API_VERSION}/coringreports/record_id"),
        (f"{API_VERSION}/pvtreports/record_id"),
        (f"{API_VERSION}/rocksampleanalyses/record_id"),
        (f"{API_VERSION}/ccereports/record_id"),
        (f"{API_VERSION}/difflibreports/record_id"),
        (f"{API_VERSION}/transporttests/record_id"),
        (f"{API_VERSION}/compositionalanalysisreports/record_id"),
        (f"{API_VERSION}/multistageseparatortests/record_id"),
        (f"{API_VERSION}/swellingtests/record_id"),
        (f"{API_VERSION}/constantvolumedepletiontests/record_id"),
        (f"{API_VERSION}/wateranalysisreports/record_id"),
        (f"{API_VERSION}/stocktankoilanalysisreports/record_id"),
        (f"{API_VERSION}/interfacialtensiontests/record_id"),
        (f"{API_VERSION}/vaporliquidequilibriumtests/record_id"),
        (f"{API_VERSION}/multiplecontactmiscibilitytests/record_id"),
        (f"{API_VERSION}/slimtubetests/record_id"),
        (f"{API_VERSION}/samplesanalysesreport/record_id"),
        (f"{API_VERSION}/capillarypressuretests/record_id"),
        (f"{API_VERSION}/relativepermeabilitytests/record_id"),
        (f"{API_VERSION}/fractionationtests/record_id"),
        (f"{API_VERSION}/extractiontests/record_id"),
        (f"{API_VERSION}/physicalchemistrytests/record_id"),
        (f"{API_VERSION}/electricalproperties/record_id"),
        (f"{API_VERSION}/rockcompressibilities/record_id"),
        (f"{API_VERSION}/watergasrelativepermeabilities/record_id"),
        (f"{API_VERSION}/formationresistivityindexes/record_id"),
        (f"{API_VERSION}/rocksamples/record_id/versions/1234"),
        (f"{API_VERSION}/coringreports/record_id/versions/1234"),
        (f"{API_VERSION}/pvtreports/record_id/versions/1234"),
        (f"{API_VERSION}/rocksampleanalyses/record_id/versions/1234"),
        (f"{API_VERSION}/ccereports/record_id/versions/1234"),
        (f"{API_VERSION}/difflibreports/record_id/versions/1234"),
        (f"{API_VERSION}/transporttests/record_id/versions/1234"),
        (f"{API_VERSION}/compositionalanalysisreports/record_id/versions/1234"),
        (f"{API_VERSION}/multistageseparatortests/record_id/versions/1234"),
        (f"{API_VERSION}/swellingtests/record_id/versions/1234"),
        (f"{API_VERSION}/constantvolumedepletiontests/record_id/versions/1234"),
        (f"{API_VERSION}/wateranalysisreports/record_id/versions/1234"),
        (f"{API_VERSION}/stocktankoilanalysisreports/record_id/versions/1234"),
        (f"{API_VERSION}/interfacialtensiontests/record_id/versions/1234"),
        (f"{API_VERSION}/vaporliquidequilibriumtests/record_id/versions/1234"),
        (f"{API_VERSION}/multiplecontactmiscibilitytests/record_id/versions/1234"),
        (f"{API_VERSION}/slimtubetests/record_id/versions/1234"),
        (f"{API_VERSION}/samplesanalysesreport/record_id/versions/1234"),
        (f"{API_VERSION}/capillarypressuretests/record_id/versions/1234"),
        (f"{API_VERSION}/relativepermeabilitytests/record_id/versions/1234"),
        (f"{API_VERSION}/fractionationtests/record_id/versions/1234"),
        (f"{API_VERSION}/extractiontests/record_id/versions/1234"),
        (f"{API_VERSION}/physicalchemistrytests/record_id/versions/1234"),
        (f"{API_VERSION}/electricalproperties/record_id/versions/1234"),
        (f"{API_VERSION}/rockcompressibilities/record_id/versions/1234"),
        (f"{API_VERSION}/watergasrelativepermeabilities/record_id/versions/1234"),
        (f"{API_VERSION}/formationresistivityindexes/record_id/versions/1234"),
        (f"{API_VERSION}/rocksamples/record_id/versions"),
        (f"{API_VERSION}/coringreports/record_id/versions"),
        (f"{API_VERSION}/pvtreports/record_id/versions"),
        (f"{API_VERSION}/rocksampleanalyses/record_id/versions"),
        (f"{API_VERSION}/ccereports/record_id/versions"),
        (f"{API_VERSION}/difflibreports/record_id/versions"),
        (f"{API_VERSION}/transporttests/record_id/versions"),
        (f"{API_VERSION}/compositionalanalysisreports/record_id/versions"),
        (f"{API_VERSION}/multistageseparatortests/record_id/versions"),
        (f"{API_VERSION}/swellingtests/record_id/versions"),
        (f"{API_VERSION}/constantvolumedepletiontests/record_id/versions"),
        (f"{API_VERSION}/wateranalysisreports/record_id/versions"),
        (f"{API_VERSION}/stocktankoilanalysisreports/record_id/versions"),
        (f"{API_VERSION}/interfacialtensiontests/record_id/versions"),
        (f"{API_VERSION}/vaporliquidequilibriumtests/record_id/versions"),
        (f"{API_VERSION}/multiplecontactmiscibilitytests/record_id/versions"),
        (f"{API_VERSION}/slimtubetests/record_id/versions"),
        (f"{API_VERSION}/samplesanalysesreport/record_id/versions"),
        (f"{API_VERSION}/capillarypressuretests/record_id/versions"),
        (f"{API_VERSION}/relativepermeabilitytests/record_id/versions"),
        (f"{API_VERSION}/fractionationtests/record_id/versions"),
        (f"{API_VERSION}/extractiontests/record_id/versions"),
        (f"{API_VERSION}/physicalchemistrytests/record_id/versions"),
        (f"{API_VERSION}/electricalproperties/record_id/versions"),
        (f"{API_VERSION}/rockcompressibilities/record_id/versions"),
        (f"{API_VERSION}/watergasrelativepermeabilities/record_id/versions"),
        (f"{API_VERSION}/formationresistivityindexes/record_id/versions"),
        (f"{API_VERSION_V2}/samplesanalysesreport/record_id"),
        (f"{API_VERSION_V2}/samplesanalysesreport/record_id/versions"),
        (f"{API_VERSION_V2}/samplesanalysesreport/record_id/versions/1234"),
        (f"{API_VERSION_V2}/samplesanalysis/record_id"),
        (f"{API_VERSION_V2}/samplesanalysis/record_id/versions"),
        (f"{API_VERSION_V2}/samplesanalysis/record_id/versions/1234"),
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
    "storage_method,api_status_code,path", [
        ("soft_delete_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/rocksamples/{TEST_ROCKSAMPLE_ID}"),
        ("soft_delete_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/coringreports/{TEST_CORING_ID}"),
        ("soft_delete_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/pvtreports/{TEST_PVT_ID}"),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/rocksampleanalyses/{TEST_ROCKSAMPLEANALYSIS_ID}",
        ),
        ("soft_delete_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/ccereports/{TEST_CCE_ID}"),
        ("soft_delete_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/difflibreports/{TEST_DL_ID}"),
        ("soft_delete_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/transporttests/{TEST_TRANSPORT_ID}"),
        (
            "soft_delete_record",
            status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/compositionalanalysisreports/{TEST_COMPOSITIONALANALYSIS_ID}",
        ),
        ("soft_delete_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/multistageseparatortests/{TEST_MSS_ID}"),
        ("soft_delete_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/swellingtests/{TEST_SWELLING_ID}"),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/constantvolumedepletiontests/{TEST_CVD_ID}",
        ),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/wateranalysisreports/{TEST_WATERANALYSIS_ID}",
        ),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/stocktankoilanalysisreports/{TEST_STO_ID}",
        ),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/interfacialtensiontests/{TEST_INTERFACIAL_TENSION_ID}",
        ),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/vaporliquidequilibriumtests/{TEST_VLE_ID}",
        ),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/multiplecontactmiscibilitytests/{TEST_MCM_ID}",
        ),
        ("soft_delete_record", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/slimtubetests/{TEST_SLIMTUBETEST_ID}"),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/samplesanalysesreport/{storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID}",
        ),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/capillarypressuretests/{TEST_SAMPLESANALYSIS_ID}",
        ),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/relativepermeabilitytests/{TEST_SAMPLESANALYSIS_ID}",
        ),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/fractionationtests/{TEST_SAMPLESANALYSIS_ID}",
        ),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/extractiontests/{TEST_SAMPLESANALYSIS_ID}",
        ),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/physicalchemistrytests/{TEST_SAMPLESANALYSIS_ID}",
        ),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/electricalproperties/{TEST_SAMPLESANALYSIS_ID}",
        ),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/rockcompressibilities/{TEST_SAMPLESANALYSIS_ID}",
        ),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/watergasrelativepermeabilities/{TEST_SAMPLESANALYSIS_ID}",
        ),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/formationresistivityindexes/{TEST_SAMPLESANALYSIS_ID}",
        ),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/samplesanalysesreport/{storage_mock_objects.TEST_SAMPLESANALYSESREPORT_ID}",
        ),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/samplesanalysis/{storage_mock_objects.TEST_SAMPLESANALYSIS_ID}",
        ),
        (
            "soft_delete_record", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION_V2}/masterdata/{storage_mock_objects.TEST_SAMPLE_ID}",
        ),
    ],
)
async def test_delete_record_auth_errors_from_storage(
    storage_method, api_status_code, path,
    with_patched_storage_raises_40x,
):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.delete(f"/api/os-rafs-ddms/{path}", headers=TEST_HEADERS)

    assert response.status_code == api_status_code


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path", [
        (f"{API_VERSION}/rocksamples/record_id"),
        (f"{API_VERSION}/coringreports/record_id"),
        (f"{API_VERSION}/pvtreports/record_id"),
        (f"{API_VERSION}/rocksampleanalyses/record_id"),
        (f"{API_VERSION}/ccereports/record_id"),
        (f"{API_VERSION}/difflibreports/record_id"),
        (f"{API_VERSION}/transporttests/record_id"),
        (f"{API_VERSION}/compositionalanalysisreports/record_id"),
        (f"{API_VERSION}/multistageseparatortests/record_id"),
        (f"{API_VERSION}/swellingtests/record_id"),
        (f"{API_VERSION}/constantvolumedepletiontests/record_id"),
        (f"{API_VERSION}/wateranalysisreports/record_id"),
        (f"{API_VERSION}/stocktankoilanalysisreports/record_id"),
        (f"{API_VERSION}/interfacialtensiontests/record_id"),
        (f"{API_VERSION}/vaporliquidequilibriumtests/record_id"),
        (f"{API_VERSION}/multiplecontactmiscibilitytests/record_id"),
        (f"{API_VERSION}/slimtubetests/record_id"),
        (f"{API_VERSION}/samplesanalysesreport/record_id"),
        (f"{API_VERSION}/capillarypressuretests/record_id"),
        (f"{API_VERSION}/relativepermeabilitytests/record_id"),
        (f"{API_VERSION}/fractionationtests/record_id"),
        (f"{API_VERSION}/extractiontests/record_id"),
        (f"{API_VERSION}/physicalchemistrytests/record_id"),
        (f"{API_VERSION}/electricalproperties/record_id"),
        (f"{API_VERSION}/rockcompressibilities/record_id"),
        (f"{API_VERSION}/watergasrelativepermeabilities/record_id"),
        (f"{API_VERSION}/formationresistivityindexes/record_id"),
        (f"{API_VERSION_V2}/samplesanalysesreport/record_id"),
        (f"{API_VERSION_V2}/samplesanalysis/record_id"),
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
        ("upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/rocksamples", ROCKSAMPLE_RECORD),
        ("upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/coringreports", CORING_RECORD),
        ("upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/pvtreports", PVT_RECORD),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/rocksampleanalyses", ROCKSAMPLEANALYSIS_RECORD,
        ),
        ("upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/ccereports", CCE_RECORD),
        ("upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/difflibreports", DL_RECORD),
        ("upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/transporttests", TRANSPORT_RECORD),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/compositionalanalysisreports", COMPOSITIONALANALYSIS_RECORD,
        ),
        ("upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/constantvolumedepletiontests", CVD_RECORD),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/multistageseparatortests", MULTISTAGESEPARATOR_RECORD,
        ),
        ("upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/swellingtests", SWELLING_RECORD),
        ("upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/constantvolumedepletiontests", CVD_RECORD),
        ("upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/wateranalysisreports", WATERANALYSIS_RECORD),
        ("upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/stocktankoilanalysisreports", STO_RECORD),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/interfacialtensiontests", INTERFACIAL_TENSION_RECORD,
        ),
        ("upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/vaporliquidequilibriumtests", VLE_RECORD),
        ("upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/multiplecontactmiscibilitytests", MCM_RECORD),
        ("upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/slimtubetests", SLIMTUBETEST_RECORD),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION}/samplesanalysesreport",
            storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V1,
        ),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/capillarypressuretests", SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/relativepermeabilitytests", SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/fractionationtests", SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/physicalchemistrytests", SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/electricalproperties", SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/rockcompressibilities", SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/watergasrelativepermeabilities", SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED,
            f"{API_VERSION}/formationresistivityindexes", SAMPLESANALYSIS_RECORD_V1,
        ),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION_V2}/samplesanalysesreport",
            storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V2,
        ),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION_V2}/samplesanalysis",
            storage_mock_objects.SAMPLESANALYSIS_RECORD_V2,
        ),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_RECORD,
        ),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_ACQUISITION_JOB_RECORD,
        ),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CHAIN_OF_CUSTODY_EVENT_RECORD,
        ),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.SAMPLE_CONTAINER_RECORD,
        ),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.GENERIC_FACILITY_RECORD,
        ),
        (
            "upsert_records", status.HTTP_401_UNAUTHORIZED, f"{API_VERSION_V2}/masterdata",
            storage_mock_objects.GENERIC_SITE_RECORD,
        ),
    ],
)
async def test_post_record_auth_errors_from_storage(
    storage_method, api_status_code, path, osdu_record,
    with_patched_storage_raises_40x,
    with_patched_storage_query_pvt_200,
):
    with storage_override():
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
        (f"{API_VERSION}/rocksamples", ROCKSAMPLE_RECORD),
        (f"{API_VERSION}/coringreports", CORING_RECORD),
        (f"{API_VERSION}/pvtreports", PVT_RECORD),
        (f"{API_VERSION}/rocksampleanalyses", ROCKSAMPLEANALYSIS_RECORD),
        (f"{API_VERSION}/ccereports", CCE_RECORD),
        (f"{API_VERSION}/difflibreports", DL_RECORD),
        (f"{API_VERSION}/transporttests", TRANSPORT_RECORD),
        (f"{API_VERSION}/compositionalanalysisreports", COMPOSITIONALANALYSIS_RECORD),
        (f"{API_VERSION}/multistageseparatortests", MULTISTAGESEPARATOR_RECORD),
        (f"{API_VERSION}/swellingtests", SWELLING_RECORD),
        (f"{API_VERSION}/constantvolumedepletiontests", CVD_RECORD),
        (f"{API_VERSION}/wateranalysisreports", WATERANALYSIS_RECORD),
        (f"{API_VERSION}/stocktankoilanalysisreports", STO_RECORD),
        (f"{API_VERSION}/interfacialtensiontests", INTERFACIAL_TENSION_RECORD),
        (f"{API_VERSION}/vaporliquidequilibriumtests", VLE_RECORD),
        (f"{API_VERSION}/multiplecontactmiscibilitytests", MCM_RECORD),
        (f"{API_VERSION}/slimtubetests", SLIMTUBETEST_RECORD),
        (f"{API_VERSION}/samplesanalysesreport", storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V1),
        (f"{API_VERSION}/capillarypressuretests", SAMPLESANALYSIS_RECORD_V1),
        (f"{API_VERSION}/relativepermeabilitytests", SAMPLESANALYSIS_RECORD_V1),
        (f"{API_VERSION}/fractionationtests", SAMPLESANALYSIS_RECORD_V1),
        (f"{API_VERSION}/extractiontests", SAMPLESANALYSIS_RECORD_V1),
        (f"{API_VERSION}/physicalchemistrytests", SAMPLESANALYSIS_RECORD_V1),
        (f"{API_VERSION}/electricalproperties", SAMPLESANALYSIS_RECORD_V1),
        (f"{API_VERSION}/rockcompressibilities", SAMPLESANALYSIS_RECORD_V1),
        (f"{API_VERSION}/watergasrelativepermeabilities", SAMPLESANALYSIS_RECORD_V1),
        (f"{API_VERSION}/formationresistivityindexes", SAMPLESANALYSIS_RECORD_V1),
        (f"{API_VERSION_V2}/samplesanalysesreport", storage_mock_objects.SAMPLESANALYSESREPORT_RECORD_V2),
        (f"{API_VERSION_V2}/samplesanalysis", storage_mock_objects.SAMPLESANALYSIS_RECORD_V2),
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
    path, osdu_record,
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
    "endpoint,record_id", [
        (CORING_ENDPOINT_PATH, TEST_ROCKSAMPLE_ID),
        (CORING_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (CORING_ENDPOINT_PATH, TEST_CCE_ID),
        (CORING_ENDPOINT_PATH, TEST_DL_ID),
        (CORING_ENDPOINT_PATH, TEST_TRANSPORT_ID),
        (CORING_ENDPOINT_PATH, TEST_COMPOSITIONALANALYSIS_ID),
        (PVT_ENDPOINT_PATH, TEST_ROCKSAMPLE_ID),
        (PVT_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (ROCKSAMPLE_ENDPOINT_PATH, TEST_CORING_ID),
        (ROCKSAMPLE_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (ROCKSAMPLE_ENDPOINT_PATH, TEST_CCE_ID),
        (ROCKSAMPLE_ENDPOINT_PATH, TEST_DL_ID),
        (ROCKSAMPLE_ENDPOINT_PATH, TEST_TRANSPORT_ID),
        (ROCKSAMPLEANALYSIS_ENDPOINT_PATH, TEST_CORING_ID),
        (ROCKSAMPLEANALYSIS_ENDPOINT_PATH, TEST_ROCKSAMPLE_ID),
        (ROCKSAMPLEANALYSIS_ENDPOINT_PATH, TEST_CCE_ID),
        (ROCKSAMPLEANALYSIS_ENDPOINT_PATH, TEST_DL_ID),
        (ROCKSAMPLEANALYSIS_ENDPOINT_PATH, TEST_TRANSPORT_ID),
        (CCE_ENDPOINT_PATH, TEST_CORING_ID),
        (CCE_ENDPOINT_PATH, TEST_ROCKSAMPLE_ID),
        (CCE_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (DIF_LIB_ENDPOINT_PATH, TEST_CORING_ID),
        (DIF_LIB_ENDPOINT_PATH, TEST_ROCKSAMPLE_ID),
        (DIF_LIB_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (TRANSPORT_ENDPOINT_PATH, TEST_CORING_ID),
        (TRANSPORT_ENDPOINT_PATH, TEST_ROCKSAMPLE_ID),
        (TRANSPORT_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (COMPOSITIONALANALYSIS_ENDPOINT_PATH, TEST_CORING_ID),
        (COMPOSITIONALANALYSIS_ENDPOINT_PATH, TEST_ROCKSAMPLE_ID),
        (COMPOSITIONALANALYSIS_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (MSS_ENDPOINT_PATH, TEST_CORING_ID),
        (MSS_ENDPOINT_PATH, TEST_ROCKSAMPLE_ID),
        (MSS_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (SWELLING_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (WATERANALYSIS_ENDPOINT_PATH, TEST_COMPOSITIONALANALYSIS_ID),
        (STO_ENDPOINT_PATH, TEST_CORING_ID),
        (STO_ENDPOINT_PATH, TEST_ROCKSAMPLE_ID),
        (STO_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (INTERFACIAL_TENSION_ENDPOINT_PATH, TEST_CORING_ID),
        (INTERFACIAL_TENSION_ENDPOINT_PATH, TEST_ROCKSAMPLE_ID),
        (INTERFACIAL_TENSION_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (VLE_ENDPOINT_PATH, TEST_CORING_ID),
        (VLE_ENDPOINT_PATH, TEST_ROCKSAMPLE_ID),
        (VLE_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (MCM_ENDPOINT_PATH, TEST_PVT_ID),
        (SLIMTUBETEST_ENDPOINT_PATH, TEST_CORING_ID),
        (SLIMTUBETEST_ENDPOINT_PATH, TEST_ROCKSAMPLE_ID),
        (SLIMTUBETEST_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (storage_mock_objects.SAMPLESANALYSES_REPORT_ENDPOINT_PATH, TEST_CORING_ID),
        (CAP_PRESSURE_ENDPOINT_PATH, TEST_CORING_ID),
        (CAP_PRESSURE_ENDPOINT_PATH, TEST_ROCKSAMPLE_ID),
        (CAP_PRESSURE_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (RELATIVE_PERMEABILITY_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (FRACTIONATION_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (EXTRACTION_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (PHYS_CHEM_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (ELECTRICAL_PROPERTIES_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (ROCK_COMPRESSIBILITY_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (WATER_GAS_RELATIVE_PERMEABILITY_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (FORMATION_RESISTIVITY_INDEX_ENDPOINT_PATH, TEST_ROCKSAMPLEANALYSIS_ID),
        (storage_mock_objects.SAMPLESANALYSES_REPORT_ENDPOINT_PATH_V2, TEST_CORING_ID),
        (storage_mock_objects.SAMPLESANALYSIS_ENDPOINT_PATH_V2, TEST_CORING_ID),
        (storage_mock_objects.MASTER_DATA_ENDPOINT_PATH_V2, TEST_ROCKSAMPLEANALYSIS_ID),
    ],
)
async def test_get_record_wrong_id_pattern(endpoint, record_id):
    with storage_override():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"{endpoint}/{record_id}",
                headers=TEST_HEADERS,
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint,manifest", [
        (CORING_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (PVT_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (ROCKSAMPLE_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (ROCKSAMPLEANALYSIS_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (DIF_LIB_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (COMPOSITIONALANALYSIS_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (MSS_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (SWELLING_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (CVD_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (WATERANALYSIS_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (STO_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (INTERFACIAL_TENSION_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (VLE_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (MCM_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (SLIMTUBETEST_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (storage_mock_objects.SAMPLESANALYSES_REPORT_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (CAP_PRESSURE_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (RELATIVE_PERMEABILITY_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (FRACTIONATION_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (EXTRACTION_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (PHYS_CHEM_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (ELECTRICAL_PROPERTIES_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (ROCK_COMPRESSIBILITY_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (WATER_GAS_RELATIVE_PERMEABILITY_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (FORMATION_RESISTIVITY_INDEX_ENDPOINT_PATH, OSDU_GENERIC_RECORD.dict()),
        (storage_mock_objects.SAMPLESANALYSES_REPORT_ENDPOINT_PATH_V2, OSDU_GENERIC_RECORD.dict()),
        (storage_mock_objects.SAMPLESANALYSIS_ENDPOINT_PATH_V2, OSDU_GENERIC_RECORD.dict()),
        (f"{storage_mock_objects.MASTER_DATA_ENDPOINT_PATH_V2}", OSDU_GENERIC_RECORD.dict()),
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
    assert response_json["code"] == status.HTTP_422_UNPROCESSABLE_ENTITY

    assert EXPECTED_422_INVALID_KIND_REASON.format(OSDU_GENERIC_RECORD.kind) in response.json()["reason"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint,record_id", [
        (CORING_ENDPOINT_PATH, TEST_WRONG_ID),
        (PVT_ENDPOINT_PATH, TEST_WRONG_ID),
        (ROCKSAMPLE_ENDPOINT_PATH, TEST_WRONG_ID),
        (CCE_ENDPOINT_PATH, TEST_WRONG_ID),
        (DIF_LIB_ENDPOINT_PATH, TEST_WRONG_ID),
        (TRANSPORT_ENDPOINT_PATH, TEST_WRONG_ID),
        (COMPOSITIONALANALYSIS_ENDPOINT_PATH, TEST_WRONG_ID),
        (MSS_ENDPOINT_PATH, TEST_WRONG_ID),
        (SWELLING_ENDPOINT_PATH, TEST_WRONG_ID),
        (CVD_ENDPOINT_PATH, TEST_WRONG_ID),
        (WATERANALYSIS_ENDPOINT_PATH, TEST_WRONG_ID),
        (STO_ENDPOINT_PATH, TEST_WRONG_ID),
        (INTERFACIAL_TENSION_ENDPOINT_PATH, TEST_WRONG_ID),
        (VLE_ENDPOINT_PATH, TEST_WRONG_ID),
        (MCM_ENDPOINT_PATH, TEST_WRONG_ID),
        (SLIMTUBETEST_ENDPOINT_PATH, TEST_WRONG_ID),
        (storage_mock_objects.SAMPLESANALYSES_REPORT_ENDPOINT_PATH, TEST_WRONG_ID),
        (CAP_PRESSURE_ENDPOINT_PATH, TEST_WRONG_ID),
        (RELATIVE_PERMEABILITY_ENDPOINT_PATH, TEST_WRONG_ID),
        (FRACTIONATION_ENDPOINT_PATH, TEST_WRONG_ID),
        (EXTRACTION_ENDPOINT_PATH, TEST_WRONG_ID),
        (PHYS_CHEM_ENDPOINT_PATH, TEST_WRONG_ID),
        (ELECTRICAL_PROPERTIES_ENDPOINT_PATH, TEST_WRONG_ID),
        (ROCK_COMPRESSIBILITY_ENDPOINT_PATH, TEST_WRONG_ID),
        (WATER_GAS_RELATIVE_PERMEABILITY_ENDPOINT_PATH, TEST_WRONG_ID),
        (FORMATION_RESISTIVITY_INDEX_ENDPOINT_PATH, TEST_WRONG_ID),
        (storage_mock_objects.SAMPLESANALYSES_REPORT_ENDPOINT_PATH_V2, TEST_WRONG_ID),
        (storage_mock_objects.SAMPLESANALYSIS_ENDPOINT_PATH_V2, TEST_WRONG_ID),
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

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
