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

from app.exceptions.exceptions import UnprocessableContentException
from app.resources.paths import DEPTH_SHIFT_STR
from app.search.depth_shift_ids_fetcher import SearchServiceDepthShiftIdsFetcher

_NO_RESULTS = {"results": [], "cursor": None}


@pytest.fixture
def mock_search_service():
    search_service = MagicMock()
    search_service.find_records = AsyncMock(return_value=_NO_RESULTS)
    return search_service


def _patch_supplement(return_value=None):
    return patch(
        "app.search.depth_shift_ids_fetcher.supplement_with_pending_writes",
        new=AsyncMock(return_value=return_value or []),
    )


def _make_fetcher(search_service):
    return SearchServiceDepthShiftIdsFetcher(search_service=search_service)


@pytest.mark.asyncio
async def test_get_ids_calls_supplement_with_pending_writes_for_unscoped_search(mock_search_service):
    """Closes lead-feedback Issue #4: depth-shift previously never called
    supplement_with_pending_writes at all (the gap auditor + lead both flagged)."""
    with _patch_supplement() as mock_supplement:
        fetcher = _make_fetcher(mock_search_service)
        await fetcher.get_ids(
            data_partition_id="partition",
            content_type="coretologdepthshift",
            target_schema_version="1.0.0",
            query_date_range=(date(2024, 1, 1), date(2024, 12, 31)),
            wks_parameters=None,
        )

    mock_supplement.assert_awaited_once_with(
        result_ids=ANY,
        data_partition_id="partition",
        analysis_family=DEPTH_SHIFT_STR,
        analysis_type="coretologdepthshift",
        target_schema_version="1.0.0",
        scope=None,
        query_date_range=(date(2024, 1, 1), date(2024, 12, 31)),
    )


@pytest.mark.asyncio
async def test_get_ids_passes_valid_scope_into_supplement(mock_search_service):
    """wellbore_id is a supported depth-shift scope key (SCOPE_PROFILE_DEPTH_SHIFT);
    it must reach supplement_with_pending_writes as a resolved scope dict."""
    with _patch_supplement() as mock_supplement:
        fetcher = _make_fetcher(mock_search_service)
        await fetcher.get_ids(
            data_partition_id="partition",
            content_type="coretologdepthshift",
            target_schema_version="1.0.0",
            query_date_range=(date(2024, 1, 1), date(2024, 12, 31)),
            wks_parameters={"wellbore_id": "partition:master-data--Wellbore:wb-1:"},
        )

    mock_supplement.assert_awaited_once_with(
        result_ids=ANY,
        data_partition_id="partition",
        analysis_family=DEPTH_SHIFT_STR,
        analysis_type="coretologdepthshift",
        target_schema_version="1.0.0",
        scope={"wellbore_id": "partition:master-data--Wellbore:wb-1:"},
        query_date_range=(date(2024, 1, 1), date(2024, 12, 31)),
    )


@pytest.mark.asyncio
async def test_get_ids_surfaces_pending_write_entry_when_search_is_stale(mock_search_service):
    """End-to-end: a depth-shift write followed immediately by a search (Search
    returns no/stale results) must surface the pending entry, the same
    'must not flicker' guarantee already proven for the other three fetchers."""
    with _patch_supplement(return_value=[("dataset-1", "wpc-1")]) as mock_supplement:
        fetcher = _make_fetcher(mock_search_service)
        result = await fetcher.get_ids(
            data_partition_id="partition",
            content_type="coretologdepthshift",
            target_schema_version="1.0.0",
            query_date_range=(date(2024, 1, 1), date(2024, 12, 31)),
            wks_parameters=None,
        )

    assert result == [("dataset-1", "wpc-1")]
    mock_supplement.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_ids_invalid_scope_key_raises_before_any_pending_write_call(mock_search_service):
    """Guards against the strict-validation-bypass risk: an unsupported scope key
    (well_id, which SCOPE_PROFILE_DEPTH_SHIFT does not support — only
    basin_id/field_id/wellbore_id are queryable for depth-shift) must raise
    UnprocessableContentException before supplement_with_pending_writes is ever
    invoked — the pending-write scope must not silently accept what the strict
    query-clause build would reject."""
    with _patch_supplement() as mock_supplement:
        fetcher = _make_fetcher(mock_search_service)
        with pytest.raises(UnprocessableContentException):
            await fetcher.get_ids(
                data_partition_id="partition",
                content_type="coretologdepthshift",
                target_schema_version="1.0.0",
                query_date_range=(date(2024, 1, 1), date(2024, 12, 31)),
                wks_parameters={"well_id": "partition:master-data--Well:w-1:"},
            )

    mock_supplement.assert_not_awaited()
    mock_search_service.find_records.assert_not_awaited()
