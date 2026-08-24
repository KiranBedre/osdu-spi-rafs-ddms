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

from app.resources.common_headers import ACCEPT, CACHE_CONTROL, CONTENT_TYPE
from tests.integration.config import DataFiles, SchemaVersions


def _thermal_payload(tests_data, record_id):
    payload = copy.deepcopy(tests_data(DataFiles.THERMAL_COMPOSITIONAL_FLUID_MODEL_DATA_V1))
    payload["data"][0][0] = f"{record_id}:"
    return payload


def test_thermal_compositional_add_data_json_v1(api, tests_data, record_id, fluid_model_type):
    """Upload valid Thermal Compositional JSON content."""
    data_payload = _thermal_payload(tests_data, record_id)
    versions_before = api.fluid_model.get_record_versions(record_id)["versions"]

    post_response = api.fluid_model.post_data(
        record_id=record_id,
        body=data_payload,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
    )

    assert post_response["ddms_urn"]
    versions_after = api.fluid_model.get_record_versions(record_id)["versions"]
    assert len(versions_after) == len(versions_before) + 1


def test_thermal_compositional_add_data_parquet_v1(api, tests_data, fresh_record_id, fluid_model_type):
    """Upload valid Thermal Compositional Parquet content."""
    data_payload = _thermal_payload(tests_data, fresh_record_id)
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

    assert post_response["ddms_urn"]
    versions_after = api.fluid_model.get_record_versions(fresh_record_id)["versions"]
    assert len(versions_after) == len(versions_before) + 1


def test_thermal_compositional_get_data_json_v1(api, tests_data, record_id, dataset_id, fluid_model_type):
    """Verify Thermal Compositional data retrieval as JSON."""
    baseline = _thermal_payload(tests_data, record_id)

    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
    )

    assert response == baseline


def test_thermal_compositional_get_data_parquet_v1(api, helper, record_id, dataset_id, fluid_model_type):
    """Verify Thermal Compositional data retrieval as canonical Parquet."""
    json_data = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
    )
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        json=False,
        headers={ACCEPT: "application/x-parquet"},
        raw=True,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-parquet")
    parquet_data = helper.load_parquet_data(response.content, content_type="parquet")
    assert parquet_data == json_data


def test_thermal_compositional_get_data_defaults_to_json_for_missing_accept_header(
    api, tests_data, record_id, dataset_id, fluid_model_type
):
    """Verify Thermal Compositional GET defaults to JSON without Accept."""
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={ACCEPT: None},
    )

    assert response == _thermal_payload(tests_data, record_id)


def test_thermal_compositional_get_data_defaults_to_json_for_wildcard_accept_header(
    api, tests_data, record_id, dataset_id, fluid_model_type
):
    """Verify Thermal Compositional GET defaults to JSON for Accept */*."""
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={ACCEPT: "*/*"},
    )

    assert response == _thermal_payload(tests_data, record_id)


def test_thermal_compositional_get_data_query_schema_version_takes_priority_over_accept_header(
    api, tests_data, record_id, dataset_id, fluid_model_type
):
    """Verify query schema version overrides deprecated Accept versioning."""
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={ACCEPT: "application/json;version=9.0.0"},
    )

    assert response == _thermal_payload(tests_data, record_id)


def test_thermal_compositional_get_data_filtered_by_column(api, tests_data, record_id, dataset_id, fluid_model_type):
    """Verify Thermal Compositional data retrieval filtered by columns."""
    baseline = _thermal_payload(tests_data, record_id)
    indices = [
        baseline["columns"].index("FluidModelID"),
        baseline["columns"].index("ComponentProperties"),
    ]
    baseline["columns"] = [baseline["columns"][index] for index in indices]
    baseline["data"][0] = [baseline["data"][0][index] for index in indices]

    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params={"columns_filter": "FluidModelID,ComponentProperties"},
    )

    assert response == baseline


def test_thermal_compositional_get_data_filtered_in_by_row(api, tests_data, record_id, dataset_id, fluid_model_type):
    """Verify Thermal Compositional rows_filter eq returns the matching row."""
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params={"rows_filter": f"FluidModelID,eq,{record_id}:"},
    )

    assert response == _thermal_payload(tests_data, record_id)


def test_thermal_compositional_get_data_filtered_out_by_row(api, tests_data, record_id, dataset_id, fluid_model_type):
    """Verify Thermal Compositional rows_filter neq excludes the matching row."""
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params={"rows_filter": f"FluidModelID,neq,{record_id}:"},
    )

    baseline = _thermal_payload(tests_data, record_id)
    assert response["columns"] == baseline["columns"]
    assert response["index"] == []
    assert response["data"] == []


def test_thermal_compositional_get_data_aggregated(api, record_id, dataset_id, fluid_model_type):
    """Verify Thermal Compositional data retrieval aggregated."""
    response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        params={"columns_aggregation": "FluidModelID,describe"},
    )

    assert response["columns"] == ["describe"]
    assert set(response["index"]) == {"count", "unique", "top", "freq"}
    assert f"{record_id}:" in (row[0] for row in response["data"])


def test_thermal_compositional_get_data_returns_identical_response_inside_cache_ttl(
    api, record_id, dataset_id, fluid_model_type
):
    """Verify Thermal Compositional GET response is identical inside cache TTL."""
    cache_headers = {CACHE_CONTROL: "max-age=60"}
    first_response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers=cache_headers,
    )
    second_response = api.fluid_model.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers=cache_headers,
        timeout=0.9,
    )

    assert second_response == first_response
