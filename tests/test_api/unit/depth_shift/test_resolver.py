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

"""Unit tests for DepthShiftResolver.resolve_depth_shift_wpc_id and WPC kind validation."""

from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest
from fastapi import HTTPException

from app.depth_shift.resolver import DepthShiftResolver
from app.models.schemas.depth_shift_query import DepthShiftQueryParams

_SHIFT_INTERVAL = {
    "OriginalTopDepth": 1000.0,
    "OriginalBaseDepth": 1010.0,
    "ShiftedTopDepth": 1001.5,
    "ShiftedBaseDepth": 1011.5,
}


def _parquet_bytes(columns: dict) -> bytes:
    """Build single-row parquet bytes from a column→cell mapping."""
    return pd.DataFrame([columns]).to_parquet()


def _make_resolver(get_record_return=None):
    storage = MagicMock()
    storage.get_record = AsyncMock(return_value=get_record_return or {})
    return DepthShiftResolver(storage_service=storage, dataset_service=MagicMock())


class TestResolveDepthShiftWpcId:
    @pytest.mark.asyncio
    async def test_id_provided_returns_depth_shift_id_without_storage_call(self):
        resolver = _make_resolver()
        params = DepthShiftQueryParams(
            depth_shift_id="ns:work-product-component--DepthShift:abc:",
            depth_shift_policy="id_provided",
        )
        result = await resolver.resolve_depth_shift_wpc_id(params)
        assert result == "ns:work-product-component--DepthShift:abc:"
        resolver._storage.get_record.assert_not_called()


class TestResolveDefinitiveWpcId:
    """Tests for DepthShiftResolver.resolve_definitive_wpc_id."""

    def _resolver(self):
        return DepthShiftResolver(storage_service=MagicMock(), dataset_service=MagicMock())

    def _sample_record(self, wpc_id):
        """Build a minimal sample record with DefinitiveDepthShift set to *wpc_id*."""
        return {"data": {"DefinitiveDepthShift": {"DefinitiveDepthShiftID": wpc_id}}}

    def test_single_sample_with_definitive_returns_wpc_id(self):
        resolver = self._resolver()
        sample_records = {
            "ns:Sample:s-1:": self._sample_record("ns:work-product-component--DepthShift:xyz:"),
        }
        result = resolver.resolve_definitive_wpc_id(sample_records)
        assert result == "ns:work-product-component--DepthShift:xyz:"

    def test_multiple_samples_agreeing_returns_wpc_id(self):
        resolver = self._resolver()
        sample_records = {
            "ns:Sample:s-1:": self._sample_record("ns:work-product-component--DepthShift:xyz:"),
            "ns:Sample:s-2:": self._sample_record("ns:work-product-component--DepthShift:xyz:"),
        }
        result = resolver.resolve_definitive_wpc_id(sample_records)
        assert result == "ns:work-product-component--DepthShift:xyz:"

    def test_no_definitive_depth_shift_raises_422(self):
        resolver = self._resolver()
        sample_records = {
            "ns:Sample:s-1:": {"data": {}},
            "ns:Sample:s-2:": {"data": {}},
        }
        with pytest.raises(HTTPException) as exc_info:
            resolver.resolve_definitive_wpc_id(sample_records)
        assert exc_info.value.status_code == 422
        assert "No DefinitiveDepthShift" in exc_info.value.detail

    def test_samples_disagree_raises_422(self):
        resolver = self._resolver()
        sample_records = {
            "ns:Sample:s-1:": self._sample_record("ns:work-product-component--DepthShift:wpc-1:"),
            "ns:Sample:s-2:": self._sample_record("ns:work-product-component--DepthShift:wpc-2:"),
        }
        with pytest.raises(HTTPException) as exc_info:
            resolver.resolve_definitive_wpc_id(sample_records)
        assert exc_info.value.status_code == 422
        assert "multiple" in exc_info.value.detail.lower()

    def test_empty_sample_records_raises_422(self):
        resolver = self._resolver()
        with pytest.raises(HTTPException) as exc_info:
            resolver.resolve_definitive_wpc_id({})
        assert exc_info.value.status_code == 422

    def test_partial_samples_with_definitive_uses_found_id(self):
        """Samples where some lack DefinitiveDepthShift are ignored; only present ones count."""
        resolver = self._resolver()
        sample_records = {
            "ns:Sample:s-1:": {"data": {}},
            "ns:Sample:s-2:": self._sample_record("ns:work-product-component--DepthShift:xyz:"),
        }
        result = resolver.resolve_definitive_wpc_id(sample_records)
        assert result == "ns:work-product-component--DepthShift:xyz:"


