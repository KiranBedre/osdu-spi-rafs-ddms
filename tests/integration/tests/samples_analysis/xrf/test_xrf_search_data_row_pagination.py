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

import pytest
from starlette import status

from app.api.dependencies.validation import MAX_ROW_LIMIT_SEARCH_DATA
from app.resources.common_headers import ACCEPT
from tests.integration.config import SamplesAnalysisTypes, SchemaVersions


def _search_data(api, params, **kwargs):
    return api.sample_analysis.search_data(
        analysis_type=SamplesAnalysisTypes.XRF,
        schema_version=SchemaVersions.V1_1_0,
        params=params,
        **kwargs,
    )


def _logical_rows(response):
    result = response["result"]
    return [dict(zip(result["columns"], row)) for row in result["data"]]


def _row_ids(response):
    return [
        (row["SamplesAnalysisID"], row["MassBalance"])
        for row in _logical_rows(response)
    ]


def test_xrf_search_data_row_pages_are_stable_and_cross_datasets(
    api,
    row_pagination_case_v1_1,
):
    """Consecutive row pages tile the stable, cross-dataset logical stream."""
    base_params = row_pagination_case_v1_1["params"]
    record_ids = sorted(row_pagination_case_v1_1["record_ids"])

    full_response = _search_data(api, base_params)
    full_rows = _row_ids(full_response)
    expected_full_rows = [
        (f"{record_id}:", mass_balance)
        for record_id in record_ids
        for mass_balance in (10.0, 20.0, 30.0)
    ]

    assert full_rows == expected_full_rows
    assert full_response["offset"] == 0
    assert full_response["page_limit"] == 100
    assert full_response["total_size"] == 2
    assert not {"row_offset", "row_limit", "total_rows"}.intersection(full_response)

    pages = []
    for row_offset in (0, 2, 4):
        response = _search_data(
            api,
            {**base_params, "row_offset": row_offset, "row_limit": 2},
        )
        assert response["row_offset"] == row_offset
        assert response["row_limit"] == 2
        assert response["total_rows"] == 6
        assert response["total_size"] == 2
        assert "offset" not in response
        assert "page_limit" not in response
        assert len(response["result"]["data"]) <= 2
        pages.extend(_row_ids(response))

    assert len(pages) == len(set(pages))
    assert pages == full_rows

    crossing_page = _search_data(
        api,
        {**base_params, "row_offset": 2, "row_limit": 3},
    )
    assert _row_ids(crossing_page) == full_rows[2:5]
    assert [row_id for row_id, _ in _row_ids(crossing_page)] == [
        f"{record_ids[0]}:",
        f"{record_ids[1]}:",
        f"{record_ids[1]}:",
    ]
    assert _row_ids(
        _search_data(
            api,
            {**base_params, "row_offset": 2, "row_limit": 3},
        ),
    ) == _row_ids(crossing_page)

    legacy_second_dataset = _search_data(
        api,
        {**base_params, "offset": 1, "page_limit": 1},
    )
    assert legacy_second_dataset["offset"] == 1
    assert legacy_second_dataset["page_limit"] == 1
    assert legacy_second_dataset["total_size"] == 2
    assert _row_ids(legacy_second_dataset) == full_rows[3:]


def test_xrf_search_data_row_offset_without_limit_returns_all_remaining_rows(
    api,
    row_pagination_case_v1_1,
):
    """An offset-only request skips rows once across the global stream."""
    base_params = row_pagination_case_v1_1["params"]
    full_rows = _row_ids(_search_data(api, base_params))
    response = _search_data(
        api,
        {**base_params, "row_offset": 2},
        raw=True,
    )
    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert _row_ids(body) == full_rows[2:]
    assert len(_row_ids(body)) == 4
    assert body["row_offset"] == 2
    assert body["row_limit"] is None
    assert body["total_rows"] == 6
    assert body["total_size"] == 2
    assert "offset" not in body
    assert "page_limit" not in body


def test_xrf_search_data_explicit_zero_row_offset_activates_row_mode(
    api,
    row_pagination_case_v1_1,
):
    """Explicit row_offset=0 is row mode rather than omitted pagination."""
    base_params = row_pagination_case_v1_1["params"]
    full_rows = _row_ids(_search_data(api, base_params))
    response = _search_data(
        api,
        {**base_params, "row_offset": 0},
        raw=True,
    )
    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert _row_ids(body) == full_rows
    assert body["row_offset"] == 0
    assert body["row_limit"] is None
    assert body["total_rows"] == 6
    assert body["total_size"] == 2
    assert "offset" not in body
    assert "page_limit" not in body


@pytest.mark.parametrize("row_offset", [6, 7], ids=["at-total", "beyond-total"])
def test_xrf_search_data_row_offset_at_or_beyond_total_returns_empty_page(
    api,
    row_pagination_case_v1_1,
    row_offset,
):
    """Offsets at and beyond total_rows return an empty successful page."""
    response = _search_data(
        api,
        {
            **row_pagination_case_v1_1["params"],
            "row_offset": row_offset,
        },
        raw=True,
    )
    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert _logical_rows(body) == []
    assert body["row_offset"] == row_offset
    assert body["row_limit"] is None
    assert body["total_rows"] == 6
    assert body["total_size"] == 2


