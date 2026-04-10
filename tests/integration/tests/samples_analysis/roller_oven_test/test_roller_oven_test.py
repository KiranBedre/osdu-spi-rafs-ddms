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

from app.resources.common_headers import CONTENT_TYPE

from tests.integration.config import (
    DataFiles,
    SamplesAnalysisTypes,
    SchemaVersions,
)


def test_roller_oven_test_create_record(api, samples_analysis_create_record, helper):
    """Verify created record can be retrieved unchanged via GET."""
    posted_record = samples_analysis_create_record

    # Retrieve the record by id
    gotten_record = api.sample_analysis.get_record(posted_record["id"])

    # Response should contain the same business fields as the original POST body
    helper.compare_responses(gotten_record, posted_record, response_type="json")


def test_roller_oven_test_versions(api, helper, record_id):
    """Verify record versioning: create v2, list versions, compare v1 and v2, confirm latest version."""
    version_1 = api.sample_analysis.get_record(record_id)

    # Create a second version by modifying the Name field
    version_2 = copy.deepcopy(version_1)
    version_2["data"]["Name"] = version_2["data"]["Name"] + " - new version"
    api.sample_analysis.post_record([version_2])

    # List versions and ensure two versions exist
    versions_payload = api.sample_analysis.get_record_versions(record_id)
    assert "versions" in versions_payload
    assert len(versions_payload["versions"]) == 2

    v1_version, v2_version = sorted(versions_payload["versions"])

    # Fetch concrete versions and compare with expected payloads
    rec_v1 = api.sample_analysis.get_record_version(record_id, v1_version)
    rec_v2 = api.sample_analysis.get_record_version(record_id, v2_version)

    helper.compare_responses(rec_v1, version_1, response_type="json")
    helper.compare_responses(rec_v2, version_2, response_type="json")
    assert rec_v2["data"]["Name"].endswith(" - new version")

    # Plain GET should return the latest version
    latest = api.sample_analysis.get_record(record_id)
    helper.compare_responses(latest, version_2, response_type="json")


def test_roller_oven_test_add_data_v1(api, helper, tests_data, record_id):
    """Upload bulk data and verify retrieval in JSON and Parquet formats are equivalent."""
    # Prepare and upload dataset payload
    data_payload = copy.deepcopy(tests_data(DataFiles.ROLLER_OVEN_TEST_DATA_V1))
    data_payload["data"][0][0] = f"{record_id}:"
    post_response = api.sample_analysis.post_measurements(
        record_id, data_payload, SamplesAnalysisTypes.ROLLER_OVEN_TEST, SchemaVersions.V1_0_0
    )
    dataset_id = helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])

    # GET data as JSON and compare with original payload
    gotten_data = api.sample_analysis.get_measurements(
        record_id, dataset_id, SamplesAnalysisTypes.ROLLER_OVEN_TEST, SchemaVersions.V1_0_0
    )
    helper.compare_responses(gotten_data, data_payload, response_type="json")

    # Verify JSON and Parquet responses are equivalent
    parquet_response = api.sample_analysis.get_measurements(
        record_id,
        dataset_id,
        SamplesAnalysisTypes.ROLLER_OVEN_TEST,
        SchemaVersions.V1_0_0,
        raw=True,
        headers={CONTENT_TYPE: "application/x-parquet"},
    ).content
    helper.compare_responses(gotten_data, parquet_response)


def test_roller_oven_test_get_data_v1_filtered_by_column(api, helper, tests_data, record_id, dataset_id_v1):
    """Verify bulk data retrieval filtered by column."""
    # Prepare baseline
    baseline = copy.deepcopy(tests_data(DataFiles.ROLLER_OVEN_TEST_DATA_V1))
    baseline["columns"] = baseline["columns"][8:10]
    baseline["data"][0] = baseline["data"][0][8:10]

    # GET data as JSON and compare with modified payload
    params = {"columns_filter": "SieveMeshSize,MeshSizeTypeID"}
    gotten_data = api.sample_analysis.get_measurements(
        record_id,
        dataset_id=dataset_id_v1,
        analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )
    helper.compare_responses(gotten_data, baseline, response_type="json")


