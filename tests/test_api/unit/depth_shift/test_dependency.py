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
    def test_neither_param_returns_none(self):
        result = get_depth_shift_params(
            depth_shift_id=None,
            depth_shift_policy=None,
        )
        assert result is None

    def test_id_provided_policy_with_depth_shift_id_returns_params(self):
        result = get_depth_shift_params(
            depth_shift_id="opendes:work-product-component--DepthShift:ds-001:",
            depth_shift_policy="id_provided",
        )
        assert isinstance(result, DepthShiftQueryParams)
        assert result.depth_shift_id == "opendes:work-product-component--DepthShift:ds-001"
        assert result.depth_shift_policy == "id_provided"
        assert result.is_definitive is False

    def test_definitive_policy_only_returns_params(self):
        result = get_depth_shift_params(
            depth_shift_id=None,
            depth_shift_policy="definitive",
        )
        assert isinstance(result, DepthShiftQueryParams)
        assert result.depth_shift_id is None
        assert result.depth_shift_policy == "definitive"
        assert result.is_definitive is True

    def test_depth_shift_id_without_policy_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            get_depth_shift_params(
                depth_shift_id="ds-001",
                depth_shift_policy=None,
            )
        assert exc_info.value.status_code == 400
        assert "depth_shift_policy" in exc_info.value.detail

    def test_id_provided_policy_without_depth_shift_id_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            get_depth_shift_params(
                depth_shift_id=None,
                depth_shift_policy="id_provided",
            )
        assert exc_info.value.status_code == 400
        assert "depth_shift_id" in exc_info.value.detail

    def test_definitive_policy_with_depth_shift_id_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            get_depth_shift_params(
                depth_shift_id="ds-001",
                depth_shift_policy="definitive",
            )
        assert exc_info.value.status_code == 400
        assert "depth_shift_id" in exc_info.value.detail

    def test_invalid_policy_value_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            get_depth_shift_params(
                depth_shift_id=None,
                depth_shift_policy="unknown_policy",
            )
        assert exc_info.value.status_code == 400
        assert "depth_shift_policy" in exc_info.value.detail