def test_xrf_search_data_accepts_maximum_row_limit(
    api,
    row_pagination_case_v1_1,
):
    """The maximum valid row_limit returns the available rows without padding."""
    base_params = row_pagination_case_v1_1["params"]
    full_rows = _row_ids(_search_data(api, base_params))
    response = _search_data(
        api,
        {**base_params, "row_limit": MAX_ROW_LIMIT_SEARCH_DATA},
        raw=True,
    )
    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert _row_ids(body) == full_rows
    assert body["row_offset"] == 0
    assert body["row_limit"] == MAX_ROW_LIMIT_SEARCH_DATA
    assert body["total_rows"] == 6
    assert body["total_size"] == 2


def test_xrf_search_data_filters_rows_before_row_pagination(
    api,
    row_pagination_case_v1_1,
):
    """row_offset and row_limit are evaluated against rows surviving rows_filter."""
    params = {
        **row_pagination_case_v1_1["params"],
        "rows_filter": "MassBalance,gt,10",
    }
    filtered_response = _search_data(api, params)
    filtered_rows = _row_ids(filtered_response)

    assert [mass_balance for _, mass_balance in filtered_rows] == [
        20.0,
        30.0,
        20.0,
        30.0,
    ]

    page = _search_data(
        api,
        {**params, "row_offset": 1, "row_limit": 1},
    )
    assert _row_ids(page) == filtered_rows[1:2]
    assert _row_ids(page)[0][1] == 30.0
    assert page["total_rows"] == 4
    assert page["row_offset"] == 1
    assert page["row_limit"] == 1


def test_xrf_search_data_filtered_offset_at_total_returns_empty_page(
    api,
    row_pagination_case_v1_1,
):
    """Filtered empty-page metadata reflects rows and surviving datasets."""
    record_id = sorted(row_pagination_case_v1_1["record_ids"])[0]
    response = _search_data(
        api,
        {
            **row_pagination_case_v1_1["params"],
            "rows_filter": f"SamplesAnalysisID,eq,{record_id}:",
            "row_offset": 3,
            "row_limit": 2,
        },
        raw=True,
    )
    body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert _logical_rows(body) == []
    assert body["row_offset"] == 3
    assert body["row_limit"] == 2
    assert body["total_rows"] == 3
    assert body["total_size"] == 1


def test_xrf_search_data_row_page_columns_filter_json_parquet_parity(
    api,
    helper,
    row_pagination_case_v1_1,
):
    """Projection preserves the selected rows and JSON/Parquet return the same page."""
    base_params = {
        **row_pagination_case_v1_1["params"],
        "row_offset": 2,
        "row_limit": 3,
    }
    unprojected = _search_data(api, base_params)
    projected = _search_data(
        api,
        {**base_params, "columns_filter": "SamplesAnalysisID,MassBalance"},
    )
    parquet_response = _search_data(
        api,
        {**base_params, "columns_filter": "SamplesAnalysisID,MassBalance"},
        raw=True,
        headers={ACCEPT: "application/x-parquet"},
    )
    parquet_page = helper.load_parquet_data(
        parquet_response.content,
        content_type="parquet",
    )

    assert _row_ids(projected) == _row_ids(unprojected)
    assert projected["result"]["columns"] == ["SamplesAnalysisID", "MassBalance"]
    assert parquet_page == projected["result"]
    assert parquet_response.headers["X-Total-Rows"] == "6"


@pytest.mark.parametrize(
    "params",
    [
        {"row_offset": -1},
        {"row_limit": 0},
        {"row_limit": -1},
        {"row_limit": MAX_ROW_LIMIT_SEARCH_DATA + 1},
        {"row_limit": "not-an-integer"},
        {"row_offset": 1.5},
        {"row_offset": "abc"},
    ],
    ids=[
        "negative-offset",
        "zero-limit",
        "negative-limit",
        "over-max-limit",
        "non-integer-limit",
        "decimal-offset",
        "non-integer-offset",
    ],
)
def test_xrf_search_data_rejects_invalid_row_pagination(api, params):
    response = _search_data(
        api,
        params,
        raw=True,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize(
    "params",
    [
        {"row_limit": 2, "offset": 0},
        {"row_limit": 2, "page_limit": 1},
        {"row_offset": 1, "offset": 0},
        {"row_offset": 1, "page_limit": 1},
    ],
    ids=[
        "row-limit-with-default-offset",
        "row-limit-with-page-limit",
        "row-offset-with-default-offset",
        "row-offset-with-page-limit",
    ],
)
def test_xrf_search_data_rejects_mixed_row_and_dataset_pagination(api, params):
    response = _search_data(
        api,
        params,
        raw=True,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "cannot be combined" in response.text


def test_xrf_search_data_rejects_row_pagination_with_aggregation(api):
    response = _search_data(
        api,
        {
            "columns_aggregation": "MassBalance,mean",
            "row_limit": 1,
        },
        raw=True,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert (
        "row_limit/row_offset cannot be combined with columns_aggregation"
        in response.text
    )
