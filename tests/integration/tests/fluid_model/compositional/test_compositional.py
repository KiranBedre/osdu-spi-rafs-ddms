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

import pandas as pd

from app.resources.common_headers import ACCEPT, CONTENT_TYPE
from tests.integration.config import DataFiles, SchemaVersions


def test_compositional_add_data_json_v1(
    api,
    tests_data,
    record_id,
    fluid_model_type,
):
    """Upload valid Compositional JSON content."""
    data_payload = copy.deepcopy(
        tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1)
    )
    data_payload["data"][0][0] = f"{record_id}:"
    versions_before = api.fluid_model.get_record_versions(record_id)["versions"]

    post_response = api.fluid_model.post_data(
        record_id=record_id,
        body=data_payload,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
    )

    assert "ddms_urn" in post_response
    assert post_response["ddms_urn"]

    versions_after = api.fluid_model.get_record_versions(record_id)["versions"]
    assert len(versions_after) == len(versions_before) + 1


def test_compositional_add_data_parquet_v1(
    api,
    tests_data,
    fresh_record_id,
    fluid_model_type,
):
    """Upload valid Compositional Parquet content using the supported MIME value."""
    data_payload = copy.deepcopy(
        tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1)
    )
    data_payload["data"][0][0] = f"{fresh_record_id}:"
    dataframe = pd.DataFrame(
        data_payload["data"],
        columns=data_payload["columns"],
        index=data_payload["index"],
    )
    versions_before = api.fluid_model.get_record_versions(fresh_record_id)["versions"]

    post_response = api.fluid_model.post_data(
        record_id=fresh_record_id,
        body=dataframe.to_parquet(),
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={CONTENT_TYPE: "application/x-parquet"},
    )

    assert "ddms_urn" in post_response
    assert post_response["ddms_urn"]

    versions_after = api.fluid_model.get_record_versions(fresh_record_id)["versions"]
    assert len(versions_after) == len(versions_before) + 1


def test_compositional_get_data_json_v1(
    api,
    tests_data,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Verify Compositional data retrieval as JSON."""
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    baseline["data"][0][0] = f"{record_id}:"

    gotten_data = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
    )

    assert gotten_data["columns"] == baseline["columns"]
    assert gotten_data["index"] == baseline["index"]
    assert gotten_data["data"] == baseline["data"]


def test_compositional_get_data_parquet_v1(
    api,
    helper,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Verify Compositional data retrieval as Parquet using the supported MIME value."""
    json_data = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
    )

    parquet_response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        json=False,
        headers={ACCEPT: "application/x-parquet"},
        raw=True,
    ).content
    parquet_data = helper.load_parquet_data(parquet_response, content_type="parquet")

    assert parquet_data["columns"] == json_data["columns"]
    assert parquet_data["index"] == json_data["index"]
    assert parquet_data["data"] == json_data["data"]


def test_compositional_get_data_accept_json_v1(
    api,
    tests_data,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Verify Accept: application/json returns Compositional JSON data."""
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    baseline["data"][0][0] = f"{record_id}:"

    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={ACCEPT: "application/json"},
    )

    assert response["columns"] == baseline["columns"]
    assert response["index"] == baseline["index"]
    assert response["data"] == baseline["data"]


def test_compositional_get_data_defaults_to_json_for_missing_accept_header(
    api,
    tests_data,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Verify Compositional data retrieval defaults to JSON when Accept is missing."""
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    baseline["data"][0][0] = f"{record_id}:"

    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={ACCEPT: None},
    )

    assert response["columns"] == baseline["columns"]
    assert response["index"] == baseline["index"]
    assert response["data"] == baseline["data"]


def test_compositional_get_data_defaults_to_json_for_wildcard_accept_header(
    api,
    tests_data,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Verify Compositional data retrieval defaults to JSON when Accept is */*."""
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    baseline["data"][0][0] = f"{record_id}:"

    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={ACCEPT: "*/*"},
    )

    assert response["columns"] == baseline["columns"]
    assert response["index"] == baseline["index"]
    assert response["data"] == baseline["data"]


