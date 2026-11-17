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

import copy

import pytest

from app.resources.common_headers import ACCEPT, CACHE_CONTROL
from tests.integration.config import (
    CONFIG,
    DataFiles,
    DataTemplates,
    DataTypes,
    SamplesAnalysisTypes,
    SchemaVersions,
)

JSON_MEDIA_TYPE = "application/json"
PARQUET_MEDIA_TYPE = "application/x-parquet"
ROW_COUNT = 8
ROW_IDS = [f"pagination-row-{number:02d}" for number in range(1, ROW_COUNT + 1)]


@pytest.fixture(scope="module")
def get_data_pagination_case(
    api,
    create_record,
    helper,
    tests_data,
    cce_record_id,
):
    """Create one isolated eight-row Saturation Test dataset."""
    record, _ = create_record(
        DataTypes.SAMPLE_ANALYSIS,
        DataFiles.SAMPLE_ANALYSIS,
        DataTemplates.ID_SAMPLE_ANALYSIS.format(
            partition=CONFIG["DATA_PARTITION"],
        ),
        SamplesAnalysisTypes.SATURATION_TEST,
    )

    payload = copy.deepcopy(tests_data(DataFiles.SATURATION_TEST_DATA_V1))
    column_positions = {
        column: payload["columns"].index(column)
        for column in (
            "SamplesAnalysisID",
            "SourceAnalysisID",
            "TestNumber",
            "Temperature",
            "SaturationPressure",
        )
    }
    base_row = payload["data"][0]
    rows = []
    for number, row_id in enumerate(ROW_IDS, start=1):
        row = copy.deepcopy(base_row)
        row[column_positions["SamplesAnalysisID"]] = f"{record['id']}:"
        row[column_positions["SourceAnalysisID"]] = f"{cce_record_id}:"
        row[column_positions["TestNumber"]] = row_id
        row[column_positions["Temperature"]] = float(100 + number)
        row[column_positions["SaturationPressure"]] = float(1000 + number)
        rows.append(row)

    payload["index"] = list(range(ROW_COUNT))
    payload["data"] = rows
    post_response = api.sample_analysis.post_data(
        record_id=record["id"],
        body=payload,
        analysis_type=SamplesAnalysisTypes.SATURATION_TEST,
        schema_version=SchemaVersions.V1_0_0,
    )

    dataset_id = helper.get_content_id_from_ddms_urn(
        post_response["ddms_urn"],
    )
    yield {
        "record_id": record["id"],
        "dataset_id": dataset_id,
        "payload": payload,
        "row_ids": ROW_IDS,
    }
    api.storage.purge_record(dataset_id)


def _get_data(
    api,
    case,
    params=None,
    accept=JSON_MEDIA_TYPE,
    cache_control=None,
    allowed_codes=None,
):
    headers = {ACCEPT: accept}
    if cache_control is not None:
        headers[CACHE_CONTROL] = cache_control

    return api.sample_analysis.get_data(
        record_id=case["record_id"],
        dataset_id=case["dataset_id"],
        analysis_type=SamplesAnalysisTypes.SATURATION_TEST,
        schema_version=SchemaVersions.V1_0_0,
        params=params or {},
        headers=headers,
        allowed_codes=allowed_codes or [200],
        raw=True,
    )


def _row_ids(split_data):
    position = split_data["columns"].index("TestNumber")
    return [row[position] for row in split_data["data"]]


def _rows_as_dicts(split_data):
    return [dict(zip(split_data["columns"], row)) for row in split_data["data"]]


def _assert_active_pagination_headers(response, total_rows, row_offset):
    assert response.headers["X-Total-Rows"] == str(total_rows)
    assert response.headers["X-Row-Offset"] == str(row_offset)


def _assert_no_pagination_headers(response):
    assert "X-Total-Rows" not in response.headers
    assert "X-Row-Offset" not in response.headers


def _decode_page(helper, response, media_type):
    assert response.headers["Content-Type"].startswith(media_type)
    if media_type == PARQUET_MEDIA_TYPE:
        return helper.load_parquet_data(response.content, content_type="parquet")
    return response.json()


def test_get_data_row_limit_returns_exact_first_rows(
    api,
    get_data_pagination_case,
):
    response = _get_data(
        api,
        get_data_pagination_case,
        params={"row_limit": 3},
    )
    body = response.json()

    assert response.status_code == 200
    assert len(body["data"]) <= 3
    assert _row_ids(body) == ROW_IDS[:3]
    _assert_active_pagination_headers(response, ROW_COUNT, 0)


