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
import datetime

import pytest
from starlette import status

from app.resources.common_headers import ACCEPT
from tests.integration.config import DataFiles, SchemaVersions


def test_compositional_search_record_filtered_in_by_row(
    api, helper, record_id, dataset_id, fluid_model_type
):
    """Verify record appears in search results after indexing completes."""
    params = {"rows_filter": f"FluidModelID,eq,{record_id}:"}

    # Wait until search returns the record_id in its result set
    response = helper.wait_for_search_record(
        lambda: api.fluid_model.search_records(
            fluid_model_type=fluid_model_type,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        ),
        record_id,
    )

    # Assert
    assert record_id in response["result"]
    assert response["offset"] == 0
    assert response["page_limit"] == 1000
    assert response["total_size"] == 1


def test_compositional_search_record_filtered_out_by_row(
    api, record_id, dataset_id, search_available, fluid_model_type
):
    """Verify record is filtered out by the specified row filter in the search results"""
    params = {"rows_filter": "FluidModelID,eq,DummyValue"}
    response = api.fluid_model.search_records(
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )

    # Assert
    assert response["result"] == []
    assert response["total_size"] == 0


def test_compositional_search_record_filtered_in_by_start_date(
    api, record_id, dataset_id, search_available, fluid_model_type
):
    """Verify record is filtered in by the specified start date filter in the search results"""
    current_date = datetime.date.today()
    params = {
        "indexed_start_date": current_date,
        "rows_filter": f"FluidModelID,eq,{record_id}:",
    }
    response = api.fluid_model.search_records(
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )

    # Assert
    assert record_id in response["result"]


def test_compositional_search_record_filtered_out_by_start_date(
    api, record_id, dataset_id, search_available, fluid_model_type
):
    """Verify record is filtered out by the specified start date filter in the search results"""
    current_date = datetime.date.today()
    tomorrow_date = current_date + datetime.timedelta(days=1)
    params = {
        "indexed_start_date": tomorrow_date,
        "rows_filter": f"FluidModelID,eq,{record_id}:",
    }
    response = api.fluid_model.search_records(
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )

    # Assert
    assert response["result"] == []


def test_compositional_search_record_filtered_in_by_end_date(
    api, record_id, dataset_id, search_available, fluid_model_type
):
    """Verify record is filtered in by the specified end date filter in the search results"""
    current_date = datetime.date.today()
    params = {
        "indexed_end_date": current_date,
        "rows_filter": f"FluidModelID,eq,{record_id}:",
    }
    response = api.fluid_model.search_records(
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )

    # Assert
    assert record_id in response["result"]


def test_compositional_search_record_filtered_out_by_end_date(
    api, record_id, dataset_id, search_available, fluid_model_type
):
    """Verify record is filtered out by the specified end date filter in the search results"""
    current_date = datetime.date.today()
    yesterday_date = current_date - datetime.timedelta(days=1)
    params = {
        "indexed_end_date": yesterday_date,
        "rows_filter": f"FluidModelID,eq,{record_id}:",
    }
    response = api.fluid_model.search_records(
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )

    # Assert
    assert record_id not in response["result"]


def test_compositional_search_record_filtered_out_by_page_limit(
    api, helper, pagination_case, fluid_model_type
):
    """Verify records are filtered out by the specified page limit filter in the search results"""
    helper.verify_record_pagination(
        lambda params: api.fluid_model.search_records(
            fluid_model_type=fluid_model_type,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        ),
        pagination_case,
    )


def test_compositional_search_record_query_schema_version_takes_priority_over_accept_header(
    api,
    record_id,
    dataset_id,
    search_available,
    fluid_model_type,
):
    """Verify content_schema_version query parameter overrides deprecated Accept versioning."""
    params = {"rows_filter": f"FluidModelID,eq,{record_id}:"}
    response = api.fluid_model.search_records(
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={ACCEPT: "application/json;version=9.9.9"},
        params=params,
        raw=True,
    )

    # Assert
    assert response.status_code == 200
    assert "Deprecation" not in response.headers
    assert record_id in response.json()["result"]


