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
import re
from email.utils import parsedate_to_datetime

import pandas as pd
import pytest
from starlette import status

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

# TODO: Consolidate Fluid Model GET Schema tests into a parametrized suite
# when Thermal Compositional Model coverage is added.

def test_compositional_get_schema_v1(api, helper, tests_data, fluid_model_type):
    """Verify schema endpoint matches expected schema model."""
    schema = api.fluid_model.get_schema(fluid_model_type, SchemaVersions.V1_0_0)
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_SCHEMA_V1))

    helper.compare_responses(schema, baseline, response_type="json")


def test_compositional_get_schema_unsupported_schema_version(api, fluid_model_type):
    """Reject unsupported Compositional schema version with 404 Not Found."""
    response = api.fluid_model.get_schema(
        fluid_model_type=fluid_model_type,
        schema_version="9.9.9",
        allowed_codes=[status.HTTP_404_NOT_FOUND],
        raw=True,
    )

    # Assert
    assert response.status_code == 404
    reason = response.json()["reason"]
    assert reason.startswith(
        f"Model not found for type '{fluid_model_type}',  "
        f"version '9.9.9'. Available versions: "
    )
    versions_section = reason.split("Available versions:", maxsplit=1)[1]
    actual_versions = set(re.findall(r"'(\d+\.\d+\.\d+)'", versions_section))
    assert actual_versions == {"1.0.0"}


@pytest.mark.parametrize("malformed_schema_version", ["abc", "1.x"])
def test_compositional_get_schema_malformed_schema_version(
    api,
    fluid_model_type,
    malformed_schema_version,
):
    """Reject malformed content_schema_version query parameter with 422."""
    response = api.fluid_model.get_schema(
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


def test_compositional_get_schema_missing_schema_version(api, fluid_model_type):
    """Reject Compositional schema retrieval when neither query nor Accept header supplies a schema version."""
    response = api.fluid_model.get_schema(
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


def test_compositional_get_schema_accept_header_schema_version_v1(
    api,
    helper,
    tests_data,
    fluid_model_type,
):
    """Verify Compositional GET schema accepts deprecated Accept header versioning."""
    response = api.fluid_model.get_schema(
        fluid_model_type=fluid_model_type,
        schema_version=None,
        headers={ACCEPT: "application/json;version=1.0.0"},
        raw=True,
    )
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_SCHEMA_V1))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers.get("Deprecation") == "true"
    parsedate_to_datetime(response.headers["Sunset"])

    deprecation_notice = response.headers["X-Deprecation-Notice"].lower()
    assert "accept header" in deprecation_notice
    assert "deprecated" in deprecation_notice

    helper.compare_responses(response.json(), baseline, response_type="json")


@pytest.mark.xfail(
    reason=(
        "Known implementation discrepancy: X-Deprecation-Notice does not yet contain "
        "the required M27/M28 wording."
    ),
    strict=True,
)
def test_compositional_get_schema_accept_header_deprecation_notice_mentions_m27_m28(
    api,
    fluid_model_type,
):
    """Verify Accept header deprecation notice contains M27/M28 wording."""
    response = api.fluid_model.get_schema(
        fluid_model_type=fluid_model_type,
        schema_version=None,
        headers={ACCEPT: "application/json;version=1.0.0"},
        raw=True,
    )

    deprecation_notice = response.headers["X-Deprecation-Notice"]
    assert "M27" in deprecation_notice
    assert "M28" in deprecation_notice


def test_compositional_get_schema_query_schema_version_takes_priority_over_accept_header(
    api,
    helper,
    tests_data,
    fluid_model_type,
):
    """Verify content_schema_version query parameter overrides deprecated Accept versioning."""
    response = api.fluid_model.get_schema(
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
        headers={ACCEPT: "application/json;version=9.9.9"},
        raw=True,
    )
    baseline = copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_SCHEMA_V1))

    assert response.status_code == 200
    assert "Deprecation" not in response.headers
    helper.compare_responses(response.json(), baseline, response_type="json")


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
