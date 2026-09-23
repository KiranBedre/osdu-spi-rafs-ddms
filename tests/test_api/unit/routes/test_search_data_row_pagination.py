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

"""Unit tests for Issue-820 row-level pagination on GenericSearchDataView.get_search_data.

These tests go through the real `get_search_data` method (the entrypoint FastAPI
wires to `/{analysis_type}/search/data`) — only its declared external
collaborators are mocked: the DDMS dataset-ids fetcher (a constructor
dependency) and `ParquetLoader.read_parquet_files` (network I/O). One test also
goes through `SamplesAnalysisDynamicSearchView`'s dynamic endpoint closure,
which is the actual object FastAPI registers as the route handler for
SamplesAnalysis, to prove `row_pagination_parameters` is threaded from the
closure into `get_search_data` (see app/api/routes/samplesanalysis/dynamic_search.py
and app/api/routes/common/dynamic_search.py).
"""

import asyncio
import io
import json
from typing import List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pandas as pd
import pytest
from fastapi import HTTPException
from pydantic import BaseModel
from starlette import status
from starlette.datastructures import Headers, QueryParams

from app.api.routes.common.base_search import GenericSearchDataView, _in_requested_order
from app.api.routes.samplesanalysis.dynamic_search import SamplesAnalysisDynamicSearchView
from app.dataframe.blob_parquet_loader import BlobParquetLoader
from app.dataframe.parquet_loader import DFPayload, ParquetLoader
from app.models.schemas.search_scope import SearchScope
from app.providers.dependencies.blob_storage import Blob, BlobMetadata
from app.resources.filters import DataFrameFilterValidator
from app.resources.mime_types import SupportedMimeTypes


class _DummyRowModel(BaseModel):
    """Minimal model so DataFrameFilterValidator can build a schema."""

    id: int
    dataset: str


def _df_filter(
    raw_columns_filter: Optional[str] = None,
    raw_rows_filter: Optional[str] = None,
    raw_columns_aggregation: Optional[str] = None,
) -> DataFrameFilterValidator:
    return DataFrameFilterValidator(
        model=_DummyRowModel,
        raw_columns_filter=raw_columns_filter,
        raw_rows_filter=raw_rows_filter,
        raw_columns_aggregation=raw_columns_aggregation,
    )


def _fetcher_class_returning(ids: List[Tuple[str, str]]):
    """Build a fake DDMSDatasetIdsFetcher class returning a fixed id list."""

    class _FakeFetcher(object):
        def __init__(self, search_service):
            self._search_service = search_service

        async def get_ids(self, *args, **kwargs):
            return list(ids)

    return _FakeFetcher


def _dfpayload(dataset_id: str, n_rows: int) -> DFPayload:
    df = pd.DataFrame({"id": list(range(n_rows)), "dataset": [dataset_id] * n_rows})
    return DFPayload(dataset_id, df, None)


def _fake_request(accept: str = "", query_params: Optional[dict] = None) -> MagicMock:
    request = MagicMock()
    # Real header lookups (get_response_mime_type reads "Accept", base_search.py reads
    # "data-partition-id") are case-insensitive via Starlette's Headers — use the real
    # class here too, rather than a plain dict, so casing mismatches can't hide bugs.
    request.headers = Headers({"data-partition-id": "opendes", "Accept": accept})
    # Real QueryParams (not an unconfigured MagicMock) so
    # `"offset" in request.query_params` (the mutual-exclusivity check in
    # GenericSearchDataView._dataset_pagination_explicitly_requested) is actually
    # exercised, not silently mocked around. Empty by default — tests that need to
    # prove offset/page_limit were "explicitly requested" pass query_params explicitly.
    request.query_params = QueryParams(query_params or {})
    return request


def _make_view(ids: List[Tuple[str, str]]) -> GenericSearchDataView:
    return GenericSearchDataView(
        router=MagicMock(),
        ddms_dataset_ids_fetcher_class=_fetcher_class_returning(ids),
        register_default_routes=False,
    )


def _row_query_params(
    row_pagination_parameters: Tuple[Optional[int], int],
    query_params: Optional[dict] = None,
) -> dict:
    """Query string FastAPI would have seen for these resolved row parameters.

    Row mode is detected from query-parameter presence (Issue-820), not from the resolved
    values, so the fake request must carry the parameters a real caller would have sent.
    A resolved `row_offset` of 0 is indistinguishable from "not sent" here, so tests that
    exercise an explicit `?row_offset=0` pass it through `query_params` themselves.
    Explicit `query_params` win over the derived ones.
    """
    row_limit, row_offset = row_pagination_parameters
    derived = {}
    if row_limit is not None:
        derived["row_limit"] = str(row_limit)
    if row_offset:
        derived["row_offset"] = str(row_offset)
    return {**derived, **(query_params or {})}


def _filtering_loader(payloads: List[DFPayload]):
    """Stand-in for `read_parquet_files` that, like the real loaders, applies the request's
    row/column filters to every payload before returning it.

    The plain `AsyncMock(return_value=payloads)` used elsewhere hands the view ready-made
    dataframes, so a `rows_filter` never actually ran in those tests. Use this when the
    test is about filtering happening *before* row pagination.
    """

    async def _read(_loader, _signed_urls, df_filter_processor):
        # Patched onto the class, so it is called as a bound method: (self, signed_urls, processor).
        processor = df_filter_processor.get_filters_without_aggregation()
        return [
            DFPayload(payload.content_id, processor.apply_filters_from_df(payload.df), payload.error_msg)
            for payload in payloads
        ]

    return _read


