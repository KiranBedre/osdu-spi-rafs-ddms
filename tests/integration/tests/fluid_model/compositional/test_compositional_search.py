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