def test_roller_oven_test_get_data_v1_filtered_in_by_row(api, helper, tests_data, record_id, dataset_id_v1):
    """Verify bulk data retrieval filtered in by row."""
    # Prepare baseline
    baseline = copy.deepcopy(tests_data(DataFiles.ROLLER_OVEN_TEST_DATA_V1))
    baseline["data"][0][0] = f"{record_id}:"

    # GET data as JSON and compare with modified payload
    params = {"rows_filter": f"SamplesAnalysisID,eq,{record_id}:"}
    gotten_data = api.sample_analysis.get_measurements(
        record_id,
        dataset_id=dataset_id_v1,
        analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )
    helper.compare_responses(gotten_data, baseline, response_type="json")


def test_roller_oven_test_get_data_v1_filtered_out_by_row(api, record_id, dataset_id_v1):
    """Verify bulk data retrieval filtered out by row."""
    # GET data as JSON
    params = {"rows_filter": f"SamplesAnalysisID,neq,{record_id}:"}
    response = api.sample_analysis.get_measurements(
        record_id,
        dataset_id=dataset_id_v1,
        analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )

    # Assert
    assert response["columns"] == [
        "SamplesAnalysisID",
        "SampleID",
        "Meta",
        "TotalClay",
        "WellFluidsReportID",
        "TestFluidVolume",
        "RollingTemperature",
        "RollingTime",
        "SieveMeshSize",
        "MeshSizeTypeID",
        "InitialSampleWeight",
        "FinalSampleWeight",
        "SampleContainerWeight",
        "FinalTotalWeight",
        "RecoveryPercent",
        "DisaggregationPercent",
        "Remarks",
    ]
    assert response["index"] == []
    assert response["data"] == []


def test_roller_oven_test_get_data_v1_aggregated(api, record_id, dataset_id_v1):
    """Verify bulk data retrieval aggregated."""
    # GET data as JSON
    params = {"columns_aggregation": "SamplesAnalysisID,describe"}
    response = api.sample_analysis.get_measurements(
        record_id,
        dataset_id=dataset_id_v1,
        analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
        schema_version=SchemaVersions.V1_0_0,
        params=params,
    )

    # Assert
    assert response["columns"] == ["describe"]
    assert set(response["index"]) == {"count", "unique", "top", "freq"}
    assert f"{record_id}:" in (row[0] for row in response["data"])


def test_roller_oven_test_get_schema_v1(api, helper, tests_data):
    """Verify schema endpoint matches expected schema model."""
    schema = api.sample_analysis.get_schema(SamplesAnalysisTypes.ROLLER_OVEN_TEST, SchemaVersions.V1_0_0)
    baseline = copy.deepcopy(tests_data(DataFiles.ROLLER_OVEN_TEST_SCHEMA_V1))

    helper.compare_responses(schema, baseline, response_type="json")


def test_roller_oven_test_search_record_filtered_in_by_row(api, helper, record_id, dataset_id_v1):
    """Verify record appears in search results after indexing completes."""
    params = {"rows_filter": f"SamplesAnalysisID,eq,{record_id}:"}

    # Wait until search returns the record_id in its result set
    response = helper.wait_for_search_record(
        lambda: api.sample_analysis.search(
            analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        ),
        record_id,
    )
    assert record_id in response["result"]


