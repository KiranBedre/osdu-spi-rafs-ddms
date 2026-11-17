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

"""Unit tests for SamplesAnalysisDataView depth-shift behavior parity points."""

import io
import json
from inspect import signature
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest
from fastapi import HTTPException, Response
from starlette.requests import Request
from starlette import status

from app.api.routes.samplesanalysis.endpoints import SamplesAnalysisDataView
from app.models.schemas.depth_shift_query import DepthShiftQueryParams


@pytest.fixture
def data_view():
    return SamplesAnalysisDataView(router=MagicMock(), id_regex_str=r".*")


@pytest.mark.asyncio
async def test_run_depth_shift_pipeline_missing_sampleid_returns_422(data_view):
    """Non-empty data without SampleID must return 422 for depth-shift requests."""
    base_response = Response(
        content=json.dumps({"index": [0], "columns": ["Value"], "data": [[1.0]]}),
        media_type="application/json",
    )
    data_view._get_data = AsyncMock(return_value=base_response)

    with pytest.raises(HTTPException) as exc_info:
        await data_view._run_depth_shift_pipeline(
            request=MagicMock(),
            record_id="rid",
            analysis_type="routinecoreanalysis",
            content_id="cid",
            dataset_service=AsyncMock(),
            storage_service=AsyncMock(),
            blob_storage_service=AsyncMock(),
            df_filter=MagicMock(),
            content_schema_version="1.0.0",
            orient="split",
            depth_shift_params=DepthShiftQueryParams(
                depth_shift_policy="id_provided",
                depth_shift_id="osdu:work-product-component--DepthShift:test:1",
            ),
        )

    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "SampleID" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_run_depth_shift_pipeline_empty_results_return_unmodified_response(data_view):
    """Empty responses should be returned unchanged when depth-shift is requested."""
    base_response = Response(
        content=json.dumps({"index": [], "columns": [], "data": []}),
        media_type="application/json",
    )
    data_view._get_data = AsyncMock(return_value=base_response)

    result = await data_view._run_depth_shift_pipeline(
        request=MagicMock(),
        record_id="rid",
        analysis_type="routinecoreanalysis",
        content_id="cid",
        dataset_service=AsyncMock(),
        storage_service=AsyncMock(),
        blob_storage_service=AsyncMock(),
        df_filter=MagicMock(),
        content_schema_version="1.0.0",
        orient="split",
        depth_shift_params=DepthShiftQueryParams(
            depth_shift_policy="id_provided",
            depth_shift_id="osdu:work-product-component--DepthShift:test:1",
        ),
    )

    assert result is base_response


@pytest.mark.asyncio
async def test_depth_shift_parquet_pagination_preserves_binary_response(data_view, monkeypatch):
    """AC-849-1: augment and paginate binary Parquet without JSON decoding."""
    base_df = pd.DataFrame({"SampleID": ["sample-1"] * 3, "TestNumber": ["row-0", "row-1", "row-2"]})
    get_data_signature = signature(data_view._get_data)
    data_view._get_data = AsyncMock(
        return_value=Response(content=base_df.to_parquet(), media_type="application/x-parquet"),
    )
    resolver = MagicMock()
    resolver.fetch_sample_records = AsyncMock(
        return_value={"sample-1": {"data": {"WellboreID": "osdu:master-data--Wellbore:test:"}}},
    )
    resolver.resolve_depth_shift_wpc_id = AsyncMock(return_value="osdu:work-product-component--DepthShift:test:1")
    resolver.fetch_coretolog_depth_shift_data = AsyncMock(return_value=(MagicMock(), {}, "wellbore"))
    monkeypatch.setattr("app.api.routes.samplesanalysis.endpoints.DepthShiftResolver", lambda **kwargs: resolver)
    monkeypatch.setattr(
        "app.api.routes.samplesanalysis.endpoints.resolve_metadata_warning_state",
        lambda **kwargs: (False, []),
    )
    augmented_df = base_df.assign(
        SampleTop=10.0,
        SampleBase=12.0,
        SampleMean=11.0,
        ShiftedSampleTop=11.0,
        ShiftedSampleBase=13.0,
        ShiftedSampleMean=12.0,
        DepthShiftWarnings=[[], [], []],
    )
    monkeypatch.setattr(
        "app.api.routes.samplesanalysis.endpoints.augment_dataframe",
        lambda **kwargs: (augmented_df, []),
    )
    request = Request({"type": "http", "headers": [(b"accept", b"application/x-parquet")]})

    response = await data_view._get_data_with_depth_shift(
        request=request,
        record_id="rid",
        analysis_type="saturation",
        content_id="cid",
        dataset_service=AsyncMock(),
        storage_service=AsyncMock(),
        blob_storage_service=AsyncMock(),
        df_filter=MagicMock(),
        content_schema_version="1.0.0",
        orient="split",
        depth_shift_params=DepthShiftQueryParams(
            depth_shift_policy="id_provided",
            depth_shift_id="osdu:work-product-component--DepthShift:test:1",
        ),
        pagination=(2, 1),
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-parquet"
    result = pd.read_parquet(io.BytesIO(response.body))
    assert result["TestNumber"].tolist() == ["row-1", "row-2"]
    assert result["ShiftedSampleTop"].tolist() == [11.0, 11.0]
    assert response.headers["X-Total-Rows"] == "3"
    assert response.headers["X-Row-Offset"] == "1"
    data_view._get_data.assert_awaited_once()
    base_fetch_args = get_data_signature.bind(*data_view._get_data.call_args.args, **data_view._get_data.call_args.kwargs)
    base_fetch_args.apply_defaults()
    assert base_fetch_args.arguments["pagination"] == (None, 0)


class TestValidateSingleWellboreScopeGetData:
    """_validate_single_wellbore_scope on the get-data view must reject mixed/missing wellbores."""

    _WB = "osdu:master-data--Wellbore:KKS1:"
    _WB2 = "osdu:master-data--Wellbore:NewOne:"

    @pytest.fixture
    def view(self):
        return SamplesAnalysisDataView(router=MagicMock(), id_regex_str=r".*")

    @staticmethod
    def _record(wellbore_id):
        if wellbore_id is None:
            return {"data": {}}
        return {"data": {"WellboreID": wellbore_id}}

    def test_single_wellbore_passes(self, view):
        records = {"s0": self._record(self._WB), "s1": self._record(self._WB)}
        view._validate_single_wellbore_scope(records)  # must not raise

    def test_multiple_wellbores_raises_422(self, view):
        records = {"s0": self._record(self._WB), "s1": self._record(self._WB2)}
        with pytest.raises(HTTPException) as exc_info:
            view._validate_single_wellbore_scope(records)
        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "multiple WellboreIDs" in exc_info.value.detail

    def test_one_sample_missing_wellbore_raises_422(self, view):
        records = {"s0": self._record(self._WB), "s1": self._record(None)}
        with pytest.raises(HTTPException) as exc_info:
            view._validate_single_wellbore_scope(records)
        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Missing WellboreID" in exc_info.value.detail
        assert "s1" in exc_info.value.detail

    def test_all_samples_missing_wellbore_raises_422(self, view):
        records = {"s0": self._record(None), "s1": self._record(None)}
        with pytest.raises(HTTPException) as exc_info:
            view._validate_single_wellbore_scope(records)
        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Missing WellboreID" in exc_info.value.detail