class TestFetchCoretologDepthShiftDataKindValidation:
    """WPC kind guard: non-DepthShift records must be rejected with 400."""

    def _make_resolver_with_dataset(self, wpc_record, parquet_bytes=None):
        storage = MagicMock()
        storage.get_record = AsyncMock(return_value=wpc_record)
        dataset = MagicMock()
        dataset.download_file = AsyncMock(return_value=parquet_bytes or b"")
        return DepthShiftResolver(storage_service=storage, dataset_service=dataset)

    @pytest.mark.asyncio
    async def test_wrong_kind_raises_400(self):
        """A record whose kind is not work-product-component--DepthShift must raise 400."""
        resolver = self._make_resolver_with_dataset(
            {"kind": "opendes:wks:work-product-component--SamplesAnalysis:2.0.0", "data": {}}
        )
        with pytest.raises(HTTPException) as exc_info:
            await resolver.fetch_coretolog_depth_shift_data("opendes:work-product-component--SamplesAnalysis:abc:")
        assert exc_info.value.status_code == 400
        assert "DepthShift WPC" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_missing_kind_raises_400(self):
        """A record with no kind field must also raise 400."""
        resolver = self._make_resolver_with_dataset({"data": {}})
        with pytest.raises(HTTPException) as exc_info:
            await resolver.fetch_coretolog_depth_shift_data("opendes:work-product-component--Unknown:abc:")
        assert exc_info.value.status_code == 400
        assert "DepthShift WPC" in exc_info.value.detail


class TestFetchCoretologDepthShiftDataContent:
    """Happy path and content guards for fetch_coretolog_depth_shift_data."""

    _WPC_ID = "opendes:work-product-component--DepthShift:abc:"

    def _make_resolver(self, wpc_record, parquet_bytes):
        storage = MagicMock()
        storage.get_record = AsyncMock(return_value=wpc_record)
        dataset = MagicMock()
        dataset.download_file = AsyncMock(return_value=parquet_bytes)
        return DepthShiftResolver(storage_service=storage, dataset_service=dataset)

    def _wpc_record(self, wellbore="opendes:master-data--Wellbore:wb-1:"):
        return {
            "kind": "opendes:wks:work-product-component--DepthShift:1.0.0",
            "data": {
                "WellboreID": wellbore,
                "DDMSDatasets": ["opendes:dataset--File.Generic:ds-1:"],
            },
        }

    @pytest.mark.asyncio
    async def test_happy_path_returns_set_meta_and_wellbore(self):
        """Returns (shift_set, shift_meta, shift_wellbore) and fetches WPC once."""
        parquet = _parquet_bytes({"DepthShiftSet": [_SHIFT_INTERVAL], "Meta": [{"unitOfMeasureID": "m"}]})
        resolver = self._make_resolver(self._wpc_record(), parquet)

        shift_set, shift_meta, shift_wellbore = await resolver.fetch_coretolog_depth_shift_data(self._WPC_ID)

        assert shift_set == [_SHIFT_INTERVAL]
        assert shift_meta == [{"unitOfMeasureID": "m"}]
        assert shift_wellbore == "opendes:master-data--Wellbore:wb-1:"
        resolver._storage.get_record.assert_called_once_with(self._WPC_ID)

    @pytest.mark.asyncio
    async def test_missing_wellbore_returns_none(self):
        parquet = _parquet_bytes({"DepthShiftSet": [_SHIFT_INTERVAL]})
        resolver = self._make_resolver(self._wpc_record(wellbore=None), parquet)

        _, _, shift_wellbore = await resolver.fetch_coretolog_depth_shift_data(self._WPC_ID)

        assert shift_wellbore is None

    @pytest.mark.asyncio
    async def test_missing_depth_shift_set_column_raises_400(self):
        parquet = _parquet_bytes({"SomethingElse": [1]})
        resolver = self._make_resolver(self._wpc_record(), parquet)

        with pytest.raises(HTTPException) as exc_info:
            await resolver.fetch_coretolog_depth_shift_data(self._WPC_ID)
        assert exc_info.value.status_code == 400
        assert "missing 'DepthShiftSet'" in exc_info.value.detail


class TestExtractDepthShiftSet:
    """Direct guards on _extract_depth_shift_set (Issue review finding #4)."""

    def _resolver(self):
        return DepthShiftResolver(storage_service=MagicMock(), dataset_service=MagicMock())

    def test_empty_list_raises_400(self):
        resolver = self._resolver()
        df = pd.DataFrame({"DepthShiftSet": [[]]})
        with pytest.raises(HTTPException) as exc_info:
            resolver._extract_depth_shift_set(df, "wpc-1")
        assert exc_info.value.status_code == 400
        assert "empty or invalid" in exc_info.value.detail

    def test_unexpected_scalar_type_raises_400(self):
        resolver = self._resolver()
        df = pd.DataFrame({"DepthShiftSet": [42]})
        with pytest.raises(HTTPException) as exc_info:
            resolver._extract_depth_shift_set(df, "wpc-1")
        assert exc_info.value.status_code == 400
        assert "empty or invalid" in exc_info.value.detail

    def test_valid_list_returned(self):
        resolver = self._resolver()
        df = pd.DataFrame({"DepthShiftSet": [[_SHIFT_INTERVAL]]})
        assert resolver._extract_depth_shift_set(df, "wpc-1") == [_SHIFT_INTERVAL]