async def _call_get_search_data(
    view: GenericSearchDataView,
    payloads: List[DFPayload],
    row_pagination_parameters: Tuple[Optional[int], int],
    pagination_parameters: Tuple[int, int, None, None] = (0, 100, None, None),
    df_filter: Optional[DataFrameFilterValidator] = None,
    accept: str = "",
    query_params: Optional[dict] = None,
    apply_filters: bool = False,
):
    read_parquet_files = _filtering_loader(payloads) if apply_filters else AsyncMock(return_value=payloads)
    with patch.object(ParquetLoader, "read_parquet_files", new=read_parquet_files):
        return await view.get_search_data(
            request=_fake_request(accept, query_params=_row_query_params(row_pagination_parameters, query_params)),
            analysis_type="routinecoreanalysis",
            dataset_service=AsyncMock(),
            blob_storage_service=AsyncMock(),
            search_service=MagicMock(),
            df_filter=df_filter or _df_filter(),
            content_schema_version="1.0.0",
            pagination_parameters=pagination_parameters,
            orient="split",
            search_scope=SearchScope(),
            row_pagination_parameters=row_pagination_parameters,
        )


class TestRowPaginationBasics:
    @pytest.mark.asyncio
    async def test_no_row_params_old_behavior_unchanged(self):
        """Default row_pagination_parameters=(None, 0) must not add row fields."""
        ids = [("ds-0", "sa-0")]
        view = _make_view(ids)
        response = await _call_get_search_data(view, [_dfpayload("ds-0", 10)], row_pagination_parameters=(None, 0))

        body = json.loads(response.body)
        assert "row_offset" not in body
        assert "row_limit" not in body
        assert "total_rows" not in body
        assert body["total_size"] == 1

    @pytest.mark.asyncio
    async def test_legacy_envelope_still_carries_dataset_pagination_fields(self):
        """Without row parameters the envelope is exactly the legacy one: offset/page_limit/total_size."""
        view = _make_view([("ds-0", "sa-0")])
        response = await _call_get_search_data(
            view,
            [_dfpayload("ds-0", 10)],
            row_pagination_parameters=(None, 0),
            pagination_parameters=(0, 50, None, None),
        )

        body = json.loads(response.body)
        assert set(body) == {"result", "offset", "page_limit", "total_size"}
        assert body["offset"] == 0
        assert body["page_limit"] == 50

    @pytest.mark.asyncio
    async def test_row_limit_within_single_dataset(self):
        """Single dataset with 50 rows, row_limit=10 -> 10 rows, total_rows=50."""
        ids = [("ds-0", "sa-0")]
        view = _make_view(ids)
        response = await _call_get_search_data(
            view,
            [_dfpayload("ds-0", 50)],
            row_pagination_parameters=(10, 0),
        )

        body = json.loads(response.body)
        assert body["total_rows"] == 50
        assert body["row_limit"] == 10
        assert body["row_offset"] == 0
        assert len(body["result"]["data"]) == 10

    @pytest.mark.asyncio
    async def test_row_offset_within_single_dataset(self):
        """row_offset=5, row_limit=5 -> rows 5-9 of a 20-row dataset."""
        ids = [("ds-0", "sa-0")]
        view = _make_view(ids)
        response = await _call_get_search_data(
            view,
            [_dfpayload("ds-0", 20)],
            row_pagination_parameters=(5, 5),
        )

        body = json.loads(response.body)
        assert body["total_rows"] == 20
        result_ids = [row[body["result"]["columns"].index("id")] for row in body["result"]["data"]]
        assert result_ids == [5, 6, 7, 8, 9]

    @pytest.mark.asyncio
    async def test_row_pagination_cross_dataset_boundary(self):
        """Two 10-row datasets; row_offset=8,row_limit=5 spans both."""
        ids = [("ds-0", "sa-0"), ("ds-1", "sa-1")]
        view = _make_view(ids)
        response = await _call_get_search_data(
            view,
            [_dfpayload("ds-0", 10), _dfpayload("ds-1", 10)],
            row_pagination_parameters=(5, 8),
        )

        body = json.loads(response.body)
        assert body["total_rows"] == 20
        dataset_col = body["result"]["columns"].index("dataset")
        result_datasets = [row[dataset_col] for row in body["result"]["data"]]
        # Rows 8,9 come from ds-0; rows 10,11,12 (index 0,1,2 of ds-1) come from ds-1.
        assert result_datasets == ["ds-0", "ds-0", "ds-1", "ds-1", "ds-1"]

    @pytest.mark.asyncio
    async def test_row_offset_only(self):
        """row_offset=15, no row_limit -> all rows from 15 to the end."""
        ids = [("ds-0", "sa-0")]
        view = _make_view(ids)
        response = await _call_get_search_data(
            view,
            [_dfpayload("ds-0", 20)],
            row_pagination_parameters=(None, 15),
        )

        body = json.loads(response.body)
        assert body["total_rows"] == 20
        assert len(body["result"]["data"]) == 5

    @pytest.mark.asyncio
    async def test_row_pagination_empty_result(self):
        """A dataset page yielding no rows returns total_rows=0, no error."""
        ids = [("ds-0", "sa-0")]
        view = _make_view(ids)
        response = await _call_get_search_data(
            view,
            [_dfpayload("ds-0", 0)],
            row_pagination_parameters=(10, 0),
        )

        body = json.loads(response.body)
        assert body["total_rows"] == 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize("row_offset", [20, 999])
    async def test_row_offset_beyond_total_rows_returns_empty_page(self, row_offset):
        """20 logical rows across two datasets, row_offset >= total_rows -> 200, an empty page and
        the global total_rows.

        Contract for an empty window: `result` is the empty split payload (no index, columns or
        rows: an empty page carries no schema), while `total_rows`, `total_size`, `row_offset`
        and `row_limit` still describe the request and the full result set, so a client paging
        past the end can tell it has run out of rows rather than hit an error.
        """
        view = _make_view([("ds-0", "sa-0"), ("ds-1", "sa-1")])
        response = await _call_get_search_data(
            view,
            [_dfpayload("ds-0", 12), _dfpayload("ds-1", 8)],
            row_pagination_parameters=(10, row_offset),
        )

        assert response.status_code == status.HTTP_200_OK
        body = json.loads(response.body)
        assert body["result"] == {"index": [], "columns": [], "data": []}
        assert body["total_rows"] == 20
        assert body["total_size"] == 2
        assert body["row_offset"] == row_offset
        assert body["row_limit"] == 10

    @pytest.mark.asyncio
    async def test_row_offset_beyond_total_rows_parquet_returns_empty_table(self):
        """Same empty window as Parquet: 200, zero rows, and X-Total-Rows still reports the global count."""
        view = _make_view([("ds-0", "sa-0"), ("ds-1", "sa-1")])
        response = await _call_get_search_data(
            view,
            [_dfpayload("ds-0", 12), _dfpayload("ds-1", 8)],
            row_pagination_parameters=(10, 999),
            accept="application/x-parquet",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["X-Total-Rows"] == "20"
        assert len(pd.read_parquet(io.BytesIO(response.body))) == 0


class TestRowPaginationGlobalSemantics:
    """Row pagination is a single logical row stream across every matching dataset
    (Issue-820 lead feedback) — no dataset-page pre-selection, regardless of the
    (unused, defaulted) legacy offset/page_limit values."""

    @pytest.mark.asyncio
    async def test_row_pagination_traverses_all_matching_datasets_globally(self):
        """total_rows/total_size reflect every matching dataset -- there is no
        dataset-page window to scope them to any more."""
        ids = [("ds-0", "sa-0"), ("ds-1", "sa-1"), ("ds-2", "sa-2")]
        view = _make_view(ids)
        response = await _call_get_search_data(
            view,
            [_dfpayload("ds-0", 10), _dfpayload("ds-1", 10), _dfpayload("ds-2", 10)],
            row_pagination_parameters=(1000, 0),
        )

        body = json.loads(response.body)
        assert body["total_size"] == 3
        assert body["total_rows"] == 30

    @pytest.mark.asyncio
    async def test_consecutive_row_pages_have_no_duplicates_or_gaps(self):
        """row_offset=0/5/10 with row_limit=5 over three 5-row datasets must
        together cover every (dataset, id) pair exactly once."""
        ids = [("ds-0", "sa-0"), ("ds-1", "sa-1"), ("ds-2", "sa-2")]

        seen = []
        for row_offset in (0, 5, 10):
            view = _make_view(ids)
            response = await _call_get_search_data(
                view,
                [_dfpayload("ds-0", 5), _dfpayload("ds-1", 5), _dfpayload("ds-2", 5)],
                row_pagination_parameters=(5, row_offset),
            )
            body = json.loads(response.body)
            dataset_col = body["result"]["columns"].index("dataset")
            id_col = body["result"]["columns"].index("id")
            seen.extend((row[dataset_col], row[id_col]) for row in body["result"]["data"])

        assert len(seen) == 15
        assert len(set(seen)) == 15  # no duplicates across pages
        expected = {(f"ds-{dataset_i}", row_i) for dataset_i in range(3) for row_i in range(5)}
        assert set(seen) == expected  # no gaps across pages

    @pytest.mark.asyncio
    async def test_row_pagination_sparse_datasets_spanning_boundary(self):
        """Sparse datasets (1 / 300 / 2 rows): a window starting near the end of
        the 300-row dataset and ending in the 2-row dataset must span correctly,
        skipping the 1-row dataset via row_offset without ever touching it."""
        ids = [("ds-0", "sa-0"), ("ds-1", "sa-1"), ("ds-2", "sa-2")]
        view = _make_view(ids)
        # Global rows: ds-0 -> [0]; ds-1 -> [1..300]; ds-2 -> [301,302]. Total 303.
        # row_offset=300 skips ds-0 (1 row) and the first 299 of ds-1, landing on
        # ds-1's last row; row_limit=3 then pulls that row plus both of ds-2's.
        response = await _call_get_search_data(
            view,
            [_dfpayload("ds-0", 1), _dfpayload("ds-1", 300), _dfpayload("ds-2", 2)],
            row_pagination_parameters=(3, 300),
        )

        body = json.loads(response.body)
        assert body["total_rows"] == 303
        dataset_col = body["result"]["columns"].index("dataset")
        id_col = body["result"]["columns"].index("id")
        result_pairs = [(row[dataset_col], row[id_col]) for row in body["result"]["data"]]
        assert result_pairs == [("ds-1", 299), ("ds-2", 0), ("ds-2", 1)]

    @pytest.mark.asyncio
    async def test_json_and_parquet_return_same_logical_page(self):
        """Same query/window: orient=split JSON and Parquet must carry identical
        logical row content, not merely the same row count."""
        ids = [("ds-0", "sa-0"), ("ds-1", "sa-1")]

        view_json = _make_view(ids)
        json_response = await _call_get_search_data(
            view_json,
            [_dfpayload("ds-0", 6), _dfpayload("ds-1", 6)],
            row_pagination_parameters=(4, 5),
        )
        view_parquet = _make_view(ids)
        parquet_response = await _call_get_search_data(
            view_parquet,
            [_dfpayload("ds-0", 6), _dfpayload("ds-1", 6)],
            row_pagination_parameters=(4, 5),
            accept="application/x-parquet",
        )

        json_body = json.loads(json_response.body)
        parquet_df = pd.read_parquet(io.BytesIO(parquet_response.body))

        assert list(parquet_df.columns) == json_body["result"]["columns"]
        assert parquet_df.values.tolist() == json_body["result"]["data"]
        assert json_body["total_rows"] == 12
        assert len(parquet_df) == 4

    @pytest.mark.asyncio
    async def test_row_pagination_with_active_filter(self):
        """rows_filter removes rows BEFORE pagination: row offsets are counted on the post-filter stream.

        Two datasets with rows 0..9 and `id,gte,5` leave 5 survivors each, i.e. the logical
        stream is ds-0:5..9 then ds-1:5..9. row_offset=4, row_limit=3 must therefore return
        ds-0:9, ds-1:5, ds-1:6. Computed on the raw rows the same window would be ds-0:4,5,6, so
        this fails if the filter is skipped or applied after slicing. The filter really runs
        here (`apply_filters=True`): a plain mocked loader would hand back unfiltered rows.
        """
        view = _make_view([("ds-0", "sa-0"), ("ds-1", "sa-1")])
        response = await _call_get_search_data(
            view,
            [_dfpayload("ds-0", 10), _dfpayload("ds-1", 10)],
            row_pagination_parameters=(3, 4),
            df_filter=_df_filter(raw_rows_filter="id,gte,5"),
            apply_filters=True,
        )

        body = json.loads(response.body)
        columns = body["result"]["columns"]
        rows = [dict(zip(columns, row)) for row in body["result"]["data"]]
        assert [(row["dataset"], row["id"]) for row in rows] == [("ds-0", 9), ("ds-1", 5), ("ds-1", 6)]
        assert body["total_rows"] == 10
        assert body["total_size"] == 2

    @pytest.mark.asyncio
    async def test_total_size_reflects_filtered_survivors_not_raw_id_count(self):
        """Lead feedback item 1: total_size in the row-paginated branch must match
        _build_result_df's existing semantics (count of datasets that survive
        row/column filtering), not fall back to the raw, unfiltered
        len(analysis_type_ids). Regression test for a bug where total_size was
        always len(analysis_type_ids) whenever row_limit/row_offset were combined
        with a filter that excluded some datasets entirely.

        The real pipeline applies rows_filter/columns_filter while loading each
        dataset's parquet (mocked out here via ParquetLoader.read_parquet_files),
        so — same as the pre-existing _build_result_df tests for this module —
        "survived filtering" is simulated by handing back an already-empty
        DataFrame for the datasets the filter would have excluded (ds-0, ds-2);
        _filter_dfs drops those, leaving only ds-1 as a survivor. total_size
        must be 1, not len(analysis_type_ids) == 3. df_filter still carries a
        real rows_filter so _is_non_empty_filter takes the filtered branch.
        """
        ids = [("ds-0", "sa-0"), ("ds-1", "sa-1"), ("ds-2", "sa-2")]
        view = _make_view(ids)
        response = await _call_get_search_data(
            view,
            [_dfpayload("ds-0", 0), _dfpayload("ds-1", 10), _dfpayload("ds-2", 0)],
            row_pagination_parameters=(100, 0),
            df_filter=_df_filter(raw_rows_filter="id,gte,5"),
        )

        body = json.loads(response.body)
        assert body["total_size"] == 1
        assert body["total_rows"] == 10

    @pytest.mark.asyncio
    async def test_total_size_unchanged_when_no_filter_active(self):
        """No filter -> total_size stays the full id count, matching
        _build_result_df's own no-filter branch (unaffected by the item-1 fix)."""
        ids = [("ds-0", "sa-0"), ("ds-1", "sa-1"), ("ds-2", "sa-2")]
        view = _make_view(ids)
        response = await _call_get_search_data(
            view,
            [_dfpayload("ds-0", 10), _dfpayload("ds-1", 10), _dfpayload("ds-2", 10)],
            row_pagination_parameters=(100, 0),
        )

        body = json.loads(response.body)
        assert body["total_size"] == 3


class TestRowPaginationValidationAndErrors:
    @pytest.mark.asyncio
    async def test_row_pagination_aggregation_conflict_422(self):
        """row_limit + columns_aggregation is rejected with 422."""
        ids = [("ds-0", "sa-0")]
        view = _make_view(ids)

        with pytest.raises(HTTPException) as exc_info:
            await _call_get_search_data(
                view,
                [_dfpayload("ds-0", 10)],
                row_pagination_parameters=(10, 0),
                df_filter=_df_filter(raw_columns_aggregation="id,mean"),
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert "columns_aggregation" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_row_pagination_aggregation_conflict_422_on_blob_path(self):
        """The 422 in `_build_result_df_row_paginated` fires before any dataset traversal,
        so it must reject row_limit + columns_aggregation on the Blob Storage backend too,
        not just the (default-tested) Dataset Service path. `BlobParquetLoader` must never
        even be called, since the conflict is detected before the row stream is consumed."""
        ids = [("blob-0", "sa-0")]
        view = _make_view(ids)
        mock_settings = MagicMock()
        mock_settings.use_blob_storage = True

        with patch("app.api.routes.common.base_search.get_app_settings", return_value=mock_settings):
            with patch.object(
                BlobParquetLoader,
                "read_parquet_files",
                new=AsyncMock(return_value=[_dfpayload("blob-0", 10)]),
            ) as blob_read:
                with pytest.raises(HTTPException) as exc_info:
                    await view.get_search_data(
                        request=_fake_request(query_params={"row_limit": "10"}),
                        analysis_type="routinecoreanalysis",
                        dataset_service=AsyncMock(),
                        blob_storage_service=AsyncMock(),
                        search_service=MagicMock(),
                        df_filter=_df_filter(raw_columns_aggregation="id,mean"),
                        content_schema_version="1.0.0",
                        pagination_parameters=(0, 100, None, None),
                        orient="split",
                        search_scope=SearchScope(),
                        row_pagination_parameters=(10, 0),
                    )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert "columns_aggregation" in exc_info.value.detail
        blob_read.assert_not_called()

    @pytest.mark.asyncio
    async def test_dataset_error_during_row_pagination_returns_500_with_sample_id(self):
        """A dataset that fails to load mid-stream surfaces as a 500 keyed by its sample id,
        not as a silently shortened row window."""
        ids = [("ds-0", "sa-0"), ("ds-1", "sa-1")]
        view = _make_view(ids)
        payloads = [_dfpayload("ds-0", 5), DFPayload("ds-1", pd.DataFrame(), "boom")]

        with pytest.raises(HTTPException) as exc_info:
            await _call_get_search_data(view, payloads, row_pagination_parameters=(3, 0))

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc_info.value.detail == {"errors": {"sa-1": "boom"}}

    @pytest.mark.asyncio
    async def test_explicit_offset_with_row_pagination_returns_422(self):
        """offset explicitly requested (in the query string) + row pagination active -> 422."""
        ids = [("ds-0", "sa-0")]
        view = _make_view(ids)

        with pytest.raises(HTTPException) as exc_info:
            await _call_get_search_data(
                view,
                [_dfpayload("ds-0", 10)],
                row_pagination_parameters=(5, 0),
                pagination_parameters=(1, 100, None, None),
                query_params={"offset": "1"},
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert "row_limit" in exc_info.value.detail
        assert "page_limit" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_explicit_page_limit_with_row_pagination_returns_422(self):
        """page_limit explicitly requested + row pagination active -> 422."""
        ids = [("ds-0", "sa-0")]
        view = _make_view(ids)

        with pytest.raises(HTTPException) as exc_info:
            await _call_get_search_data(
                view,
                [_dfpayload("ds-0", 10)],
                row_pagination_parameters=(None, 5),
                pagination_parameters=(0, 10, None, None),
                query_params={"page_limit": "10"},
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_explicit_row_offset_zero_activates_row_pagination(self):
        """`?row_offset=0` is an explicit row-pagination request even though 0 is the default:
        row mode (row fields, total_rows, no dataset-pagination fields) must be active."""
        view = _make_view([("ds-0", "sa-0")])
        response = await _call_get_search_data(
            view,
            [_dfpayload("ds-0", 10)],
            row_pagination_parameters=(None, 0),
            query_params={"row_offset": "0"},
        )

        body = json.loads(response.body)
        assert body["row_offset"] == 0
        assert body["row_limit"] is None
        assert body["total_rows"] == 10
        assert len(body["result"]["data"]) == 10
        assert "offset" not in body
        assert "page_limit" not in body

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "dataset_param", [{"page_limit": "10"}, {"offset": "0"}, {"offset": "1", "page_limit": "10"}]
    )
    async def test_explicit_row_offset_zero_with_dataset_pagination_returns_422(self, dataset_param):
        """`?row_offset=0&page_limit=10` used to slip past the mutual-exclusivity check because a
        resolved row_offset of 0 looked like "row pagination not requested"."""
        view = _make_view([("ds-0", "sa-0")])

        with pytest.raises(HTTPException) as exc_info:
            await _call_get_search_data(
                view,
                [_dfpayload("ds-0", 10)],
                row_pagination_parameters=(None, 0),
                query_params={"row_offset": "0", **dataset_param},
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert "row_limit" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_explicit_dataset_pagination_without_row_pagination_is_unaffected(self):
        """offset/page_limit explicitly requested, no row pagination -> unaffected
        (the mutual-exclusion check only fires when row pagination is active)."""
        ids = [("ds-0", "sa-0"), ("ds-1", "sa-1")]
        view = _make_view(ids)
        response = await _call_get_search_data(
            view,
            [_dfpayload("ds-1", 10)],
            row_pagination_parameters=(None, 0),
            pagination_parameters=(1, 1, None, None),
            query_params={"offset": "1", "page_limit": "1"},
        )

        body = json.loads(response.body)
        assert "row_offset" not in body
        assert body["offset"] == 1
        assert body["page_limit"] == 1


class TestRowPaginationDeterministicOrdering:
    """Consecutive row pages can only be trusted if the logical row stream has ONE order:
    datasets sorted by (samples analysis id, dataset id), rows in stored order within each."""

    @pytest.mark.asyncio
    async def test_datasets_sharing_an_analysis_id_are_ordered_by_dataset_id(self):
        """Search may return datasets of one analysis in any order; the stream must not depend on it."""
        ids = [("ds-b", "sa-1"), ("ds-a", "sa-1"), ("ds-c", "sa-0")]
        view = _make_view(ids)
        dataset_service = AsyncMock()
        dataset_service.get_signed_urls = AsyncMock(return_value=[])

        with patch.object(ParquetLoader, "read_parquet_files", new=AsyncMock(return_value=[])):
            with patch("app.api.routes.common.base_search.get_app_settings") as settings:
                settings.return_value.use_blob_storage = False
                await view.get_search_data(
                    request=_fake_request(query_params={"row_limit": "5"}),
                    analysis_type="routinecoreanalysis",
                    dataset_service=dataset_service,
                    blob_storage_service=AsyncMock(),
                    search_service=MagicMock(),
                    df_filter=_df_filter(),
                    content_schema_version="1.0.0",
                    pagination_parameters=(0, 100, None, None),
                    orient="split",
                    search_scope=SearchScope(),
                    row_pagination_parameters=(5, 0),
                )

        requested = [call.args[0] for call in dataset_service.get_signed_urls.await_args_list]
        assert requested == [["ds-c", "ds-a", "ds-b"]]

    @pytest.mark.asyncio
    async def test_legacy_dataset_pagination_orders_same_analysis_id_datasets_by_dataset_id(self):
        """Issue-820 lead follow-up: the (analysis id, dataset id) tie-break added for row
        pagination's deterministic stream is applied unconditionally, before either pagination
        mode branches, so it also orders the legacy `offset`/`page_limit` path -- which slices
        this same sorted `analysis_type_ids` list.

        Before Issue-820 the sort key was `analysis_type_id[1]` alone (no tie-break), so datasets
        sharing an analysis id could come back in whatever order the search service happened to
        return them -- already not something a correct caller could rely on, so this is a
        compatibility-safe determinism improvement, not a behavior break. This test pins the new
        order down explicitly for the legacy path too, so it can't silently regress back to
        non-determinism.
        """
        ids = [("ds-b", "sa-1"), ("ds-a", "sa-1"), ("ds-c", "sa-0")]
        view = _make_view(ids)
        dataset_service = AsyncMock()
        dataset_service.get_signed_urls = AsyncMock(return_value=[])

        with patch.object(ParquetLoader, "read_parquet_files", new=AsyncMock(return_value=[])):
            with patch("app.api.routes.common.base_search.get_app_settings") as settings:
                settings.return_value.use_blob_storage = False
                await view.get_search_data(
                    request=_fake_request(),  # no row_limit/row_offset -> legacy dataset pagination
                    analysis_type="routinecoreanalysis",
                    dataset_service=dataset_service,
                    blob_storage_service=AsyncMock(),
                    search_service=MagicMock(),
                    df_filter=_df_filter(),
                    content_schema_version="1.0.0",
                    pagination_parameters=(0, 100, None, None),
                    orient="split",
                    search_scope=SearchScope(),
                    row_pagination_parameters=(None, 0),
                )

        requested = [call.args[0] for call in dataset_service.get_signed_urls.await_args_list]
        assert requested == [["ds-c", "ds-a", "ds-b"]]

    @pytest.mark.asyncio
    async def test_dataset_service_response_order_does_not_reorder_the_stream(self):
        """The Dataset Service may answer in any order; loading must follow the requested order."""
        view = _make_view([])
        dataset_service = AsyncMock()
        dataset_service.get_signed_urls = AsyncMock(
            return_value=[("ds-c", "url-c"), ("ds-a", "url-a"), ("ds-b", "url-b")],
        )
        read_parquet_files = AsyncMock(return_value=[])

        with patch.object(ParquetLoader, "read_parquet_files", new=read_parquet_files):
            async for _batch in view._get_search_data_for_datasets(
                analysis_type_ids=[("ds-a", "sa-0"), ("ds-b", "sa-1"), ("ds-c", "sa-2")],
                dataset_service=dataset_service,
                df_filter=_df_filter(),
            ):
                pass

        loaded = read_parquet_files.await_args.args[0]
        assert loaded == [("ds-a", "url-a"), ("ds-b", "url-b"), ("ds-c", "url-c")]

    @pytest.mark.asyncio
    async def test_dataset_service_multi_dataset_rows_follow_stable_order_under_real_concurrency(self):
        """Dataset Service equivalent of `test_blob_path_multi_dataset_rows_follow_stable_dataset_order`
        above: drives the REAL `ParquetLoader.read_parquet_files` (`asyncio.gather` over concurrent
        per-dataset HTTP reads), not a loader mocked to return pre-built payloads, so an out-of-order
        network completion can't leak into the row stream undetected.

        The Dataset Service answers with the ids scrambled (`_in_requested_order` above only proves
        the *signed_urls list* gets reordered before being handed to the loader); here the HTTP
        response for each dataset also completes in the REVERSE of the stable (analysis id, dataset
        id) order (`ds-b` slowest), so if row order came from completion time rather than
        `asyncio.gather`'s input order, the stream would come out shuffled.
        """
        ids = [("ds-b", "sa-1"), ("ds-c", "sa-1"), ("ds-a", "sa-2")]
        delays = {"ds-b": 0.06, "ds-c": 0.03, "ds-a": 0.0}
        parquet_by_dataset = {ds: pd.DataFrame({"id": [0, 1, 2], "dataset": [ds] * 3}).to_parquet() for ds in delays}

        view = _make_view(ids)
        dataset_service = AsyncMock()
        dataset_service.get_signed_urls = AsyncMock(
            return_value=[
                (dataset_id, f"http://example.com/{dataset_id}")
                for dataset_id in ("ds-a", "ds-c", "ds-b")  # scrambled, not the stable order
            ],
        )

        class _FakeHttpResponse(object):
            def __init__(self, content: bytes):
                self._content = content

            async def aread(self):
                return self._content

            def raise_for_status(self):
                pass

        class _FakeHttpStream(object):
            def __init__(self, content: bytes, delay: float):
                self._content = content
                self._delay = delay

            async def __aenter__(self):
                await asyncio.sleep(self._delay)
                return _FakeHttpResponse(self._content)

            async def __aexit__(self, exc_type, exc, traceback):
                return False

        def fake_stream(_client, _method, url, **_kwargs):
            dataset_id = url.rsplit("/", 1)[-1]
            return _FakeHttpStream(parquet_by_dataset[dataset_id], delays[dataset_id])

        page_datasets = []
        for row_offset in (0, 4, 8):
            with patch.object(httpx.AsyncClient, "stream", new=fake_stream):
                response = await view.get_search_data(
                    request=_fake_request(query_params={"row_limit": "4", "row_offset": str(row_offset)}),
                    analysis_type="routinecoreanalysis",
                    dataset_service=dataset_service,
                    blob_storage_service=AsyncMock(),
                    search_service=MagicMock(),
                    df_filter=_df_filter(),
                    content_schema_version="1.0.0",
                    pagination_parameters=(0, 100, None, None),
                    orient="split",
                    search_scope=SearchScope(),
                    row_pagination_parameters=(4, row_offset),
                )
            body = json.loads(response.body)
            assert body["total_rows"] == 9
            columns = body["result"]["columns"]
            page_datasets.append([dict(zip(columns, row))["dataset"] for row in body["result"]["data"]])

        expected_stream = ["ds-b"] * 3 + ["ds-c"] * 3 + ["ds-a"] * 3
        assert page_datasets == [expected_stream[0:4], expected_stream[4:8], expected_stream[8:9]]
        assert [dataset for page in page_datasets for dataset in page] == expected_stream

    def test_in_requested_order_keeps_unrequested_ids_last_in_relative_order(self):
        signed = [("x", "ux"), ("b", "ub"), ("y", "uy"), ("a", "ua")]

        assert _in_requested_order(signed, ["a", "b"]) == [("a", "ua"), ("b", "ub"), ("x", "ux"), ("y", "uy")]


class TestRowPaginationQueryConstraints:
    """Exercises the real Query(...) constraints on get_row_pagination_parameters
    through FastAPI's dependency-resolution/validation layer -- calling the
    Python function directly (as the other tests in this module do, passing
    row_pagination_parameters as an already-resolved tuple) bypasses Query
    validation entirely, since Query objects are only enforced by FastAPI's
    routing layer. A minimal throwaway app mounting the *real* dependency
    function proves these constraints actually fire, without standing up the
    full search/data route's DDMS/parquet-loader mocking."""

    @staticmethod
    def _probe_client():
        from fastapi import Depends, FastAPI
        from fastapi.testclient import TestClient

        from app.api.dependencies.validation import RowPaginationParameters, get_row_pagination_parameters

        probe_app = FastAPI()

        @probe_app.get("/probe")
        def probe(row_pagination_parameters: RowPaginationParameters = Depends(get_row_pagination_parameters)):
            row_limit, row_offset = row_pagination_parameters
            return {"row_limit": row_limit, "row_offset": row_offset}

        return TestClient(probe_app)

    def test_negative_row_offset_422(self):
        response = self._probe_client().get("/probe", params={"row_offset": -1})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_zero_row_limit_422(self):
        response = self._probe_client().get("/probe", params={"row_limit": 0})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_negative_row_limit_422(self):
        response = self._probe_client().get("/probe", params={"row_limit": -1})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_row_limit_above_max_422(self):
        from app.api.dependencies.validation import MAX_ROW_LIMIT_SEARCH_DATA

        response = self._probe_client().get("/probe", params={"row_limit": MAX_ROW_LIMIT_SEARCH_DATA + 1})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_row_limit_at_max_boundary_200(self):
        """The max itself (not max+1) must be accepted -- `le=MAX_ROW_LIMIT_SEARCH_DATA` is inclusive."""
        from app.api.dependencies.validation import MAX_ROW_LIMIT_SEARCH_DATA

        response = self._probe_client().get("/probe", params={"row_limit": MAX_ROW_LIMIT_SEARCH_DATA})
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"row_limit": MAX_ROW_LIMIT_SEARCH_DATA, "row_offset": 0}

    def test_valid_row_params_200(self):
        response = self._probe_client().get("/probe", params={"row_limit": 10, "row_offset": 5})
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"row_limit": 10, "row_offset": 5}


class TestRowPaginationResponseShapes:
    @pytest.mark.asyncio
    async def test_response_envelope_includes_row_fields(self):
        """JSON envelope carries row_offset/row_limit/total_rows (and total_size) when active,
        and does NOT echo the legacy dataset-pagination fields (Issue-820, lead review)."""
        ids = [("ds-0", "sa-0")]
        view = _make_view(ids)
        response = await _call_get_search_data(
            view,
            [_dfpayload("ds-0", 10)],
            row_pagination_parameters=(3, 2),
        )

        body = json.loads(response.body)
        assert body["row_offset"] == 2
        assert body["row_limit"] == 3
        assert body["total_rows"] == 10
        assert body["total_size"] == 1
        # `offset`/`page_limit` did not select these rows, so the row-mode envelope must not
        # make it look as if both pagination dimensions were active.
        assert "offset" not in body
        assert "page_limit" not in body

    @pytest.mark.asyncio
    async def test_parquet_response_with_row_pagination(self):
        """Accept: application/x-parquet, row_limit=5 -> parquet body + X-Total-Rows header."""
        ids = [("ds-0", "sa-0")]
        view = _make_view(ids)
        response = await _call_get_search_data(
            view,
            [_dfpayload("ds-0", 10)],
            row_pagination_parameters=(5, 0),
            accept="application/x-parquet",
        )

        assert response.headers["x-total-rows"] == "10"
        import io

        roundtrip_df = pd.read_parquet(io.BytesIO(response.body))
        assert len(roundtrip_df) == 5

    @pytest.mark.asyncio
    async def test_blob_path_row_pagination(self):
        """use_blob_storage=True routes through BlobParquetLoader but pagination is unaffected."""
        ids = [("blob-0", "sa-0")]
        view = _make_view(ids)
        mock_settings = MagicMock()
        mock_settings.use_blob_storage = True

        with patch("app.api.routes.common.base_search.get_app_settings", return_value=mock_settings):
            with patch.object(
                BlobParquetLoader,
                "read_parquet_files",
                new=AsyncMock(return_value=[_dfpayload("blob-0", 12)]),
            ):
                response = await view.get_search_data(
                    request=_fake_request(query_params={"row_limit": "4"}),
                    analysis_type="routinecoreanalysis",
                    dataset_service=AsyncMock(),
                    blob_storage_service=AsyncMock(),
                    search_service=MagicMock(),
                    df_filter=_df_filter(),
                    content_schema_version="1.0.0",
                    pagination_parameters=(0, 100, None, None),
                    orient="split",
                    search_scope=SearchScope(),
                    row_pagination_parameters=(4, 0),
                )

        body = json.loads(response.body)
        assert body["total_rows"] == 12
        assert len(body["result"]["data"]) == 4

    @pytest.mark.asyncio
    async def test_blob_path_multi_dataset_rows_follow_stable_dataset_order(self):
        """Blob Storage: rows are produced in the same stable dataset order as the logical row stream.

        Runs the REAL BlobParquetLoader against a fake blob service. The search service returns the
        ids scrambled, so the stable order (samples analysis id, then dataset id) is b, c, a; and
        the blobs complete in the *reverse* of that order (b slowest), so if order came from
        completion time, or from anything but the requested id order, the pages would come out
        shuffled. Consecutive windows must also tile the stream without duplicates or gaps.
        """
        prefix = "fam/type/1.0.0"
        ids = [(f"{prefix}/uuid-c", "sa-1"), (f"{prefix}/uuid-a", "sa-2"), (f"{prefix}/uuid-b", "sa-1")]
        delays = {"uuid-b": 0.06, "uuid-c": 0.03, "uuid-a": 0.0}
        parquet_by_uuid = {uuid: pd.DataFrame({"id": [0, 1, 2], "dataset": [uuid] * 3}).to_parquet() for uuid in delays}

        async def fake_get_blob(blob_metadata):
            await asyncio.sleep(delays[blob_metadata.uuid])
            return Blob(blob_data=parquet_by_uuid[blob_metadata.uuid], blob_metadata=blob_metadata)

        blob_storage_service = MagicMock()
        blob_storage_service.get_blob = AsyncMock(side_effect=fake_get_blob)
        view = _make_view(ids)
        mock_settings = MagicMock()
        mock_settings.use_blob_storage = True

        page_datasets = []
        for row_offset in (0, 4, 8):
            with patch("app.api.routes.common.base_search.get_app_settings", return_value=mock_settings):
                response = await view.get_search_data(
                    request=_fake_request(query_params={"row_limit": "4", "row_offset": str(row_offset)}),
                    analysis_type="routinecoreanalysis",
                    dataset_service=AsyncMock(),
                    blob_storage_service=blob_storage_service,
                    search_service=MagicMock(),
                    df_filter=_df_filter(),
                    content_schema_version="1.0.0",
                    pagination_parameters=(0, 100, None, None),
                    orient="split",
                    search_scope=SearchScope(),
                    row_pagination_parameters=(4, row_offset),
                )
            body = json.loads(response.body)
            assert body["total_rows"] == 9
            columns = body["result"]["columns"]
            page_datasets.append([dict(zip(columns, row))["dataset"] for row in body["result"]["data"]])

        expected_stream = ["uuid-b"] * 3 + ["uuid-c"] * 3 + ["uuid-a"] * 3
        assert page_datasets == [expected_stream[0:4], expected_stream[4:8], expected_stream[8:9]]
        assert [dataset for page in page_datasets for dataset in page] == expected_stream
        # The view asked the blob service for the datasets in the stable order, not the order search returned.
        requested = [call.kwargs["blob_metadata"].uuid for call in blob_storage_service.get_blob.await_args_list[:3]]
        assert requested == ["uuid-b", "uuid-c", "uuid-a"]


class TestDynamicEndpointWiring:
    """Proves row_pagination_parameters flows from the actual registered route
    handler (the dynamic endpoint closure) into get_search_data — not just that
    get_search_data itself accepts the parameter when called directly."""

    @pytest.mark.asyncio
    async def test_dynamic_endpoint_forwards_row_pagination_parameters(self):
        ids = [("ds-0", "sa-0")]
        search_view = SamplesAnalysisDynamicSearchView(
            router=MagicMock(),
            ddms_dataset_ids_fetcher_class=_fetcher_class_returning(ids),
            endpoints_config=[],
        )

        endpoint = search_view._build_dynamic_endpoint(
            method_name="get_search_data",
            extractor=lambda req: "routinecoreanalysis",
            filter_dep=MagicMock(),
        )
        handler = endpoint.__wrapped__ if hasattr(endpoint, "__wrapped__") else endpoint

        request = _fake_request(query_params={"row_limit": "3", "row_offset": "1"})
        request.path_params = {"analysis_type": "routinecoreanalysis"}
        request.url.path = "/routinecoreanalysis/search/data"

        with patch.object(ParquetLoader, "read_parquet_files", new=AsyncMock(return_value=[_dfpayload("ds-0", 9)])):
            response = await handler(
                request=request,
                df_filter=_df_filter(),
                content_schema_version="1.0.0",
                pagination_parameters=(0, 100, None, None),
                search_scope=SearchScope(),
                dataset_service=AsyncMock(),
                blob_storage_service=AsyncMock(),
                search_service=MagicMock(),
                storage_service=AsyncMock(),
                orient="split",
                depth_shift_params=None,
                row_pagination_parameters=(3, 1),
            )

        body = json.loads(response.body)
        assert body["row_limit"] == 3
        assert body["row_offset"] == 1
        assert body["total_rows"] == 9
        assert len(body["result"]["data"]) == 3
