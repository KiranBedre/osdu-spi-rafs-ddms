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
from httpx import AsyncClient
from starlette import status

from app.api.dependencies.parquet import get_parquet_loader
from app.api.dependencies.services import (
    get_async_dataset_service,
    get_async_search_service,
)
from app.api.routes.samplesanalysis.endpoints import SEARCH_READ_BATCH_SIZE
from app.dataframe import parquet_loader
from app.main import app
from app.services import dataset, search
from tests.test_api.test_routes import dependencies
from tests.test_api.test_routes.data.data_mock_objects import TEST_HEADERS_JSON
from tests.test_api.test_routes.osdu.storage_mock_objects import (
    SAMPLESANALYSIS_ENDPOINT_PATH,
    TEST_HEADERS,
    TEST_SERVER,
)
from tests.test_api.test_routes.samplesanalysis.samplesanalysis_mock_objects import (
    build_dataset_get_signed_urls_response,
    build_orient_split_tests,
    build_parquet_loader_read_parquets_response,
    build_sa_ids_response,
    build_search_find_records_response,
    get_aggregated_count,
)

async_dataset_service_mock = create_autospec(dataset.DatasetService, spec_set=True, instance=True)
async_search_service_mock = create_autospec(search.SearchService, spec_set=True, instance=True)
parquet_loader_mock = create_autospec(parquet_loader.ParquetLoader, spec_set=True, instance=True)


async def mock_get_async_dataset_service():
    yield async_dataset_service_mock


async def mock_get_async_search_service():
    yield async_search_service_mock


async def mock_get_parquet_loader():
    yield parquet_loader_mock

ALL_SAMPLES_ANALYSIS_TYPES = [
    "routinecoreanalysis",
    "constantcompositionexpansion",
    "differentialliberation",
    "transport",
    "multistageseparator",
    "compositionalanalysis",
    "swelling",
    "constantvolumedepletion",
    "wateranalysis",
    "interfacialtension",
    "vaporliquidequilibrium",
    "multiplecontactmiscibility",
    "slimtube",
    "extraction",
    "fractionation",
    "relativepermeability",
    "rockcompressibility",
    "capillarypressure",
    "electricalproperties",
    "nmr",
    "multiplesalinitytests",
    "gcmsalkanes",
    "gcmsaromatics",
    "gcmsratios",
    "gaschromatographyanalyses",
    "gascompositionanalyses",
    "isotopes",
    "bulkpyrolysisanalyses",
    "coregamma",
    "uniaxial",
    "gcmsms",
    "cec",
    "triaxial",
    "wettabilityindex",
    "tec",
    "edsmapping",
    "xrf",
    "tensilestrength",
    "xrd",
    "pdp",
    "stocktankoilanalysis",
]


@contextmanager
def services_overrides():
    overrides = {
        get_async_search_service: mock_get_async_search_service,
        get_async_dataset_service: mock_get_async_dataset_service,
        get_parquet_loader: mock_get_parquet_loader,
    }
    with dependencies.DependencyOverrider(app, overrides) as mock_dependencies:
        yield mock_dependencies


@pytest.fixture
def with_patched_services_success(total_size, with_parquet_read_error):
    """Patch services for success."""
    with patch.object(
        async_search_service_mock,
        "find_records",
            side_effect=[build_search_find_records_response(1, total_size + 1), {}],
    ):
        with patch.object(
            async_dataset_service_mock,
            "get_signed_urls",
                side_effect=[build_dataset_get_signed_urls_response(1, total_size + 1), []],
        ):
            with patch.object(
                parquet_loader_mock,
                "read_parquet_files",
                    side_effect=[
                        build_parquet_loader_read_parquets_response(
                            1, total_size + 1, with_parquet_read_error,
                        ), [],
                    ],
            ):
                yield


