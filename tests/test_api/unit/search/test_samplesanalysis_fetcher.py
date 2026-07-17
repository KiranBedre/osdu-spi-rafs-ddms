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
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.search.ddms_dataset_ids_fetcher import SearchServiceSamplesAnalysisTypeIdsFetcher


@pytest.fixture
def mock_search_service():
    return MagicMock()


def _make_fetcher(search_service):
    return SearchServiceSamplesAnalysisTypeIdsFetcher(search_service=search_service)


@pytest.mark.asyncio
async def test_get_ids_with_basin_scope_resolves_sample_hop_first(mock_search_service):
    """When basin_id scope is set the fetcher must first query Sample kind,
    then filter SamplesAnalysis by the resolved sample IDs."""

    # Hop 1: Sample query returns sample IDs from version-agnostic Sample kind search.
    # Hop 2: SamplesAnalysis query returns no datasets (empty result is fine for this test).
    sample_kind_calls = {}

    def find_records_side_effect(**kwargs):
        kind = kwargs.get("kind", "")
        if "master-data--Sample" in kind:
            count = sample_kind_calls.get(kind, 0)
            sample_kind_calls[kind] = count + 1
            if count == 0:
                return {"results": [{"id": "partition:master-data--Sample:s-1:"}], "cursor": None}
            return {"results": [], "cursor": None}
        # SamplesAnalysis query
        return {"results": [], "cursor": None}

    mock_search_service.find_records = AsyncMock(side_effect=find_records_side_effect)

    fetcher = _make_fetcher(mock_search_service)
    result = await fetcher.get_ids(
        data_partition_id="partition",
        analysis_type="routinecoreanalysis",
        target_schema_version="1.0.0",
        query_date_range=(date(2024, 1, 1), date(2024, 12, 31)),
        wks_parameters={"basin_id": "partition:master-data--Basin:b-1:"},
    )

    # Verify Sample kind query was made.
    sample_calls = [
        call for call in mock_search_service.find_records.call_args_list if "master-data--Sample" in str(call)
    ]
    assert len(sample_calls) >= 1, "Expected query against Sample kind"

    # Verify at least one SamplesAnalysis query was made that included SampleIDs filter.
    sa_calls = [call for call in mock_search_service.find_records.call_args_list if "SamplesAnalysis" in str(call)]
    assert len(sa_calls) >= 1
    sa_query = str(sa_calls[0])
    assert "data.SampleIDs" in sa_query
    assert "s-1" in sa_query

    assert result == []


@pytest.mark.asyncio
async def test_get_ids_with_basin_scope_returns_empty_when_no_matching_samples(mock_search_service):
    """When no Sample records match the scope the fetcher must short-circuit and return []."""
    mock_search_service.find_records = AsyncMock(return_value={"results": [], "cursor": None})

    fetcher = _make_fetcher(mock_search_service)
    result = await fetcher.get_ids(
        data_partition_id="partition",
        analysis_type="routinecoreanalysis",
        target_schema_version="1.0.0",
        query_date_range=(None, None),
        wks_parameters={"basin_id": "partition:master-data--Basin:b-1:"},
    )

    assert result == []
    # After the empty Sample responses, the SamplesAnalysis query must NOT be made.
    sa_calls = [call for call in mock_search_service.find_records.call_args_list if "SamplesAnalysis" in str(call)]
    assert len(sa_calls) == 0


@pytest.mark.asyncio
async def test_get_ids_with_well_scope_resolves_three_hop_resolution(mock_search_service):
    """When well_id scope is set, the fetcher must perform 3-hop resolution:
    1. Query Wellbore with well_id → Get wellbore ID
    2. Query Sample with wellbore ID → Get sample IDs
    3. Query SamplesAnalysis with sample IDs → Get analysis IDs"""

    call_count = {"wellbore": 0, "sample": 0, "sa": 0}

    def find_records_side_effect(**kwargs):
        kind = kwargs.get("kind", "")
        if "master-data--Wellbore" in kind:
            # Hop 0: Wellbore query returns one wellbore ID
            count = call_count["wellbore"]
            call_count["wellbore"] += 1
            if count == 0:
                return {"results": [{"id": "partition:master-data--Wellbore:wb-1:"}], "cursor": None}
            return {"results": [], "cursor": None}
        elif "master-data--Sample" in kind:
            # Hop 1: Sample query returns one sample ID
            count = call_count["sample"]
            call_count["sample"] += 1
            if count == 0:
                return {"results": [{"id": "partition:master-data--Sample:s-1:"}], "cursor": None}
            return {"results": [], "cursor": None}
        else:  # SamplesAnalysis
            # Hop 2: SamplesAnalysis query returns no datasets (fine for this test)
            call_count["sa"] += 1
            return {"results": [], "cursor": None}

    mock_search_service.find_records = AsyncMock(side_effect=find_records_side_effect)

    fetcher = _make_fetcher(mock_search_service)
    result = await fetcher.get_ids(
        data_partition_id="partition",
        analysis_type="routinecoreanalysis",
        target_schema_version="1.0.0",
        query_date_range=(date(2024, 1, 1), date(2024, 12, 31)),
        wks_parameters={"well_id": "partition:master-data--Well:w-1:"},
    )

    # Verify Wellbore query was made (hop 0)
    wellbore_calls = [
        call for call in mock_search_service.find_records.call_args_list if "master-data--Wellbore" in str(call)
    ]
    assert len(wellbore_calls) >= 1, "Expected Wellbore query for well_id scope"

    # Verify Sample query was made for resolved wellbore scope (hop 1)
    sample_calls = [
        call for call in mock_search_service.find_records.call_args_list if "master-data--Sample" in str(call)
    ]
    assert len(sample_calls) >= 1, "Expected Sample query for resolved wellbore"

    # Verify SamplesAnalysis query was made with SampleIDs filter (hop 2)
    sa_calls = [call for call in mock_search_service.find_records.call_args_list if "SamplesAnalysis" in str(call)]
    assert len(sa_calls) >= 1, "Expected SamplesAnalysis query"
    sa_query = str(sa_calls[0])
    assert "data.SampleIDs" in sa_query, "Expected SampleIDs filter in SamplesAnalysis query"
    assert "s-1" in sa_query, "Expected resolved sample ID in query"

    assert result == []
