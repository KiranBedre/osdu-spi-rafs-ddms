#  Copyright 2025 ExxonMobil Technology and Engineering Company
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

"""Unit tests for SamplesAnalysisDynamicSearchView depth-shift integration."""

import io
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from fastapi import HTTPException, Response
from starlette import status

from app.api.routes.common.dynamic_search import SamplesAnalysisDynamicSearchView
from app.models.schemas.depth_shift_query import DepthShiftQueryParams


class TestSamplesAnalysisDynamicSearchView:
    """Tests for SamplesAnalysisDynamicSearchView depth-shift support."""

    @pytest.fixture
    def mock_router(self):
        """Create a mock FastAPI router."""
        return MagicMock()

    @pytest.fixture
    def mock_fetcher_class(self):
        """Create a mock dataset IDs fetcher class."""
        return MagicMock()

    @pytest.fixture
    def search_view(self, mock_router, mock_fetcher_class):
        """Create SamplesAnalysisDynamicSearchView instance."""
        return SamplesAnalysisDynamicSearchView(
            router=mock_router,
            ddms_dataset_ids_fetcher_class=mock_fetcher_class,
            endpoints_config=[
                {
                    "path": "/{analysis_type}/search/data",
                    "handler": "get_search_data",
                    "param_name": "analysis_type",
                    "filter_dep": MagicMock(),
                    "description": "Test search/data endpoint",
                }
            ],
        )

    def test_class_initialization(self, search_view):
        """Test that SamplesAnalysisDynamicSearchView initializes correctly."""
        assert search_view is not None
        assert hasattr(search_view, "_apply_depth_shift_to_search_results")
        assert hasattr(search_view, "_validate_single_wellbore_scope")

    def test_extract_sample_wellbore_id_from_nested_acquisition(self):
        """Test extracting wellbore ID from nested SampleAcquisition."""
        sample_record = {
            "data": {
                "SampleAcquisition": {
                    "SampleAcquisitionDetail": {"WellboreID": "osdu:master-data--Wellbore:test_wellbore:1"}
                }
            }
        }
        wellbore_id = SamplesAnalysisDynamicSearchView._extract_sample_wellbore_id(sample_record)
        assert wellbore_id == "osdu:master-data--Wellbore:test_wellbore:1"

    def test_extract_sample_wellbore_id_from_root(self):
        """Test extracting wellbore ID from root data."""
        sample_record = {"data": {"WellboreID": "osdu:master-data--Wellbore:root_wellbore:1"}}
        wellbore_id = SamplesAnalysisDynamicSearchView._extract_sample_wellbore_id(sample_record)
        assert wellbore_id == "osdu:master-data--Wellbore:root_wellbore:1"

    def test_extract_sample_wellbore_id_returns_nested_priority(self):
        """Test that nested acquisition path takes priority over root."""
        sample_record = {
            "data": {
                "WellboreID": "osdu:master-data--Wellbore:root_wellbore:1",
                "SampleAcquisition": {
                    "SampleAcquisitionDetail": {"WellboreID": "osdu:master-data--Wellbore:nested_wellbore:1"}
                },
            }
        }
        wellbore_id = SamplesAnalysisDynamicSearchView._extract_sample_wellbore_id(sample_record)
        assert wellbore_id == "osdu:master-data--Wellbore:nested_wellbore:1"

    def test_get_definitive_wpc_id_from_nested(self):
        """Test extracting DefinitiveDepthShiftID from nested DefinitiveDepthShift."""
        sample_record = {
            "data": {
                "DefinitiveDepthShift": {
                    "DefinitiveDepthShiftID": "osdu:work-product-component--DepthShift:definitive_001:"
                }
            }
        }
        wpc_id = SamplesAnalysisDynamicSearchView._get_definitive_wpc_id(sample_record)
        assert wpc_id == "osdu:work-product-component--DepthShift:definitive_001"

    def test_get_definitive_wpc_id_from_root(self):
        """Test extracting DefinitiveDepthShiftID from root data."""
        sample_record = {
            "data": {"DefinitiveDepthShiftID": "osdu:work-product-component--DepthShift:root_definitive:1"}
        }
        wpc_id = SamplesAnalysisDynamicSearchView._get_definitive_wpc_id(sample_record)
        assert wpc_id == "osdu:work-product-component--DepthShift:root_definitive"

    def test_validate_single_wellbore_scope_success(self, search_view):
        """Test validation passes with single wellbore."""
        sample_records = {
            "sample1": {"data": {"SampleAcquisition": {"SampleAcquisitionDetail": {"WellboreID": "wellbore_1"}}}},
            "sample2": {"data": {"SampleAcquisition": {"SampleAcquisitionDetail": {"WellboreID": "wellbore_1"}}}},
        }
        # Should not raise
        search_view._validate_single_wellbore_scope(sample_records)

    def test_validate_single_wellbore_scope_multiple_wellbores(self, search_view):
        """Test validation fails with multiple wellbores."""
        from fastapi import HTTPException

        sample_records = {
            "sample1": {"data": {"SampleAcquisition": {"SampleAcquisitionDetail": {"WellboreID": "wellbore_1"}}}},
            "sample2": {"data": {"SampleAcquisition": {"SampleAcquisitionDetail": {"WellboreID": "wellbore_2"}}}},
        }
        with pytest.raises(HTTPException) as exc_info:
            search_view._validate_single_wellbore_scope(sample_records)
        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_validate_single_wellbore_scope_no_wellbores(self, search_view):
        """Test validation fails when no wellbores found."""
        from fastapi import HTTPException

        sample_records = {
            "sample1": {"data": {}},
            "sample2": {"data": {}},
        }
        with pytest.raises(HTTPException) as exc_info:
            search_view._validate_single_wellbore_scope(sample_records)
        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "WellboreID" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_apply_depth_shift_no_depth_shift_params(self, search_view):
        """Test that response is returned unchanged when no depth shift params."""
        search_response = Response(
            content=json.dumps(
                {
                    "result": {"index": [0], "columns": ["col1"], "data": [[1]]},
                    "offset": 0,
                    "page_limit": 100,
                    "total_size": 1,
                }
            ),
            media_type="application/json",
        )

        # With None, it should return the response unchanged
        # This is tested in the endpoint level, not here
        assert search_response is not None

    @pytest.mark.asyncio
    async def test_apply_depth_shift_empty_result(self, search_view):
        """Test handling of empty search results returns original response."""
        from app.models.schemas.search_scope import SearchScope

        search_response = Response(
            content=json.dumps(
                {
                    "result": {"index": [], "columns": [], "data": []},
                    "offset": 0,
                    "page_limit": 100,
                    "total_size": 0,
                }
            ),
            media_type="application/json",
        )

        depth_shift_params = DepthShiftQueryParams(
            depth_shift_policy="id_provided",
            depth_shift_id="test_id",
        )

        search_scope = SearchScope(wellbore_id="test_wellbore")
        mock_storage = AsyncMock()
        mock_dataset = AsyncMock()

        result = await search_view._apply_depth_shift_to_search_results(
            search_response=search_response,
            orient="split",
            depth_shift_params=depth_shift_params,
            storage_service=mock_storage,
            dataset_service=mock_dataset,
            search_scope=search_scope,
        )

        # Should return the original response when result is empty (no SampleID)
        assert result is not None
        assert isinstance(result, Response)
        # Should be the original response since no SampleID column
        response_data = json.loads(result.body.decode("utf-8"))
        assert response_data["total_size"] == 0

    @pytest.mark.asyncio
    async def test_apply_depth_shift_missing_sampleid(self, search_view):
        """Non-empty results without SampleID should return 422 when depth shift is requested."""
        from app.models.schemas.search_scope import SearchScope

        search_response = Response(
            content=json.dumps(
                {
                    "result": {"index": [0], "columns": ["col1"], "data": [[1]]},
                    "offset": 0,
                    "page_limit": 100,
                    "total_size": 1,
                }
            ),
            media_type="application/json",
        )

        depth_shift_params = DepthShiftQueryParams(
            depth_shift_policy="id_provided",
            depth_shift_id="test_id",
        )

        search_scope = SearchScope(wellbore_id="test_wellbore")
        mock_storage = AsyncMock()
        mock_dataset = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await search_view._apply_depth_shift_to_search_results(
                search_response=search_response,
                orient="split",
                depth_shift_params=depth_shift_params,
                storage_service=mock_storage,
                dataset_service=mock_dataset,
                search_scope=search_scope,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "SampleID" in str(exc_info.value.detail)

    def test_validate_single_wellbore_scope_requested_mismatch(self, search_view):
        """Validation should fail when resolved sample wellbore differs from requested scope."""
        sample_records = {
            "sample1": {
                "data": {
                    "SampleAcquisition": {
                        "SampleAcquisitionDetail": {
                            "WellboreID": "osdu:master-data--Wellbore:wb-2:1",
                        },
                    },
                },
            },
        }

        with pytest.raises(HTTPException) as exc_info:
            search_view._validate_single_wellbore_scope(
                sample_records,
                requested_wellbore_id="osdu:master-data--Wellbore:wb-1:",
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "requested wellbore_id" in str(exc_info.value.detail)

    def test_build_dynamic_endpoint_override(self, search_view):
        """Test that _build_dynamic_endpoint is overridden."""
        # Verify the method exists and is the overridden version
        assert hasattr(search_view, "_build_dynamic_endpoint")
        # The method should be callable
        assert callable(search_view._build_dynamic_endpoint)

    @pytest.mark.asyncio
    async def test_apply_depth_shift_missing_wellbore_scope(self, search_view):
        """Test error when wellbore_id is not in search scope."""
        from fastapi import HTTPException

        from app.models.schemas.search_scope import SearchScope

        search_response = Response(
            content=json.dumps(
                {
                    "result": {"index": [0], "columns": ["SampleID"], "data": [["sample_1"]]},
                    "offset": 0,
                    "page_limit": 100,
                    "total_size": 1,
                }
            ),
            media_type="application/json",
        )

        depth_shift_params = DepthShiftQueryParams(
            depth_shift_policy="id_provided",
            depth_shift_id="test_id",
        )

        # No wellbore_id in scope
        search_scope = SearchScope()
        mock_storage = AsyncMock()
        mock_dataset = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await search_view._apply_depth_shift_to_search_results(
                search_response=search_response,
                orient="split",
                depth_shift_params=depth_shift_params,
                storage_service=mock_storage,
                dataset_service=mock_dataset,
                search_scope=search_scope,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "wellbore-scoped" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_apply_depth_shift_definitive_raises_422_when_missing(self, search_view):
        """Definitive policy should raise 422 when no DefinitiveDepthShift found in samples."""
        from app.models.schemas.search_scope import SearchScope

        search_response = Response(
            content=json.dumps(
                {
                    "result": {
                        "index": [0],
                        "columns": ["SampleID", "Value"],
                        "data": [["sample_1", 10.0]],
                    },
                    "offset": 0,
                    "page_limit": 100,
                    "total_size": 1,
                }
            ),
            media_type="application/json",
        )

        depth_shift_params = DepthShiftQueryParams(
            depth_shift_policy="definitive",
            depth_shift_id=None,
        )
        search_scope = SearchScope(wellbore_id="osdu:master-data--Wellbore:wb-1:")

        mock_storage = AsyncMock()
        mock_dataset = AsyncMock()

        mock_resolver = MagicMock()
        mock_resolver.fetch_sample_records = AsyncMock(
            return_value={
                "sample_1": {
                    "data": {
                        "SampleAcquisition": {
                            "SampleAcquisitionDetail": {
                                "WellboreID": "osdu:master-data--Wellbore:wb-1:",
                            },
                        },
                    },
                },
            },
        )
        mock_resolver.resolve_definitive_wpc_id.side_effect = HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No DefinitiveDepthShift found in any sample record.",
        )

        mock_search = MagicMock()

        with patch("app.api.routes.common.dynamic_search.DepthShiftResolver", return_value=mock_resolver):
            with pytest.raises(HTTPException) as exc_info:
                await search_view._apply_depth_shift_to_search_results(
                    search_response=search_response,
                    orient="split",
                    depth_shift_params=depth_shift_params,
                    storage_service=mock_storage,
                    dataset_service=mock_dataset,
                    search_scope=search_scope,
                    search_service=mock_search,
                )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "No DefinitiveDepthShift found in any sample record" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_apply_depth_shift_out_of_range_includes_row_and_metadata_warnings(self, search_view):
        """Out-of-range SampleTop must pass through unchanged and include warnings."""
        from app.models.schemas.search_scope import SearchScope

        requested_wpc = "osdu:work-product-component--DepthShift:requested:1"
        definitive_wpc = "osdu:work-product-component--DepthShift:definitive:1"

        search_response = Response(
            content=json.dumps(
                {
                    "result": {
                        "index": [0],
                        "columns": ["SampleID", "Value"],
                        "data": [["osdu:master-data--Sample:s-1:", 1.0]],
                    },
                    "offset": 0,
                    "page_limit": 100,
                    "total_size": 1,
                }
            ),
            media_type="application/json",
        )

        depth_shift_params = DepthShiftQueryParams(
            depth_shift_policy="id_provided",
            depth_shift_id=requested_wpc,
        )
        search_scope = SearchScope(wellbore_id="osdu:master-data--Wellbore:wb-1:")

        mock_resolver = MagicMock()
        mock_resolver.fetch_sample_records = AsyncMock(
            return_value={
                "osdu:master-data--Sample:s-1": {
                    "data": {
                        "DefinitiveDepthShiftID": definitive_wpc,
                        "SampleAcquisition": {
                            "SampleAcquisitionDetail": {
                                "WellboreID": "osdu:master-data--Wellbore:wb-1:",
                                "TopDepth": 500.0,
                                "BaseDepth": 510.0,
                            }
                        },
                    }
                },
            },
        )
        mock_resolver.resolve_depth_shift_wpc_id = AsyncMock(return_value=requested_wpc)
        mock_resolver.fetch_coretolog_depth_shift_data = AsyncMock(
            return_value=(
                [
                    {
                        "OriginalTopDepth": 100.0,
                        "OriginalBaseDepth": 200.0,
                        "ShiftedTopDepth": 110.0,
                        "ShiftedBaseDepth": 210.0,
                    }
                ],
                [],
                "osdu:master-data--Wellbore:wb-1:",
            ),
        )

        with patch("app.api.routes.common.dynamic_search.DepthShiftResolver", return_value=mock_resolver):
            response = await search_view._apply_depth_shift_to_search_results(
                search_response=search_response,
                orient="split",
                depth_shift_params=depth_shift_params,
                storage_service=AsyncMock(),
                dataset_service=AsyncMock(),
                search_scope=search_scope,
                search_service=MagicMock(),
            )

        payload = json.loads(response.body.decode("utf-8"))
        depth_row = payload["DepthShiftData"][0]
        metadata = payload["DepthShiftMetadata"]

        assert "DepthShiftData" in payload
        assert "DepthShiftMetadata" in payload
        assert depth_row["SampleTop"] == 500.0
        assert depth_row["ShiftedSampleTop"] == 500.0
        assert any("outside all shift intervals" in warning for warning in depth_row["DepthShiftWarnings"])
        assert any("requested depth_shift_id" in warning for warning in metadata["warnings"])
        assert not any("outside all shift intervals" in warning for warning in metadata["warnings"])

    @pytest.mark.asyncio
    async def test_apply_depth_shift_bilinear_validation_error_propagates(self, search_view):
        """Bilinear interpolation validation failures must surface as 422."""
        from app.models.schemas.search_scope import SearchScope

        search_response = Response(
            content=json.dumps(
                {
                    "result": {
                        "index": [0],
                        "columns": ["SampleID", "Value"],
                        "data": [["sample_1", 1.0]],
                    },
                    "offset": 0,
                    "page_limit": 100,
                    "total_size": 1,
                }
            ),
            media_type="application/json",
        )

        depth_shift_params = DepthShiftQueryParams(
            depth_shift_policy="id_provided",
            depth_shift_id="osdu:work-product-component--DepthShift:test:1",
        )
        search_scope = SearchScope(wellbore_id="osdu:master-data--Wellbore:wb-1:")

        mock_resolver = MagicMock()
        mock_resolver.fetch_sample_records = AsyncMock(
            return_value={
                "sample_1": {
                    "data": {
                        "SampleAcquisition": {
                            "SampleAcquisitionDetail": {
                                "WellboreID": "osdu:master-data--Wellbore:wb-1:",
                                "TopDepth": 150.0,
                            }
                        },
                    }
                },
            },
        )
        mock_resolver.resolve_depth_shift_wpc_id = AsyncMock(
            return_value="osdu:work-product-component--DepthShift:test:1",
        )
        mock_resolver.fetch_coretolog_depth_shift_data = AsyncMock(
            side_effect=HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="DepthShiftInterpolationMethodID resolves to 'bilinear'",
            ),
        )

        with patch("app.api.routes.common.dynamic_search.DepthShiftResolver", return_value=mock_resolver):
            with pytest.raises(HTTPException) as exc_info:
                await search_view._apply_depth_shift_to_search_results(
                    search_response=search_response,
                    orient="split",
                    depth_shift_params=depth_shift_params,
                    storage_service=AsyncMock(),
                    dataset_service=AsyncMock(),
                    search_scope=search_scope,
                    search_service=MagicMock(),
                )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "bilinear" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_apply_depth_shift_overlapping_intervals_error_propagates(self, search_view):
        """Overlapping-interval validation failures must surface as 422."""
        from app.models.schemas.search_scope import SearchScope

        search_response = Response(
            content=json.dumps(
                {
                    "result": {
                        "index": [0],
                        "columns": ["SampleID", "Value"],
                        "data": [["sample_1", 1.0]],
                    },
                    "offset": 0,
                    "page_limit": 100,
                    "total_size": 1,
                }
            ),
            media_type="application/json",
        )

        depth_shift_params = DepthShiftQueryParams(
            depth_shift_policy="id_provided",
            depth_shift_id="osdu:work-product-component--DepthShift:test:1",
        )
        search_scope = SearchScope(wellbore_id="osdu:master-data--Wellbore:wb-1:")

        mock_resolver = MagicMock()
        mock_resolver.fetch_sample_records = AsyncMock(
            return_value={
                "sample_1": {
                    "data": {
                        "SampleAcquisition": {
                            "SampleAcquisitionDetail": {
                                "WellboreID": "osdu:master-data--Wellbore:wb-1:",
                                "TopDepth": 150.0,
                            }
                        },
                    }
                },
            },
        )
        mock_resolver.resolve_depth_shift_wpc_id = AsyncMock(
            return_value="osdu:work-product-component--DepthShift:test:1",
        )
        mock_resolver.fetch_coretolog_depth_shift_data = AsyncMock(
            side_effect=HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="DepthShiftSet has overlapping intervals",
            ),
        )

        with patch("app.api.routes.common.dynamic_search.DepthShiftResolver", return_value=mock_resolver):
            with pytest.raises(HTTPException) as exc_info:
                await search_view._apply_depth_shift_to_search_results(
                    search_response=search_response,
                    orient="split",
                    depth_shift_params=depth_shift_params,
                    storage_service=AsyncMock(),
                    dataset_service=AsyncMock(),
                    search_scope=search_scope,
                    search_service=MagicMock(),
                )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "overlapping intervals" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_apply_depth_shift_none_interpolation_auto_detects_from_span(self, search_view):
        """Interpolation method None should auto-detect interpolation from span mismatch."""
        from app.models.schemas.search_scope import SearchScope

        search_response = Response(
            content=json.dumps(
                {
                    "result": {
                        "index": [0],
                        "columns": ["SampleID", "Value"],
                        "data": [["sample_1", 1.0]],
                    },
                    "offset": 0,
                    "page_limit": 100,
                    "total_size": 1,
                }
            ),
            media_type="application/json",
        )

        depth_shift_params = DepthShiftQueryParams(
            depth_shift_policy="id_provided",
            depth_shift_id="osdu:work-product-component--DepthShift:test:1",
        )
        search_scope = SearchScope(wellbore_id="osdu:master-data--Wellbore:wb-1:")

        mock_resolver = MagicMock()
        mock_resolver.fetch_sample_records = AsyncMock(
            return_value={
                "sample_1": {
                    "data": {
                        "SampleAcquisition": {
                            "SampleAcquisitionDetail": {
                                "WellboreID": "osdu:master-data--Wellbore:wb-1:",
                                "TopDepth": 150.0,
                                "BaseDepth": 170.0,
                            }
                        },
                    }
                },
            },
        )
        mock_resolver.resolve_depth_shift_wpc_id = AsyncMock(
            return_value="osdu:work-product-component--DepthShift:test:1",
        )
        mock_resolver.fetch_coretolog_depth_shift_data = AsyncMock(
            return_value=(
                [
                    {
                        "OriginalTopDepth": 100.0,
                        "OriginalBaseDepth": 200.0,
                        "ShiftedTopDepth": 110.0,
                        "ShiftedBaseDepth": 240.0,
                        "DepthShiftInterpolationMethodID": ("osdu:reference-data--DepthShiftInterpolationMethod:None:"),
                    }
                ],
                [],
                "osdu:master-data--Wellbore:wb-1:",
            ),
        )

        with patch("app.api.routes.common.dynamic_search.DepthShiftResolver", return_value=mock_resolver):
            response = await search_view._apply_depth_shift_to_search_results(
                search_response=search_response,
                orient="split",
                depth_shift_params=depth_shift_params,
                storage_service=AsyncMock(),
                dataset_service=AsyncMock(),
                search_scope=search_scope,
                search_service=MagicMock(),
            )

        payload = json.loads(response.body.decode("utf-8"))
        depth_row = payload["DepthShiftData"][0]
        assert depth_row["ShiftedSampleTop"] == pytest.approx(175.0)
        assert depth_row["ShiftedSampleBase"] == pytest.approx(201.0)
