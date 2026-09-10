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

from datetime import date
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from app.resources.paths import RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR, SATURATION_FUNCTION_SET_STR
from app.search.ddms_dataset_ids_fetcher import SearchServiceSamplesAnalysisTypeIdsFetcher
from app.search.res_sim_rock_physics_ids_fetcher import SearchServiceResSimRockPhysicsIdsFetcher
from app.search.saturation_function_set_ids_fetcher import SearchServiceSaturationFunctionSetIdsFetcher

_NO_RESULTS = {"results": [], "cursor": None}


@pytest.fixture
def mock_search_service():
    search_service = MagicMock()
    search_service.find_records = AsyncMock(return_value=_NO_RESULTS)
    return search_service


def _patch_supplement():
    return patch(
        "app.search.ddms_dataset_ids_fetcher.supplement_with_pending_writes",
        new=AsyncMock(return_value=[]),
    )


# --- SearchServiceSamplesAnalysisTypeIdsFetcher (no scope keys directly queryable; passes scope=None) ---


@pytest.mark.asyncio
async def test_samplesanalysis_fetcher_calls_supplement_with_correct_family_and_no_scope(mock_search_service):
    with _patch_supplement() as mock_supplement:
        fetcher = SearchServiceSamplesAnalysisTypeIdsFetcher(search_service=mock_search_service)
        await fetcher.get_ids(
            data_partition_id="partition",
            analysis_type="routinecoreanalysis",
            target_schema_version="1.0.0",
            query_date_range=(date(2024, 1, 1), date(2024, 12, 31)),
            wks_parameters=None,
        )

    mock_supplement.assert_awaited_once_with(
        result_ids=ANY,
        data_partition_id="partition",
        analysis_family="samplesanalysis",
        analysis_type="routinecoreanalysis",
        target_schema_version="1.0.0",
        scope=None,
    )


# --- SearchServiceResSimRockPhysicsIdsFetcher ---


def _patch_res_sim_supplement():
    return patch(
        "app.search.res_sim_rock_physics_ids_fetcher.supplement_with_pending_writes",
        new=AsyncMock(return_value=[]),
    )


@pytest.mark.asyncio
async def test_res_sim_fetcher_passes_resolved_scope_into_supplement(mock_search_service):
    with _patch_res_sim_supplement() as mock_supplement:
        fetcher = SearchServiceResSimRockPhysicsIdsFetcher(search_service=mock_search_service)
        await fetcher.get_ids(
            data_partition_id="partition",
            content_type="rockphysicsmodel",
            target_schema_version="1.0.0",
            query_date_range=(date(2024, 1, 1), date(2024, 12, 31)),
            wks_parameters={"basin_id": "partition:master-data--Basin:b-1:"},
        )

    mock_supplement.assert_awaited_once_with(
        result_ids=ANY,
        data_partition_id="partition",
        analysis_family=RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR,
        analysis_type="rockphysicsmodel",
        target_schema_version="1.0.0",
        scope={"basin_id": "partition:master-data--Basin:b-1:"},
    )


@pytest.mark.asyncio
async def test_res_sim_fetcher_passes_none_scope_when_no_wks_parameters(mock_search_service):
    with _patch_res_sim_supplement() as mock_supplement:
        fetcher = SearchServiceResSimRockPhysicsIdsFetcher(search_service=mock_search_service)
        await fetcher.get_ids(
            data_partition_id="partition",
            content_type="rockphysicsmodel",
            target_schema_version="1.0.0",
            query_date_range=(date(2024, 1, 1), date(2024, 12, 31)),
            wks_parameters=None,
        )

    mock_supplement.assert_awaited_once_with(
        result_ids=ANY,
        data_partition_id="partition",
        analysis_family=RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR,
        analysis_type="rockphysicsmodel",
        target_schema_version="1.0.0",
        scope=None,
    )


@pytest.mark.asyncio
async def test_res_sim_fetcher_builds_search_scope_only_once(mock_search_service):
    """Anti-pattern #5 guard: SearchScope must be built once in get_ids and reused
    by _build_query, not reconstructed a second time inside it."""
    with patch(
        "app.search.res_sim_rock_physics_ids_fetcher.SearchScope",
        wraps=__import__("app.models.schemas.search_scope", fromlist=["SearchScope"]).SearchScope,
    ) as mock_scope_cls, _patch_res_sim_supplement():
        fetcher = SearchServiceResSimRockPhysicsIdsFetcher(search_service=mock_search_service)
        await fetcher.get_ids(
            data_partition_id="partition",
            content_type="rockphysicsmodel",
            target_schema_version="1.0.0",
            query_date_range=(date(2024, 1, 1), date(2024, 12, 31)),
            wks_parameters={"basin_id": "partition:master-data--Basin:b-1:"},
        )

    assert mock_scope_cls.call_count == 1


# --- SearchServiceSaturationFunctionSetIdsFetcher ---


def _patch_saturation_supplement():
    return patch(
        "app.search.saturation_function_set_ids_fetcher.supplement_with_pending_writes",
        new=AsyncMock(return_value=[]),
    )


@pytest.mark.asyncio
async def test_saturation_function_set_fetcher_passes_resolved_scope_into_supplement(mock_search_service):
    with _patch_saturation_supplement() as mock_supplement:
        fetcher = SearchServiceSaturationFunctionSetIdsFetcher(search_service=mock_search_service)
        await fetcher.get_ids(
            data_partition_id="partition",
            content_type="saturationfunctionset",
            target_schema_version="1.0.0",
            query_date_range=(date(2024, 1, 1), date(2024, 12, 31)),
            wks_parameters={"field_id": "partition:master-data--Field:f-1:"},
        )

    mock_supplement.assert_awaited_once_with(
        result_ids=ANY,
        data_partition_id="partition",
        analysis_family=SATURATION_FUNCTION_SET_STR,
        analysis_type="saturationfunctionset",
        target_schema_version="1.0.0",
        scope={"field_id": "partition:master-data--Field:f-1:"},
    )


@pytest.mark.asyncio
async def test_saturation_function_set_fetcher_passes_none_scope_when_no_wks_parameters(mock_search_service):
    with _patch_saturation_supplement() as mock_supplement:
        fetcher = SearchServiceSaturationFunctionSetIdsFetcher(search_service=mock_search_service)
        await fetcher.get_ids(
            data_partition_id="partition",
            content_type="saturationfunctionset",
            target_schema_version="1.0.0",
            query_date_range=(date(2024, 1, 1), date(2024, 12, 31)),
            wks_parameters=None,
        )

    mock_supplement.assert_awaited_once_with(
        result_ids=ANY,
        data_partition_id="partition",
        analysis_family=SATURATION_FUNCTION_SET_STR,
        analysis_type="saturationfunctionset",
        target_schema_version="1.0.0",
        scope=None,
    )