@pytest.mark.parametrize("malformed_schema_version", ["abc", "1.x"])
def test_compositional_search_record_malformed_schema_version(
    api,
    fluid_model_type,
    malformed_schema_version,
):
    """Reject malformed content_schema_version query parameter with 422."""
    response = api.fluid_model.search_records(
        fluid_model_type=fluid_model_type,
        schema_version=malformed_schema_version,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert (
        f"Invalid version format in content_schema_version: '{malformed_schema_version}'. "
        "Expected format: major.minor.patch (e.g. 1.0.0)"
    ) in body["reason"]


def test_compositional_search_record_missing_schema_version(api, fluid_model_type):
    """Reject Compositional search when neither query nor Accept header supplies a schema version."""
    response = api.fluid_model.search_records(
        fluid_model_type=fluid_model_type,
        schema_version=None,
        headers={ACCEPT: None},
        allowed_codes=[status.HTTP_406_NOT_ACCEPTABLE],
        raw=True,
    )

    # Assert
    assert response.status_code == 406
    body = response.json()
    assert (
        "No schema version specified or invalid schema format. Use the content_schema_version query parameter "
        "(e.g. ?content_schema_version=1.0.0). The deprecated Accept header versioning is also still accepted "
        "(e.g. Accept: */*;version=1.0.0)."
    ) in body["reason"]


def test_compositional_search_data_filtered_in_by_row(
    api, helper, tests_data, record_id, dataset_id, fluid_model_type
):
    """Verify bulk data appears in search results matching baseline."""
    params = {"rows_filter": f"FluidModelID,eq,{record_id}:"}

    # Baseline expected dataset (with concrete record id substituted)
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    baseline["data"][0][0] = f"{record_id}:"

    # Wait until search data returns the record_id in result set
    search_response = helper.wait_for_search_data(
        lambda: api.fluid_model.search_data(
            fluid_model_type=fluid_model_type,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        ),
        record_id,
    )

    result_data = search_response.get("result", {})
    helper.compare_responses(result_data, baseline, response_type="json")
    assert result_data["data"][0][0] == f"{record_id}:"
    assert result_data["data"][0][7] == 0.0


def test_compositional_search_data_filtered_by_columns(
    api,
    helper,
    tests_data,
    record_id,
    dataset_id,
    search_available,
    fluid_model_type,
):
    """Verify bulk data is filtered out by the specified columns filter in the search results"""
    params = {
        "columns_filter": "FluidModelID,StandardPressure,StandardTemperature",
        "rows_filter": f"FluidModelID,eq,{record_id}:",
    }
    response = api.fluid_model.search_data(
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )
    result_data = response.get("result", {})

    # Prepare baseline
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    baseline["data"][0][0] = f"{record_id}:"
    indices = [
        baseline["columns"].index("FluidModelID"),
        baseline["columns"].index("StandardPressure"),
        baseline["columns"].index("StandardTemperature"),
    ]
    baseline["columns"] = [baseline["columns"][i] for i in indices]
    baseline["data"][0] = [baseline["data"][0][i] for i in indices]

    # Verify expected results match baseline
    helper.compare_responses(result_data, baseline, response_type="json")


def test_compositional_search_data_aggregated(
    api, record_id, dataset_id, search_available, fluid_model_type
):
    """Verify bulk data aggregated in the search results"""
    params = {
        "columns_aggregation": "StandardPressure,mean",
        "rows_filter": f"FluidModelID,eq,{record_id}:",
    }
    response = api.fluid_model.search_data(
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )

    # Assert
    assert response["result"]["columns"] == ["StandardPressure"]
    assert response["result"]["index"] == ["mean"]
    assert response["result"]["data"] == [[0.0]]


def test_compositional_search_data_filtered_out_by_row(
    api, record_id, dataset_id, search_available, fluid_model_type
):
    """Verify bulk data is filtered out by row filter in the search results"""
    params = {"rows_filter": "FluidModelID,eq,DummyValue"}
    response = api.fluid_model.search_data(
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )

    # Assert
    assert response["result"]["columns"] == []
    assert response["result"]["index"] == []
    assert response["result"]["data"] == []
    assert response["total_size"] == 0


def test_compositional_search_data_filtered_in_by_start_date(
    api, tests_data, record_id, dataset_id, search_available, fluid_model_type
):
    """Verify bulk data is filtered in by the specified start date filter in the search results"""
    current_date = datetime.date.today()
    params = {
        "indexed_start_date": current_date,
        "rows_filter": f"FluidModelID,eq,{record_id}:",
    }
    response = api.fluid_model.search_data(
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )

    # Assert
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))

    assert set(response["result"]["columns"]).issubset(baseline["columns"])
    assert any(row[0] == f"{record_id}:" for row in response["result"]["data"])


def test_compositional_search_data_filtered_out_by_start_date(
    api, record_id, dataset_id, search_available, fluid_model_type
):
    """Verify bulk data is filtered out by the specified start date filter in the search results"""
    current_date = datetime.date.today()
    tomorrow_date = current_date + datetime.timedelta(days=1)
    params = {
        "indexed_start_date": tomorrow_date,
        "rows_filter": f"FluidModelID,eq,{record_id}:",
    }
    response = api.fluid_model.search_data(
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )

    # Assert
    assert response["result"]["columns"] == []
    assert response["result"]["index"] == []
    assert response["result"]["data"] == []


def test_compositional_search_data_filtered_in_by_end_date(
    api, tests_data, record_id, dataset_id, search_available, fluid_model_type
):
    """Verify bulk data is filtered in by the specified end date filter in the search results"""
    current_date = datetime.date.today()
    params = {
        "indexed_end_date": current_date,
        "rows_filter": f"FluidModelID,eq,{record_id}:",
    }
    response = api.fluid_model.search_data(
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )

    # Assert
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))

    assert set(response["result"]["columns"]).issubset(baseline["columns"])
    assert any(row[0] == f"{record_id}:" for row in response["result"]["data"])


