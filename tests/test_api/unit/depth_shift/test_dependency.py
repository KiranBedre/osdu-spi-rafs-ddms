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

"""Unit tests for the get_depth_shift_params FastAPI dependency."""

import pytest
from fastapi import HTTPException

from app.api.dependencies.request import get_depth_shift_params
from app.models.schemas.depth_shift_query import DepthShiftQueryParams


class TestGetDepthShiftParams:
    @pytest.mark.asyncio
    async def test_neither_param_returns_none(self):
        result = await get_depth_shift_params(
            depth_shift_id=None,
            abstract_definitive_depth_shift_id=None,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_depth_shift_id_only_returns_params(self):
        result = await get_depth_shift_params(
            depth_shift_id="opendes:work-product-component--DepthShift:ds-001:",
            abstract_definitive_depth_shift_id=None,
        )
        assert isinstance(result, DepthShiftQueryParams)
        assert result.depth_shift_id == "opendes:work-product-component--DepthShift:ds-001:"
        assert result.abstract_definitive_depth_shift_id is None
        assert result.is_abstract is False

    @pytest.mark.asyncio
    async def test_abstract_id_only_returns_params(self):
        result = await get_depth_shift_params(
            depth_shift_id=None,
            abstract_definitive_depth_shift_id="opendes:work-product-component--AbstractDS:abs-001:",
        )
        assert isinstance(result, DepthShiftQueryParams)
        assert result.depth_shift_id is None
        assert result.abstract_definitive_depth_shift_id == "opendes:work-product-component--AbstractDS:abs-001:"
        assert result.is_abstract is True

    @pytest.mark.asyncio
    async def test_both_params_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            await get_depth_shift_params(
                depth_shift_id="ds-001",
                abstract_definitive_depth_shift_id="abs-001",
            )
        assert exc_info.value.status_code == 400
        assert "only one" in exc_info.value.detail.lower()