def test_roller_oven_test_search_data_filtered_in_by_row(api, helper, tests_data, record_id, dataset_id_v1):
    """Verify bulk data appears in search results matching baseline."""
    params = {"rows_filter": f"SamplesAnalysisID,eq,{record_id}:"}

    # Baseline expected dataset (with concrete record id substituted)
    baseline = copy.deepcopy(tests_data(DataFiles.ROLLER_OVEN_TEST_DATA_V1))
    baseline["data"][0][0] = f"{record_id}:"

    # Wait until search data returns the record_id in result set
    search_response = helper.wait_for_search_data(
        lambda: api.sample_analysis.search_data(
            analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        ),
        record_id,
    )

    result_data = search_response.get("result", {})
    helper.compare_responses(result_data, baseline, response_type="json")


def test_roller_oven_test_search_record_filtered_out_by_row(api, record_id, dataset_id_v1, search_available_v1):
    """Verify record is filtered out by the specified row filter in the search results"""
    params = {"rows_filter": f"SamplesAnalysisID,neq,{record_id}:"}
    response = api.sample_analysis.search(
            analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        )

    # Assert
    assert record_id not in response["result"]


def test_roller_oven_test_search_record_filtered_in_by_start_date(api, record_id, dataset_id_v1, search_available_v1):
    """Verify record is filtered in by the specified start date filter in the search results"""
    current_date = datetime.date.today()
    params = {"indexed_start_date": current_date}
    response = api.sample_analysis.search(
            analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        )

    # Assert
    assert record_id in response["result"]


def test_roller_oven_test_search_record_filtered_out_by_start_date(api, record_id, dataset_id_v1, search_available_v1):
    """Verify record is filtered out by the specified start date filter in the search results"""
    current_date = datetime.date.today()
    tomorrow_date = current_date + datetime.timedelta(days=1)
    params = {"indexed_start_date": tomorrow_date}
    response = api.sample_analysis.search(
            analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        )

    # Assert
    assert response["result"] == []


def test_roller_oven_test_search_record_filtered_in_by_end_date(api, record_id, dataset_id_v1, search_available_v1):
    """Verify record is filtered in by the specified end date filter in the search results"""
    current_date = datetime.date.today()
    params = {"indexed_end_date": current_date}
    response = api.sample_analysis.search(
            analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        )

    # Assert
    assert record_id in response["result"]


def test_roller_oven_test_search_record_filtered_out_by_end_date(api, record_id, dataset_id_v1, search_available_v1):
    """Verify record is filtered out by the specified end date filter in the search results"""
    current_date = datetime.date.today()
    yesterday_date = current_date - datetime.timedelta(days=1)
    params = {"indexed_end_date": yesterday_date}
    response = api.sample_analysis.search(
            analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        )

    # Assert
    assert record_id not in response["result"]


def test_roller_oven_test_search_record_filtered_out_by_page_limit(api, record_id, dataset_id_v1, search_available_v1):
    """Verify records are filtered out by the specified page limit filter in the search results"""
    params = {"page_limit": 2}
    response = api.sample_analysis.search(
            analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        )

    # Assert
    assert len(response["result"]) == 2


def test_roller_oven_test_search_data_filtered_by_columns(
    api, helper, tests_data, record_id, dataset_id_v1, search_available_v1
):
    """Verify bulk data is filtered out by the specified columns filter in the search results"""
    params = {"columns_filter": "WellFluidsReportID,TestFluidVolume",
              "rows_filter": f"SamplesAnalysisID,eq,{record_id}:"}
    response = api.sample_analysis.search_data(
            analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        )
    result_data = response.get("result", {})

    # Prepare baseline
    baseline = copy.deepcopy(tests_data(DataFiles.ROLLER_OVEN_TEST_DATA_V1))
    baseline["columns"] = baseline["columns"][4:6]
    baseline["data"][0] = baseline["data"][0][4:6]

    # Verify expected results match baseline
    helper.compare_responses(result_data, baseline, response_type="json")


def test_roller_oven_test_search_data_filtered_out_by_row(api, record_id, dataset_id_v1, search_available_v1):
    """Verify bulk data is filtered out by row filter in the search results"""
    params = {"rows_filter": "SamplesAnalysisID,eq,DummyValue"}
    response = api.sample_analysis.search_data(
            analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        )

    # Assert
    assert response["result"]["columns"] == []
    assert response["result"]["index"] == []
    assert response["result"]["data"] == []