@pytest.mark.asyncio
async def test_types_route():
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        response = await client.get(
            f"{SAMPLESANALYSIS_ENDPOINT_PATH}/analysistypes",
            headers=TEST_HEADERS,
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/json"

    response_json = response.json()
    assert isinstance(response_json, dict)
    assert response_json


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "analysistype", ALL_SAMPLES_ANALYSIS_TYPES,
)
async def test_content_schemas_route(analysistype):
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        response = await client.get(
            f"{SAMPLESANALYSIS_ENDPOINT_PATH}/{analysistype}/data/schema",
            headers={**TEST_HEADERS, "Accept": "application/json;version=1.0.0"},
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/json"

    response_json = response.json()
    assert isinstance(response_json, dict)
    assert response_json


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "analysistype", ALL_SAMPLES_ANALYSIS_TYPES,
)
async def test_content_schemas_wrong_version(analysistype):
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        response = await client.get(
            f"{SAMPLESANALYSIS_ENDPOINT_PATH}/{analysistype}/data/schema",
            headers={**TEST_HEADERS, "Accept": "application/json;version=0.0.0"},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["message"] == f"Schema not found for {analysistype} and version 0.0.0"


@pytest.mark.asyncio
async def test_content_schemas_wrong_type():
    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
        response = await client.get(
            f"{SAMPLESANALYSIS_ENDPOINT_PATH}/wrongtype/data/schema",
            headers={**TEST_HEADERS, "Accept": "application/json;version=0.0.0"},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["message"] == "Schema not found for wrongtype and version 0.0.0"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "analysistype,pagination_params,total_size,with_parquet_read_error",
    [
        ("nmr", {}, 10, None),
        ("nmr", {"offset": 10, "page_limit": 20}, 50, None),
        ("nmr", {"offset": 50, "page_limit": 100}, 105, None),
    ],
)
async def test_search_data_success(
    analysistype,
    with_patched_services_success,
    pagination_params,
    total_size,
    with_parquet_read_error,
):
    parameters = {}
    parameters.update(pagination_params)

    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"{SAMPLESANALYSIS_ENDPOINT_PATH}/{analysistype}/search/data",
                headers=TEST_HEADERS_JSON,
                params=parameters,
            )

    expected_offset = parameters.get("offset", 0)
    expected_page_limit = parameters.get("page_limit", 100)

    assert response.json()["offset"] == expected_offset
    assert response.json()["page_limit"] == expected_page_limit
    assert response.json()["total_size"] == total_size

    result_df = response.json()["result"]

    expected_test_data = [
        test["data"][0]
        for test in build_orient_split_tests(
            expected_offset + 1, min(expected_offset + expected_page_limit + 1, total_size + 1),
        )
    ]
    assert result_df["data"] == expected_test_data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "analysistype,pagination_params,total_size,filters,expected_filtered_data,with_parquet_read_error",
    [
        ("nmr", {}, 100, {"columns_aggregation": "SamplesAnalysisID,count"}, get_aggregated_count(100), None),
        (
            "nmr", {}, 1, {
                "columns_aggregation": "SamplesAnalysisID,count",
                "rows_filter": "SamplesAnalysisID,eq,opendes:work-product-component--SamplesAnalysis:1:",
            }, get_aggregated_count(1), None,
        ),
    ],
)
async def test_search_data_with_filters_success(
    analysistype,
    with_patched_services_success,
    pagination_params,
    total_size,
    filters,
    expected_filtered_data,
    with_parquet_read_error,
):
    parameters = {}
    parameters.update(pagination_params)
    parameters.update(filters)

    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"{SAMPLESANALYSIS_ENDPOINT_PATH}/{analysistype}/search/data",
                headers=TEST_HEADERS_JSON,
                params=parameters,
            )

    assert response.json() == expected_filtered_data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "analysistype,pagination_params,total_size,with_parquet_read_error", [
        ("nmr", {}, 10, None),
        ("nmr", {"offset": 10, "page_limit": 50}, 100, None),
    ],
)
async def test_search_success(
    analysistype,
    with_patched_services_success,
    pagination_params,
    total_size,
    with_parquet_read_error,
):
    parameters = {}
    parameters.update(pagination_params)

    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"{SAMPLESANALYSIS_ENDPOINT_PATH}/{analysistype}/search",
                headers=TEST_HEADERS_JSON,
                params=parameters,
            )

    expected_offset = parameters.get("offset", 0)
    expected_page_limit = parameters.get("page_limit", 1000)

    assert response.json()["result"] == build_sa_ids_response(
        expected_offset + 1, min(expected_offset + expected_page_limit + 1, total_size + 1),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "analysistype,total_size,with_parquet_read_error", [
        ("nmr", 10, "Error Msg"),
    ],
)
async def test_search_failed(
    analysistype,
    with_patched_services_success,
    total_size,
    with_parquet_read_error,
):

    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                f"{SAMPLESANALYSIS_ENDPOINT_PATH}/{analysistype}/search/data",
                headers=TEST_HEADERS_JSON,
            )
    from loguru import logger
    logger.warning(response.json())

    assert response.json()["code"] == status.HTTP_500_INTERNAL_SERVER_ERROR
    response_values = response.json()["reason"]["errors"].values()
    assert list(response_values) == [with_parquet_read_error for _ in range(len(response_values))]