def test_get_data_positive_row_offset_returns_all_remaining_rows(
    api,
    get_data_pagination_case,
):
    response = _get_data(
        api,
        get_data_pagination_case,
        params={"row_offset": 3},
    )

    assert response.status_code == 200
    assert _row_ids(response.json()) == ROW_IDS[3:]
    _assert_active_pagination_headers(response, ROW_COUNT, 3)


def test_get_data_row_limit_and_offset_return_exact_slice(
    api,
    get_data_pagination_case,
):
    response = _get_data(
        api,
        get_data_pagination_case,
        params={"row_limit": 2, "row_offset": 3},
    )

    assert response.status_code == 200
    assert _row_ids(response.json()) == ROW_IDS[3:5]
    _assert_active_pagination_headers(response, ROW_COUNT, 3)


def test_get_data_consecutive_pages_have_no_gaps_or_duplicates(
    api,
    get_data_pagination_case,
):
    page_size = 3
    returned_ids = []

    for row_offset in range(0, ROW_COUNT, page_size):
        response = _get_data(
            api,
            get_data_pagination_case,
            params={"row_limit": page_size, "row_offset": row_offset},
        )
        returned_ids.extend(_row_ids(response.json()))
        _assert_active_pagination_headers(response, ROW_COUNT, row_offset)

    assert returned_ids == ROW_IDS
    assert len(returned_ids) == len(set(returned_ids))


def test_get_data_tail_page_returns_only_remaining_rows(
    api,
    get_data_pagination_case,
):
    row_limit = 5
    response = _get_data(
        api,
        get_data_pagination_case,
        params={"row_limit": row_limit, "row_offset": 6},
    )
    body = response.json()

    assert response.status_code == 200
    assert _row_ids(body) == ROW_IDS[6:]
    assert len(body["data"]) < row_limit
    _assert_active_pagination_headers(response, ROW_COUNT, 6)


