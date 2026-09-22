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

"""Row-level pagination (row_limit/row_offset) tests for get_data_v2 (Issue-819).

Split out of data_v2_test.py to keep that module manageable. Covers the Dataset
Service and Blob Storage paths, JSON/Parquet responses, filter/aggregation
interaction, validation, consecutive-page tiling and cache-key distinctness.
"""

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pandas as pd
import pyarrow as pa
import pytest
from httpx import AsyncClient
from starlette import status

from app.api.dependencies.services import (
    get_async_dataset_service,
    get_async_entitlements_service,
    get_async_storage_service,
)
from app.api.routes.samplesanalysis.endpoints import SamplesAnalysisDataView
from app.main import app
from app.services import dataset, entitlements, storage
from tests.test_api.test_routes import dependencies
from tests.test_api.test_routes.data.data_mock_objects import (
    TEST_HEADERS_JSON,
    TEST_HEADERS_PARQUET,
    TEST_SERVER,
)
from tests.test_api.test_routes.osdu.storage_mock_objects import TestContentPathsApiV2

async_storage_record_service_mock = create_autospec(storage.StorageService, spec_set=True, instance=True)
async_dataset_service_mock = create_autospec(dataset.DatasetService, spec_set=True, instance=True)
async_entitlements_service_mock = create_autospec(entitlements.EntitlementsService, spec_set=True, instance=True)

async_entitlements_service_mock.get_groups.return_value = {
    "groups": [{"name": "test-group", "email": "test@example.com"}],
    "desId": "test-user",
}


async def mock_get_async_dataset_service():
    yield async_dataset_service_mock


async def mock_get_async_storage_service():
    yield async_storage_record_service_mock


async def mock_get_async_entitlements_service():
    yield async_entitlements_service_mock


@contextmanager
def services_overrides():
    overrides = {
        get_async_storage_service: mock_get_async_storage_service,
        get_async_dataset_service: mock_get_async_dataset_service,
        get_async_entitlements_service: mock_get_async_entitlements_service,
    }
    with dependencies.DependencyOverrider(app, overrides) as mock_dependencies:
        yield mock_dependencies


def _headers_json(version="1.0.0"):
    return {**TEST_HEADERS_JSON, "Accept": f"*/*;version={version}"}


def _headers_parquet(version="1.0.0"):
    return {**TEST_HEADERS_PARQUET, "Accept": f"application/x-parquet;version={version}"}


def _build_multi_row_parquet(n_rows: int) -> bytes:
    """Build parquet bytes for a simple N-row dataframe.

    GET data does not run pandera/schema validation (only apply_filters_from_bytes),
    so an arbitrary shape is fine for exercising row-level pagination.
    """
    df = pd.DataFrame({"RowId": list(range(n_rows)), "Label": [f"row-{i}" for i in range(n_rows)]})
    return df.to_parquet()


def _rca_get_path():
    from tests.test_api.test_routes.api_v2.routinecoreanalysis import rca_mock_objects

    return f"{TestContentPathsApiV2.RCA}/{rca_mock_objects.TEST_DATASET_RECORD_ID}"


def _rca_record_data():
    from tests.test_api.test_routes.api_v2.routinecoreanalysis import rca_mock_objects

    return rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION


@pytest.mark.asyncio
async def test_get_data_v2_no_pagination_backward_compat():
    """No row_limit/row_offset -> full result, no X-Total-Rows/X-Row-Offset headers."""
    with patch.object(async_storage_record_service_mock, "get_record", side_effect=[_rca_record_data()]):
        with patch.object(async_dataset_service_mock, "download_file", side_effect=[_build_multi_row_parquet(10)]):
            with services_overrides():
                async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                    response = await client.get(_rca_get_path(), headers=_headers_json("1.0.0"))

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()["data"]) == 10
    assert "x-total-rows" not in response.headers
    assert "x-row-offset" not in response.headers