def test_roller_oven_test_search_data_aggregated(api, record_id, dataset_id_v1, search_available_v1):
    """Verify bulk data aggregated in the search results"""
    params = {"columns_aggregation": "MeshSizeTypeID,describe"}
    response = api.sample_analysis.search_data(
            analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        )

    # Assert
    assert response["result"]["columns"] == ["describe"]
    assert set(response["result"]["index"]) == {"count", "unique", "top", "freq"}


def test_roller_oven_test_search_data_filtered_in_by_start_date(
    api, tests_data, record_id, dataset_id_v1, search_available_v1
):
    """Verify bulk data is filtered in by the specified start date filter in the search results"""
    current_date = datetime.date.today()
    params = {"indexed_start_date": current_date}
    response = api.sample_analysis.search_data(
            analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        )

    # Assert
    baseline = copy.deepcopy(tests_data(DataFiles.ROLLER_OVEN_TEST_DATA_V1))

    assert set(response["result"]["columns"]).issubset(baseline["columns"])
    assert any(row[0] == f"{record_id}:" for row in response["result"]["data"])


def test_roller_oven_test_search_data_filtered_out_by_start_date(api, record_id, dataset_id_v1, search_available_v1):
    """Verify bulk data is filtered out by the specified start date filter in the search results"""
    current_date = datetime.date.today()
    tomorrow_date = current_date + datetime.timedelta(days=1)
    params = {"indexed_start_date": tomorrow_date}
    response = api.sample_analysis.search_data(
            analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        )

    # Assert
    assert response["result"]["columns"] == []
    assert response["result"]["index"] == []
    assert response["result"]["data"] == []


def test_roller_oven_test_search_data_filtered_in_by_end_date(
    api, tests_data, record_id, dataset_id_v1, search_available_v1
):
    """Verify bulk data is filtered in by the specified end date filter in the search results"""
    current_date = datetime.date.today()
    params = {"indexed_end_date": current_date}
    response = api.sample_analysis.search_data(
            analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        )

    # Assert
    baseline = copy.deepcopy(tests_data(DataFiles.ROLLER_OVEN_TEST_DATA_V1))

    assert set(response["result"]["columns"]).issubset(baseline["columns"])
    assert any(row[0] == f"{record_id}:" for row in response["result"]["data"])


def test_roller_oven_test_search_data_filtered_out_by_end_date(
    api, tests_data, record_id, dataset_id_v1, search_available_v1
):
    """Verify bulk data is filtered out by the specified end date filter in the search results"""
    current_date = datetime.date.today()
    yesterday_date = current_date - datetime.timedelta(days=1)
    params = {"indexed_end_date": yesterday_date}
    response = api.sample_analysis.search_data(
            analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        )

    # Assert
    baseline = copy.deepcopy(tests_data(DataFiles.ROLLER_OVEN_TEST_DATA_V1))

    assert set(response["result"]["columns"]).issubset(baseline["columns"])
    assert not any(row[0] == f"{record_id}:" for row in response["result"]["data"])


def test_roller_oven_test_search_data_filtered_out_by_page_limit(
    api, tests_data, record_id, dataset_id_v1, search_available_v1
):
    """Verify bulk data is filtered out by the specified page limit filter in the search results"""
    params = {"page_limit": 2}
    response = api.sample_analysis.search_data(
            analysis_type=SamplesAnalysisTypes.ROLLER_OVEN_TEST,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        )

    # Assert
    baseline = copy.deepcopy(tests_data(DataFiles.ROLLER_OVEN_TEST_DATA_V1))

    assert set(response["result"]["columns"]).issubset(baseline["columns"])
    assert len({row[0] for row in response["result"]["data"]}) <= 2