@pytest.mark.parametrize(
    "row_offset",
    [
        pytest.param(ROW_COUNT, id="equal-to-total-rows"),
        pytest.param(ROW_COUNT + 20, id="past-total-rows"),
    ],
)
def test_get_data_offset_at_or_past_end_returns_empty_page(
    api,
    get_data_pagination_case,
    row_offset,
):
    response = _get_data(
        api,
        get_data_pagination_case,
        params={"row_limit": 2, "row_offset": row_offset},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["data"] == []
    assert body["index"] == []
    _assert_active_pagination_headers(response, ROW_COUNT, row_offset)


def test_get_data_applies_rows_filter_before_pagination(
    api,
    get_data_pagination_case,
):
    response = _get_data(
        api,
        get_data_pagination_case,
        params={
            "rows_filter": "Temperature,gte,104",
            "row_offset": 1,
            "row_limit": 2,
        },
    )

    assert response.status_code == 200
    assert _row_ids(response.json()) == ROW_IDS[4:6]
    _assert_active_pagination_headers(response, 5, 1)


def test_get_data_applies_columns_filter_without_changing_page_rows(
    api,
    get_data_pagination_case,
):
    response = _get_data(
        api,
        get_data_pagination_case,
        params={
            "columns_filter": "TestNumber,Temperature",
            "row_offset": 2,
            "row_limit": 3,
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["columns"] == ["TestNumber", "Temperature"]
    assert _row_ids(body) == ROW_IDS[2:5]
    assert [row["Temperature"] for row in _rows_as_dicts(body)] == [
        103.0,
        104.0,
        105.0,
    ]
    _assert_active_pagination_headers(response, ROW_COUNT, 2)


def test_get_data_json_and_parquet_return_same_logical_page(
    api,
    helper,
    get_data_pagination_case,
):
    params = {
        "columns_filter": "TestNumber,Temperature,SaturationPressure",
        "row_offset": 2,
        "row_limit": 3,
    }
    json_response = _get_data(
        api,
        get_data_pagination_case,
        params=params,
        accept=JSON_MEDIA_TYPE,
    )
    parquet_response = _get_data(
        api,
        get_data_pagination_case,
        params=params,
        accept=PARQUET_MEDIA_TYPE,
    )
    json_page = _decode_page(helper, json_response, JSON_MEDIA_TYPE)
    parquet_page = _decode_page(helper, parquet_response, PARQUET_MEDIA_TYPE)

    assert _row_ids(json_page) == ROW_IDS[2:5]
    assert _row_ids(parquet_page) == ROW_IDS[2:5]
    assert _rows_as_dicts(json_page) == _rows_as_dicts(parquet_page)
    _assert_active_pagination_headers(json_response, ROW_COUNT, 2)
    _assert_active_pagination_headers(parquet_response, ROW_COUNT, 2)


def test_get_data_active_pagination_returns_exact_headers(
    api,
    get_data_pagination_case,
):
    response = _get_data(
        api,
        get_data_pagination_case,
        params={"row_limit": 2, "row_offset": 4},
    )

    assert response.status_code == 200
    assert _row_ids(response.json()) == ROW_IDS[4:6]
    _assert_active_pagination_headers(response, ROW_COUNT, 4)


def test_get_data_zero_offset_without_limit_preserves_legacy_response(
    api,
    get_data_pagination_case,
):
    """Treat row_offset=0 without row_limit as a legacy-response no-op."""
    response = _get_data(
        api,
        get_data_pagination_case,
        params={"row_offset": 0},
    )

    assert response.status_code == 200
    assert _row_ids(response.json()) == ROW_IDS
    _assert_no_pagination_headers(response)


@pytest.mark.parametrize(
    "row_limit",
    [
        pytest.param(0, id="zero"),
        pytest.param(-1, id="negative"),
        pytest.param(10001, id="above-maximum"),
        pytest.param("abc", id="non-numeric"),
        pytest.param("1.5", id="non-integer"),
    ],
)
def test_get_data_rejects_invalid_row_limit(
    api,
    get_data_pagination_case,
    row_limit,
):
    response = _get_data(
        api,
        get_data_pagination_case,
        params={"row_limit": row_limit},
        allowed_codes=[422],
    )

    assert response.status_code == 422


def test_get_data_accepts_maximum_row_limit(
    api,
    get_data_pagination_case,
):
    response = _get_data(
        api,
        get_data_pagination_case,
        params={"row_limit": 10000},
    )

    assert response.status_code == 200
    assert _row_ids(response.json()) == ROW_IDS
    _assert_active_pagination_headers(response, ROW_COUNT, 0)


@pytest.mark.parametrize(
    "row_offset",
    [
        pytest.param(-1, id="negative"),
        pytest.param("abc", id="non-numeric"),
        pytest.param("1.5", id="non-integer"),
    ],
)
def test_get_data_rejects_invalid_row_offset(
    api,
    get_data_pagination_case,
    row_offset,
):
    response = _get_data(
        api,
        get_data_pagination_case,
        params={"row_offset": row_offset},
        allowed_codes=[422],
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "pagination",
    [
        pytest.param({"row_limit": 2}, id="row-limit"),
        pytest.param({"row_offset": 1}, id="positive-row-offset"),
        pytest.param(
            {"row_limit": 2, "row_offset": 1},
            id="row-limit-and-offset",
        ),
    ],
)
def test_get_data_rejects_aggregation_with_active_row_pagination(
    api,
    get_data_pagination_case,
    pagination,
):
    response = _get_data(
        api,
        get_data_pagination_case,
        params={
            **pagination,
            "columns_aggregation": "Temperature,mean",
        },
        allowed_codes=[422],
    )

    assert response.status_code == 422


def test_get_data_aggregation_with_noop_zero_offset_preserves_aggregation(
    api,
    get_data_pagination_case,
):
    """Keep aggregation unchanged when row_offset=0 is a pagination no-op."""
    response = _get_data(
        api,
        get_data_pagination_case,
        params={
            "row_offset": 0,
            "columns_aggregation": "Temperature,mean",
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["columns"] == ["Temperature"]
    assert body["index"] == ["mean"]
    assert body["data"][0][0] == pytest.approx(104.5)
    _assert_no_pagination_headers(response)


def test_get_data_without_row_pagination_preserves_legacy_response(
    api,
    get_data_pagination_case,
):
    response = _get_data(api, get_data_pagination_case)
    body = response.json()
    expected = get_data_pagination_case["payload"]

    assert response.status_code == 200
    assert body["columns"] == expected["columns"]
    assert body["index"] == expected["index"]
    assert body["data"] == expected["data"]
    assert _row_ids(body) == ROW_IDS
    _assert_no_pagination_headers(response)


@pytest.mark.parametrize(
    "first_media_type,second_media_type,cache_probe",
    [
        pytest.param(
            JSON_MEDIA_TYPE,
            PARQUET_MEDIA_TYPE,
            "json-then-parquet",
            id="json-then-parquet",
        ),
        pytest.param(
            PARQUET_MEDIA_TYPE,
            JSON_MEDIA_TYPE,
            "parquet-then-json",
            id="parquet-then-json",
        ),
    ],
)
def test_get_data_cache_keeps_content_negotiation_representations_separate(
    api,
    helper,
    get_data_pagination_case,
    first_media_type,
    second_media_type,
    cache_probe,
):
    """Exercise the deployed cache with the same URL in both Accept orders."""
    params = {
        "columns_filter": "TestNumber,Temperature,SaturationPressure",
        "row_offset": 1,
        "row_limit": 2,
        "cache_probe": cache_probe,
    }
    first_response = _get_data(
        api,
        get_data_pagination_case,
        params=params,
        accept=first_media_type,
        cache_control="max-age=60",
    )
    second_response = _get_data(
        api,
        get_data_pagination_case,
        params=params,
        accept=second_media_type,
        cache_control="max-age=60",
    )
    first_page = _decode_page(helper, first_response, first_media_type)
    second_page = _decode_page(helper, second_response, second_media_type)

    assert _row_ids(first_page) == ROW_IDS[1:3]
    assert _row_ids(second_page) == ROW_IDS[1:3]
    assert _rows_as_dicts(first_page) == _rows_as_dicts(second_page)
    _assert_active_pagination_headers(first_response, ROW_COUNT, 1)
    _assert_active_pagination_headers(second_response, ROW_COUNT, 1)


def _search_data(api, case, params, accept=None, cache_control=None, raw=True):
    headers = {}
    if accept is not None:
        headers[ACCEPT] = accept
    if cache_control is not None:
        headers[CACHE_CONTROL] = cache_control

    return api.sample_analysis.search_data(
        analysis_type=SamplesAnalysisTypes.SATURATION_TEST,
        schema_version=SchemaVersions.V1_0_0,
        params={"rows_filter": f"SamplesAnalysisID,eq,{case['record_id']}:", **params},
        raw=raw,
        **({"headers": headers} if headers else {}),
    )


def _decode_search_page(helper, response, media_type):
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith(media_type)
    if media_type == PARQUET_MEDIA_TYPE:
        return helper.load_parquet_data(response.content, content_type="parquet")
    return response.json()["result"]


@pytest.mark.parametrize(
    "first_media_type,second_media_type,cache_probe",
    [
        pytest.param(
            JSON_MEDIA_TYPE,
            PARQUET_MEDIA_TYPE,
            "search-json-then-parquet",
            id="json-then-parquet",
        ),
        pytest.param(
            PARQUET_MEDIA_TYPE,
            JSON_MEDIA_TYPE,
            "search-parquet-then-json",
            id="parquet-then-json",
        ),
    ],
)
def test_search_data_cache_keeps_content_negotiation_representations_separate(
    api,
    helper,
    get_data_pagination_case,
    first_media_type,
    second_media_type,
    cache_probe,
):
    """Exercise the deployed cache on Search Data V2 with the same URL in both Accept orders.

    Both requests of a pair deliberately share one ``cache_probe`` value so that
    they differ only by Accept; pairs are isolated from each other by distinct values.
    """
    helper.wait_for_search_data(
        lambda: _search_data(api, get_data_pagination_case, {}, raw=False),
        get_data_pagination_case["record_id"],
    )
    params = {
        "columns_filter": "TestNumber,Temperature,SaturationPressure",
        "row_offset": 1,
        "row_limit": 2,
        "cache_probe": cache_probe,
    }
    first_response = _search_data(
        api,
        get_data_pagination_case,
        params,
        first_media_type,
        cache_control="max-age=60",
    )
    second_response = _search_data(
        api,
        get_data_pagination_case,
        params,
        second_media_type,
        cache_control="max-age=60",
    )
    first_page = _decode_search_page(helper, first_response, first_media_type)
    second_page = _decode_search_page(helper, second_response, second_media_type)

    assert _row_ids(first_page) == ROW_IDS[1:3]
    assert _row_ids(second_page) == ROW_IDS[1:3]
    assert _rows_as_dicts(first_page) == _rows_as_dicts(second_page)
    json_response = first_response if first_media_type == JSON_MEDIA_TYPE else second_response
    assert json_response.json()["total_rows"] == ROW_COUNT
