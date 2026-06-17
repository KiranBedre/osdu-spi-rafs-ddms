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

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Response
from starlette import status

if not hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT"):
    status.HTTP_422_UNPROCESSABLE_CONTENT = status.HTTP_422_UNPROCESSABLE_ENTITY

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

    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
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