def test_compositional_get_data_accept_header_schema_version_v1(
    api,
    tests_data,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Verify Compositional GET data accepts deprecated Accept header versioning."""
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    baseline["data"][0][0] = f"{record_id}:"

    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=None,
        headers={ACCEPT: "application/json;version=1.0.0"},
    )

    assert response["columns"] == baseline["columns"]
    assert response["index"] == baseline["index"]
    assert response["data"] == baseline["data"]


def test_compositional_get_data_query_schema_version_takes_priority_over_accept_header(
    api,
    tests_data,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Verify content_schema_version query parameter overrides deprecated Accept versioning."""
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    baseline["data"][0][0] = f"{record_id}:"

    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={ACCEPT: "application/json;version=9.0.0"},
    )

    assert response["columns"] == baseline["columns"]
    assert response["index"] == baseline["index"]
    assert response["data"] == baseline["data"]


def test_compositional_get_data_filtered_by_column(
    api,
    tests_data,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Verify Compositional data retrieval filtered by columns."""
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    baseline["data"][0][0] = f"{record_id}:"
    indices = [
        baseline["columns"].index("FluidModelID"),
        baseline["columns"].index("ComponentProperties"),
    ]
    baseline["columns"] = [baseline["columns"][i] for i in indices]
    baseline["data"][0] = [baseline["data"][0][i] for i in indices]

    params = {"columns_filter": "FluidModelID,ComponentProperties"}
    gotten_data = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )

    assert gotten_data["columns"] == baseline["columns"]
    assert gotten_data["index"] == baseline["index"]
    assert gotten_data["data"] == baseline["data"]
    assert all(len(row) == len(baseline["columns"]) for row in gotten_data["data"])


def test_compositional_get_data_filtered_in_by_row(
    api,
    tests_data,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Verify Compositional data retrieval filtered in by row."""
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    baseline["data"][0][0] = f"{record_id}:"

    params = {"rows_filter": f"FluidModelID,eq,{record_id}:"}
    gotten_data = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )

    assert gotten_data["columns"] == baseline["columns"]
    assert gotten_data["index"] == baseline["index"]
    assert gotten_data["data"] == baseline["data"]


def test_compositional_get_data_filtered_out_by_row(
    api,
    tests_data,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Verify Compositional data retrieval filtered out by row."""
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    non_existing_fluid_model_id = f"{record_id}-no-match:"

    params = {"rows_filter": f"FluidModelID,eq,{non_existing_fluid_model_id}"}
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )

    assert response["columns"] == baseline["columns"]
    assert response["index"] == []
    assert response["data"] == []


def test_compositional_get_data_aggregated(
    api,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Verify Compositional data retrieval aggregated."""
    params = {"columns_aggregation": "FluidModelID,describe"}
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )

    assert response["columns"] == ["describe"]
    assert set(response["index"]) == {"count", "unique", "top", "freq"}
    assert f"{record_id}:" in (row[0] for row in response["data"])


def test_compositional_get_data_filtered_json(
    api,
    tests_data,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Verify Compositional filtered data retrieval as JSON."""
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    baseline["data"][0][0] = f"{record_id}:"
    indices = [
        baseline["columns"].index("FluidModelID"),
        baseline["columns"].index("ComponentProperties"),
    ]
    baseline["columns"] = [baseline["columns"][i] for i in indices]
    baseline["data"][0] = [baseline["data"][0][i] for i in indices]

    params = {"columns_filter": "FluidModelID,ComponentProperties"}
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
        headers={ACCEPT: "application/json"},
    )

    assert response["columns"] == baseline["columns"]
    assert response["index"] == baseline["index"]
    assert response["data"] == baseline["data"]


def test_compositional_get_data_filtered_parquet(
    api,
    helper,
    tests_data,
    record_id,
    dataset_id,
    fluid_model_type,
):
    """Verify Compositional filtered data retrieval as Parquet."""
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    baseline["data"][0][0] = f"{record_id}:"
    indices = [
        baseline["columns"].index("FluidModelID"),
        baseline["columns"].index("ComponentProperties"),
    ]
    baseline["columns"] = [baseline["columns"][i] for i in indices]
    baseline["data"][0] = [baseline["data"][0][i] for i in indices]

    params = {"columns_filter": "FluidModelID,ComponentProperties"}
    parquet_response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
        json=False,
        headers={ACCEPT: "application/x-parquet"},
        raw=True,
    ).content
    parquet_data = helper.load_parquet_data(parquet_response, content_type="parquet")

    assert parquet_data["columns"] == baseline["columns"]
    assert parquet_data["index"] == baseline["index"]
    assert parquet_data["data"] == baseline["data"]
    assert all(len(row) == len(baseline["columns"]) for row in parquet_data["data"])