@pytest.mark.asyncio
async def test_get_data_v2_no_pagination_preserves_aggregation_index():
    """Regression test: no row_limit/row_offset must not disturb columns_aggregation's index.

    slice_dataframe() does `iloc(...).reset_index(drop=True)`, which is only a true no-op
    when the DataFrame already has a default RangeIndex. A columns_aggregation result is
    indexed by the aggregation function name (e.g. "count"), so calling slice_dataframe
    unconditionally -- even with the default (None, 0) pagination tuple -- silently
    replaced that label with a fresh RangeIndex, corrupting the "index" field of the
    orient=split response body. This regressed once (fixed by gating slice_dataframe
    behind pagination_active); this test goes through the real get_data_v2 endpoint,
    not slice_dataframe in isolation, so it fails if that call-site guard is ever removed.
    """
    from tests.test_api.test_routes.api_v2.routinecoreanalysis import rca_mock_objects
    from tests.test_api.test_routes.data.data_mock_objects import build_get_test_data

    with patch.object(
        async_storage_record_service_mock,
        "get_record",
        side_effect=[rca_mock_objects.RECORD_DATA_WITH_SCHEMA_VERSION],
    ):
        with patch.object(
            async_dataset_service_mock,
            "download_file",
            side_effect=[build_get_test_data("x-parquet", rca_mock_objects.TEST_DATA)],
        ):
            with services_overrides():
                async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                    response = await client.get(
                        _rca_get_path(),
                        headers=_headers_json("1.0.0"),
                        params=rca_mock_objects.TEST_PARAMS_AGGREGATION,
                    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["index"] == rca_mock_objects.TEST_AGGREGATED_DATA["index"]
    assert "x-total-rows" not in response.headers
    assert "x-row-offset" not in response.headers


@pytest.mark.asyncio
async def test_get_data_v2_active_pagination_with_aggregation_rejected_422():
    """Lead feedback item 5: row_limit/row_offset combined with columns_aggregation
    while pagination is genuinely active must be rejected, not silently accepted.

    Before this fix, ?columns_aggregation=...&row_limit=N returned HTTP 200 with the
    aggregation's index label ("count"/"mean") clobbered to a plain RangeIndex by
    slice_dataframe's reset_index(drop=True) — and ?row_offset=1 on top of an
    aggregation (which always produces exactly one row) silently returned an empty
    body. search/data already rejects this combination with 422
    (GenericSearchDataView._build_result_df_row_paginated); get_data_v2 must be
    consistent rather than silently returning corrupted or empty data with a 200.
    """
    # columns_aggregation is validated against the RCA content schema's declared
    # fields, and then actually applied against the parquet's real columns -- the
    # generic RowId/Label fixture satisfies neither, so build one with a real RCA
    # field instead.
    aggregation_parquet = pd.DataFrame({"NetConfiningStress": [800, 810, 820]}).to_parquet()

    with patch.object(async_storage_record_service_mock, "get_record", side_effect=[_rca_record_data()]):
        with patch.object(async_dataset_service_mock, "download_file", side_effect=[aggregation_parquet]):
            with services_overrides():
                async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                    response = await client.get(
                        _rca_get_path(),
                        headers=_headers_json("1.0.0"),
                        params={"columns_aggregation": "NetConfiningStress,mean", "row_limit": 5},
                    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "columns_aggregation" in response.json()["reason"]


@pytest.mark.asyncio
async def test_get_data_v2_row_limit_applied():
    """?row_limit=3 -> 3 rows, X-Total-Rows present and correct."""
    with patch.object(async_storage_record_service_mock, "get_record", side_effect=[_rca_record_data()]):
        with patch.object(async_dataset_service_mock, "download_file", side_effect=[_build_multi_row_parquet(10)]):
            with services_overrides():
                async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                    response = await client.get(
                        _rca_get_path(),
                        headers=_headers_json("1.0.0"),
                        params={"row_limit": 3},
                    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body["data"]) == 3
    assert [row[0] for row in body["data"]] == [0, 1, 2]
    assert response.headers["x-total-rows"] == "10"
    assert response.headers["x-row-offset"] == "0"


@pytest.mark.asyncio
async def test_get_data_v2_row_offset_applied():
    """?row_offset=5 -> rows from index 5 to the end."""
    with patch.object(async_storage_record_service_mock, "get_record", side_effect=[_rca_record_data()]):
        with patch.object(async_dataset_service_mock, "download_file", side_effect=[_build_multi_row_parquet(10)]):
            with services_overrides():
                async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                    response = await client.get(
                        _rca_get_path(),
                        headers=_headers_json("1.0.0"),
                        params={"row_offset": 5},
                    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert [row[0] for row in body["data"]] == [5, 6, 7, 8, 9]
    assert response.headers["x-total-rows"] == "10"
    assert response.headers["x-row-offset"] == "5"


@pytest.mark.asyncio
async def test_get_data_v2_row_limit_and_offset():
    """?row_limit=3&row_offset=2 -> rows 2-4."""
    with patch.object(async_storage_record_service_mock, "get_record", side_effect=[_rca_record_data()]):
        with patch.object(async_dataset_service_mock, "download_file", side_effect=[_build_multi_row_parquet(10)]):
            with services_overrides():
                async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                    response = await client.get(
                        _rca_get_path(),
                        headers=_headers_json("1.0.0"),
                        params={"row_limit": 3, "row_offset": 2},
                    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert [row[0] for row in body["data"]] == [2, 3, 4]


@pytest.mark.asyncio
async def test_get_data_v2_consecutive_pages_have_no_duplicates_or_gaps():
    """Consecutive windows over a 20-row dataset tile it exactly (Issue-819 acceptance criterion).

    row_offset=0/5/10 with row_limit=5 must return rows 0-4, 5-9 and 10-14: no row
    repeated across pages and none skipped, with a stable X-Total-Rows throughout.
    """
    pages = []
    total_rows_headers = set()
    for row_offset in (0, 5, 10):
        with patch.object(async_storage_record_service_mock, "get_record", side_effect=[_rca_record_data()]):
            with patch.object(async_dataset_service_mock, "download_file", side_effect=[_build_multi_row_parquet(20)]):
                with services_overrides():
                    async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                        response = await client.get(
                            _rca_get_path(),
                            headers=_headers_json("1.0.0"),
                            params={"row_limit": 5, "row_offset": row_offset},
                        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["x-row-offset"] == str(row_offset)
        total_rows_headers.add(response.headers["x-total-rows"])
        pages.append([row[0] for row in response.json()["data"]])

    assert pages == [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9], [10, 11, 12, 13, 14]]
    flattened = [row_id for page in pages for row_id in page]
    assert len(flattened) == len(set(flattened)), "a row was returned on more than one page"
    assert flattened == list(range(15)), "a row was skipped between pages"
    assert total_rows_headers == {"20"}


@pytest.mark.asyncio
async def test_get_data_v2_offset_beyond_data():
    """?row_offset=999 -> empty body, 200 (not 404), X-Total-Rows still reports the real total."""
    with patch.object(async_storage_record_service_mock, "get_record", side_effect=[_rca_record_data()]):
        with patch.object(async_dataset_service_mock, "download_file", side_effect=[_build_multi_row_parquet(10)]):
            with services_overrides():
                async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                    response = await client.get(
                        _rca_get_path(),
                        headers=_headers_json("1.0.0"),
                        params={"row_offset": 999},
                    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"] == []
    assert response.headers["x-total-rows"] == "10"
    assert response.headers["x-row-offset"] == "999"


@pytest.mark.asyncio
async def test_get_data_v2_row_limit_zero_422():
    """?row_limit=0 -> 422 (Query gt=0 constraint)."""
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                _rca_get_path(),
                headers=_headers_json("1.0.0"),
                params={"row_limit": 0},
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_get_data_v2_row_limit_negative_422():
    """?row_limit=-1 -> 422 (Query gt=0 constraint)."""
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                _rca_get_path(),
                headers=_headers_json("1.0.0"),
                params={"row_limit": -1},
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_get_data_v2_row_offset_negative_422():
    """?row_offset=-1 -> 422 (Query ge=0 constraint)."""
    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                _rca_get_path(),
                headers=_headers_json("1.0.0"),
                params={"row_offset": -1},
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_get_data_v2_parquet_response_with_pagination():
    """Accept: application/x-parquet, ?row_limit=2 -> parquet body + X-Total-Rows header."""
    with patch.object(async_storage_record_service_mock, "get_record", side_effect=[_rca_record_data()]):
        with patch.object(async_dataset_service_mock, "download_file", side_effect=[_build_multi_row_parquet(10)]):
            with services_overrides():
                async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                    response = await client.get(
                        _rca_get_path(),
                        headers=_headers_parquet("1.0.0"),
                        params={"row_limit": 2},
                    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["x-total-rows"] == "10"
    roundtrip_df = pd.read_parquet(pa.BufferReader(response.content))
    assert len(roundtrip_df) == 2


@pytest.mark.asyncio
async def test_get_data_v2_blob_path_dynamic_content_type_pagination():
    """use_blob_storage=True routes DynamicContentTypeDataViewV2 through get_parquet_data.

    SamplesAnalysisDataView (RCA) always uses the dataset-service path, so blob-path
    pagination is exercised here through a DynamicContentTypeDataViewV2-backed route
    (fluid model), which is the class that actually branches on settings.use_blob_storage.
    """
    from tests.test_api.test_routes.api_v2.black_oil_fluid_model import black_oil_fluid_model_mock_objects as bofm

    path = f"{TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL}/{bofm.TEST_DATASET_RECORD_ID}"
    mock_settings = MagicMock()
    mock_settings.use_blob_storage = True

    blob_data = pd.DataFrame({"RowId": list(range(6))}).to_parquet()

    with patch("app.api.routes.v2.data.endpoints.get_app_settings", return_value=mock_settings):
        with patch.object(
            async_storage_record_service_mock,
            "get_record",
            side_effect=[bofm.RECORD_DATA_WITH_SCHEMA_VERSION],
        ):
            with patch("app.api.routes.utils.ddms_datasets.find_object_name_index", return_value=0):
                with patch(
                    "app.api.routes.utils.ddms_datasets.check_object_name_schema_version",
                    return_value=None,
                ):
                    from app.api.dependencies.services import get_blob_storage_service
                    from app.providers.dependencies.blob_storage import Blob, BlobMetadata
                    from app.resources.mime_types import SupportedMimeTypes as _BlobMimeTypes

                    blob_obj = Blob(
                        blob_data=blob_data,
                        blob_metadata=BlobMetadata(
                            "fluidmodel", "blackoilfluidmodel", "1.0.0", "uuid-1", _BlobMimeTypes.PARQUET
                        ),
                    )
                    blob_storage_service_mock = AsyncMock()
                    blob_storage_service_mock.get_blob.return_value = blob_obj

                    async def mock_get_blob_storage_service():
                        return blob_storage_service_mock

                    overrides = {
                        get_async_storage_service: mock_get_async_storage_service,
                        get_async_dataset_service: mock_get_async_dataset_service,
                        get_blob_storage_service: mock_get_blob_storage_service,
                    }
                    with dependencies.DependencyOverrider(app, overrides):
                        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                            response = await client.get(
                                path,
                                headers=_headers_json("1.0.0"),
                                params={"row_limit": 3},
                            )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert len(body["data"]) == 3
    assert response.headers["x-total-rows"] == "6"


async def _get_blob_dynamic_content_type_data(params: dict, blob_data: bytes):
    """GET the black-oil fluid model data route through the Blob Storage path."""
    from app.api.dependencies.services import get_blob_storage_service
    from app.providers.dependencies.blob_storage import Blob, BlobMetadata
    from app.resources.mime_types import SupportedMimeTypes as _BlobMimeTypes
    from tests.test_api.test_routes.api_v2.black_oil_fluid_model import black_oil_fluid_model_mock_objects as bofm

    path = f"{TestContentPathsApiV2.BLACK_OIL_FLUID_MODEL}/{bofm.TEST_DATASET_RECORD_ID}"
    mock_settings = MagicMock()
    mock_settings.use_blob_storage = True

    blob_storage_service_mock = AsyncMock()
    blob_storage_service_mock.get_blob.return_value = Blob(
        blob_data=blob_data,
        blob_metadata=BlobMetadata("fluidmodel", "blackoilfluidmodel", "1.0.0", "uuid-1", _BlobMimeTypes.PARQUET),
    )

    async def mock_get_blob_storage_service():
        return blob_storage_service_mock

    overrides = {
        get_async_storage_service: mock_get_async_storage_service,
        get_async_dataset_service: mock_get_async_dataset_service,
        get_blob_storage_service: mock_get_blob_storage_service,
    }
    with patch("app.api.routes.v2.data.endpoints.get_app_settings", return_value=mock_settings):
        with patch.object(
            async_storage_record_service_mock,
            "get_record",
            side_effect=[bofm.RECORD_DATA_WITH_SCHEMA_VERSION],
        ):
            with patch("app.api.routes.utils.ddms_datasets.find_object_name_index", return_value=0):
                with patch("app.api.routes.utils.ddms_datasets.check_object_name_schema_version", return_value=None):
                    with dependencies.DependencyOverrider(app, overrides):
                        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                            return await client.get(path, headers=_headers_json("1.0.0"), params=params)


@pytest.mark.asyncio
@pytest.mark.parametrize("pagination", [{"row_limit": 3}, {"row_offset": 1}, {"row_limit": 3, "row_offset": 1}])
async def test_get_data_v2_blob_path_active_pagination_with_aggregation_rejected_422(pagination):
    """Blob Storage must reject columns_aggregation + row pagination with 422, like the Dataset Service path.

    Without the guard, slice_dataframe's reset_index(drop=True) clobbers the aggregation
    index label ("count"), and any row_offset > 0 drops the single aggregated row entirely.
    """
    blob_data = pd.DataFrame({"FluidModelID": [f"fm-{idx}" for idx in range(6)]}).to_parquet()

    response = await _get_blob_dynamic_content_type_data(
        {"columns_aggregation": "FluidModelID,count", **pagination},
        blob_data,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "columns_aggregation" in response.json()["reason"]
    assert "x-total-rows" not in response.headers


@pytest.mark.asyncio
async def test_get_data_v2_blob_path_aggregation_without_pagination_keeps_index_label():
    """Regression guard: the new 422 must not fire when pagination is inactive."""
    blob_data = pd.DataFrame({"FluidModelID": [f"fm-{idx}" for idx in range(6)]}).to_parquet()

    response = await _get_blob_dynamic_content_type_data({"columns_aggregation": "FluidModelID,count"}, blob_data)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["index"] == ["count"]
    assert "x-total-rows" not in response.headers


@pytest.mark.asyncio
async def test_get_data_v2_row_limit_above_max_422():
    """?row_limit=MAX_ROW_LIMIT_GET_DATA+1 -> 422 (Query le=MAX_ROW_LIMIT_GET_DATA constraint)."""
    from app.api.dependencies.validation import MAX_ROW_LIMIT_GET_DATA

    with services_overrides():
        async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
            response = await client.get(
                _rca_get_path(),
                headers=_headers_json("1.0.0"),
                params={"row_limit": MAX_ROW_LIMIT_GET_DATA + 1},
            )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_get_data_v2_rows_filter_with_row_pagination():
    """rows_filter + row_limit/row_offset together, through the real endpoint.

    Issue-819 requires pagination to apply after rows_filter/columns_filter and
    before serialization -- this proves it end-to-end (not just via slice_dataframe
    in isolation): X-Total-Rows must reflect the post-filter row count, and
    row_limit/row_offset must slice the filtered survivors, not the raw dataset.
    """
    filterable_parquet = pd.DataFrame(
        {"NetConfiningStress": [780, 790, 800, 810, 820], "RowId": [0, 1, 2, 3, 4]},
    ).to_parquet()

    with patch.object(async_storage_record_service_mock, "get_record", side_effect=[_rca_record_data()]):
        with patch.object(async_dataset_service_mock, "download_file", side_effect=[filterable_parquet]):
            with services_overrides():
                async with AsyncClient(base_url=TEST_SERVER, app=app) as client:
                    response = await client.get(
                        _rca_get_path(),
                        headers=_headers_json("1.0.0"),
                        params={"rows_filter": "NetConfiningStress,gte,800", "row_limit": 2},
                    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    # 3 rows survive the filter (NetConfiningStress 800/810/820); row_limit=2 takes the first 2.
    row_id_col = body["columns"].index("RowId")
    assert [row[row_id_col] for row in body["data"]] == [2, 3]
    assert response.headers["x-total-rows"] == "3"
    assert response.headers["x-row-offset"] == "0"


def _pagination_cache_request(query: str, token: str = "Bearer token", partition: str = "opendes"):
    """Build a minimal GET request for the RCA data route, for cache key inspection."""
    from starlette.requests import Request

    path = _rca_get_path()
    return Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "http",
            "server": ("testserver", 80),
            "root_path": "",
            "path": path,
            "raw_path": path.encode(),
            "query_string": query.encode(),
            "headers": [
                (b"authorization", token.encode()),
                (b"data-partition-id", partition.encode()),
            ],
        },
    )


def test_get_data_v2_pagination_cache_distinct_keys():
    """Different row_offset/row_limit windows must resolve to distinct cache keys.

    Caching itself is mocked out for the unit suite (tests/conftest.py), so this
    verifies the precondition: key_builder_using_token hashes the full request URL
    (including query string), so row_limit/row_offset naturally participate in the
    cache key without any special-casing in the pagination code.
    """
    from app.core.helpers.cache.key_builder import key_builder_using_token

    func = SamplesAnalysisDataView.get_data_v2

    def build_key(query: str) -> str:
        with patch("fastapi_cache.FastAPICache.get_prefix", return_value="rafs"):
            return key_builder_using_token(
                func,
                "",
                request=_pagination_cache_request(query),
                response=None,
                args=(),
                kwargs={},
            )

    baseline = build_key("content_schema_version=1.0.0")
    assert build_key("content_schema_version=1.0.0&row_offset=5") != baseline
    assert build_key("content_schema_version=1.0.0&row_limit=10") != baseline
    assert build_key("content_schema_version=1.0.0&row_offset=5&row_limit=10") != build_key(
        "content_schema_version=1.0.0&row_offset=10&row_limit=5",
    )