def test_compositional_search_data_filtered_out_by_end_date(
    api, tests_data, record_id, dataset_id, search_available, fluid_model_type
):
    """Verify bulk data is filtered out by the specified end date filter in the search results"""
    current_date = datetime.date.today()
    yesterday_date = current_date - datetime.timedelta(days=1)
    params = {
        "indexed_end_date": yesterday_date,
        "rows_filter": f"FluidModelID,eq,{record_id}:",
    }
    response = api.fluid_model.search_data(
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )

    # Assert
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))

    assert set(response["result"]["columns"]).issubset(baseline["columns"])
    assert not any(row[0] == f"{record_id}:" for row in response["result"]["data"])


def test_compositional_search_data_filtered_out_by_page_limit(
    api, helper, pagination_case, fluid_model_type
):
    """Verify bulk data is filtered out by the specified page limit filter in the search results"""
    helper.verify_data_pagination(
        lambda params: api.fluid_model.search_data(
            fluid_model_type=fluid_model_type,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        ),
        pagination_case,
    )


def test_compositional_search_data_records_format_filtered_in_by_row(
    api, helper, tests_data, record_id, dataset_id, search_available, fluid_model_type
):
    """Verify bulk data in records_format appears in search results matching baseline."""
    params = {
        "rows_filter": f"FluidModelID,eq,{record_id}:",
        "orient": "records",
    }

    data_payload = copy.deepcopy(
        tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1)
    )
    data_payload["data"][0][0] = f"{record_id}:"
    baseline = dict(zip(data_payload["columns"], data_payload["data"][0]))

    response = api.fluid_model.search_data(
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )
    helper.compare_responses(response["result"], [baseline], response_type="json")


def test_compositional_search_data_records_format_aggregated(
    api, record_id, dataset_id, search_available, fluid_model_type
):
    """Verify bulk data in record format aggregated in the search results - orient param ignored in response"""
    params = {
        "columns_aggregation": "FluidModelID,count",
        "rows_filter": f"FluidModelID,eq,{record_id}:",
        "orient": "records",
    }
    response = api.fluid_model.search_data(
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )

    # Assert
    assert response["result"]["columns"] == ["FluidModelID"]
    assert response["result"]["index"] == ["count"]
    assert response["result"]["data"] == [[1]]


def test_compositional_search_data_accept_x_parquet(
    api, helper, record_id, dataset_id, search_available, fluid_model_type
):
    """Verify Compositional search data retrieval as Parquet using the supported MIME value."""
    params = {"rows_filter": f"FluidModelID,eq,{record_id}:"}
    response = api.fluid_model.search_data(
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
        json=False,
        headers={ACCEPT: "application/x-parquet"},
        raw=True,
    )
    parquet_data = helper.load_parquet_data(response.content, content_type="parquet")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-parquet")
    assert parquet_data["columns"][0] == "FluidModelID"
    assert any(row[0] == f"{record_id}:" for row in parquet_data["data"])


def test_compositional_search_data_query_schema_version_takes_priority_over_accept_header(
    api,
    helper,
    tests_data,
    record_id,
    dataset_id,
    search_available,
    fluid_model_type,
):
    """Verify content_schema_version query parameter overrides deprecated Accept versioning."""
    params = {"rows_filter": f"FluidModelID,eq,{record_id}:"}
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    baseline["data"][0][0] = f"{record_id}:"

    response = api.fluid_model.search_data(
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={ACCEPT: "application/json;version=9.9.9"},
        params=params,
    )

    result_data = response.get("result", {})
    helper.compare_responses(result_data, baseline, response_type="json")


@pytest.mark.parametrize("malformed_schema_version", ["abc", "1.x"])
def test_compositional_search_data_malformed_schema_version(
    api,
    fluid_model_type,
    malformed_schema_version,
):
    """Reject malformed content_schema_version query parameter with 422."""
    response = api.fluid_model.search_data(
        fluid_model_type=fluid_model_type,
        schema_version=malformed_schema_version,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert (
        f"Invalid version format in content_schema_version: '{malformed_schema_version}'. "
        "Expected format: major.minor.patch (e.g. 1.0.0)"
    ) in body["reason"]


def test_compositional_search_data_missing_schema_version(api, fluid_model_type):
    """Reject Compositional search data when neither query nor Accept header supplies a schema version."""
    response = api.fluid_model.search_data(
        fluid_model_type=fluid_model_type,
        schema_version=None,
        headers={ACCEPT: None},
        allowed_codes=[status.HTTP_406_NOT_ACCEPTABLE],
        raw=True,
    )

    # Assert
    assert response.status_code == 406
    body = response.json()
    assert (
        "No schema version specified or invalid schema format. Use the content_schema_version query parameter "
        "(e.g. ?content_schema_version=1.0.0). The deprecated Accept header versioning is also still accepted "
        "(e.g. Accept: */*;version=1.0.0)."
    ) in body["reason"]
