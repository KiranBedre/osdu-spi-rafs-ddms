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

from app.resources.common_headers import ACCEPT

from tests.integration.config import (
    CONFIG,
    DataFiles,
)

DATA_PARTITION_ID = CONFIG["DATA_PARTITION"]


def test_rsrp_create_record(api, simulation_rock_physics_create_record, helper):
    """Verify created record can be retrieved unchanged via GET."""
    posted_record = simulation_rock_physics_create_record

    # Retrieve the record by id
    gotten_record = api.simulation_rock_physics.get_record(posted_record["id"])

    # Response should contain the same business fields as the original POST body
    helper.compare_responses(gotten_record, posted_record, response_type="json")


def test_rsrp_versions(api, fresh_record_id, helper):
    """Verify record versioning: create v2, list versions, compare v1 and v2, confirm latest version."""
    version_1 = api.simulation_rock_physics.get_record(fresh_record_id)

    # Create a second version by modifying the Name field
    version_2 = copy.deepcopy(version_1)
    version_2["data"]["Name"] = version_2["data"]["Name"] + " - new version"
    api.simulation_rock_physics.post_record([version_2])

    # List versions and ensure two versions exist
    versions_payload = api.simulation_rock_physics.get_record_versions(fresh_record_id)
    assert "versions" in versions_payload
    assert len(versions_payload["versions"]) == 2

    v1_version, v2_version = sorted(versions_payload["versions"])

    # Fetch concrete versions and compare with expected payloads
    rec_v1 = api.simulation_rock_physics.get_record_version(fresh_record_id, v1_version)
    rec_v2 = api.simulation_rock_physics.get_record_version(fresh_record_id, v2_version)

    helper.compare_responses(rec_v1, version_1, response_type="json")
    helper.compare_responses(rec_v2, version_2, response_type="json")
    assert rec_v2["data"]["Name"].endswith(" - new version")

    # Plain GET should return the latest version
    latest = api.simulation_rock_physics.get_record(fresh_record_id)
    helper.compare_responses(latest, version_2, response_type="json")


def test_rsrp_add_data_vtp(api, record_id, helper, tests_data):
    """Upload bulk data and verify retrieval in JSON and Parquet formats are equivalent."""
    # Prepare and upload dataset payload
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
    data_payload["data"][0][0] = f"{record_id}:"
    post_response = api.simulation_rock_physics.post_data(record_id, data_payload)
    dataset_id = helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])

    # GET data as JSON and compare with original payload
    gotten_data = api.simulation_rock_physics.get_data(record_id, dataset_id)
    helper.compare_responses(gotten_data, data_payload, response_type="json")

    # Verify JSON and Parquet responses are equivalent
    parquet_response = api.simulation_rock_physics.get_data(
        record_id,
        dataset_id,
        json=False,
        headers={ACCEPT: "application/x-parquet"},
        raw=True,
    ).content
    helper.compare_responses(gotten_data, parquet_response)


def test_rsrp_add_data_volume_multiplier(api, record_id, helper, tests_data):
    """Upload bulk data and verify retrieval in JSON and Parquet formats are equivalent."""
    # Prepare and upload dataset payload
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA2_V1))
    data_payload["data"][0][0] = f"{record_id}:"
    post_response = api.simulation_rock_physics.post_data(record_id, data_payload)
    dataset_id = helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])

    # GET data as JSON and compare with original payload
    gotten_data = api.simulation_rock_physics.get_data(record_id, dataset_id)
    helper.compare_responses(gotten_data, data_payload, response_type="json")

    # Verify JSON and Parquet responses are equivalent
    parquet_response = api.simulation_rock_physics.get_data(
        record_id,
        dataset_id,
        json=False,
        headers={ACCEPT: "application/x-parquet"},
        raw=True,
    ).content
    helper.compare_responses(gotten_data, parquet_response)

def test_rsrp_add_data_correlation_compressibility(api, record_id, helper, tests_data):
    """Upload bulk data and verify retrieval in JSON and Parquet formats are equivalent."""
    # Prepare and upload dataset payload
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
    data_payload["data"][0][0] = f"{record_id}:"
    post_response = api.simulation_rock_physics.post_data(record_id, data_payload)
    dataset_id = helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])

    # GET data as JSON and compare with original payload
    gotten_data = api.simulation_rock_physics.get_data(record_id, dataset_id)
    helper.compare_responses(gotten_data, data_payload, response_type="json")

    # Verify JSON and Parquet responses are equivalent
    parquet_response = api.simulation_rock_physics.get_data(
        record_id,
        dataset_id,
        json=False,
        headers={ACCEPT: "application/x-parquet"},
        raw=True,
    ).content
    helper.compare_responses(gotten_data, parquet_response)


def test_rsrp_get_data_filtered_by_column(api, helper, tests_data, record_id, dataset_id):
    """Verify bulk data retrieval filtered by column."""
    # Prepare baseline
    baseline = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
    baseline["data"][0][0] = f"{record_id}:"
    baseline["columns"] = baseline["columns"][2:]
    baseline["data"][0] = baseline["data"][0][2:]

    # GET data as JSON and compare with modified payload
    params = {"columns_filter": "Compressibility,ThermalModelDefinition"}
    gotten_data = api.simulation_rock_physics.get_data(record_id, dataset_id, params=params)
    helper.compare_responses(gotten_data, baseline, response_type="json")


def test_rsrp_get_data_filtered_in_by_row(api, helper, tests_data, record_id, dataset_id):
    """Verify bulk data retrieval filtered in by row."""
    # Prepare baseline
    baseline = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
    baseline["data"][0][0] = f"{record_id}:"

    # GET data as JSON and compare with modified payload
    params = {"rows_filter": f"ReservoirSimulationRockPhysicsID,eq,{record_id}:"}
    gotten_data = api.simulation_rock_physics.get_data(record_id, dataset_id, params=params)
    helper.compare_responses(gotten_data, baseline, response_type="json")


def test_rsrp_get_data_filtered_out_by_row(api, tests_data, record_id, dataset_id):
    """Verify bulk data retrieval filtered out by row."""
    # GET data as JSON
    params = {"rows_filter": f"ReservoirSimulationRockPhysicsID,neq,{record_id}:"}
    response = api.simulation_rock_physics.get_data(record_id, dataset_id, params=params)

    # Assert
    baseline = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))

    assert set(response["columns"]).issubset(baseline["columns"])
    assert response["index"] == []
    assert response["data"] == []


def test_rsrp_get_data_aggregated(api, record_id, dataset_id):
    """Verify bulk data retrieval aggregated."""
    # GET data as JSON
    params = {"columns_aggregation": "ReservoirSimulationRockPhysicsID,describe"}
    response = api.simulation_rock_physics.get_data(record_id, dataset_id, params=params)

    # Assert
    assert response["columns"] == ["describe"]
    assert set(response["index"]) == {"count", "unique", "top", "freq"}
    assert f"{record_id}:" in (row[0] for row in response["data"])


def test_rsrp_get_schema(api, helper, tests_data):
    """Verify schema endpoint matches expected schema model."""
    schema = api.simulation_rock_physics.get_schema()
    baseline = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_SCHEMA))

    helper.compare_responses(schema, baseline, response_type="json")


def test_rsrp_search_record_filtered_in_by_row(api, helper, record_id, dataset_id):
    """Verify record appears in search results after indexing completes."""
    params = {"rows_filter": f"ReservoirSimulationRockPhysicsID,eq,{record_id}:"}

    # Wait until search returns the record_id in its result set
    response = helper.wait_for_search_record(
        lambda: api.simulation_rock_physics.search_records(params=params),
        record_id,
    )
    assert record_id in response["result"]


def test_rsrp_search_data_filtered_in_by_row(api, helper, tests_data, record_id, dataset_id):
    """Verify bulk data appears in search results matching baseline."""
    params = {"rows_filter": f"ReservoirSimulationRockPhysicsID,eq,{record_id}:"}

    # Baseline expected dataset (with concrete record id substituted)
    baseline = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
    baseline["data"][0][0] = f"{record_id}:"

    # Wait until search data returns the record_id in result set
    search_response = helper.wait_for_search_data(
        lambda: api.simulation_rock_physics.search_data(params=params),
        record_id,
    )

    result_data = search_response.get("result", {})
    helper.compare_responses(result_data, baseline, response_type="json")


def test_rsrp_search_record_filtered_out_by_row(api, record_id, dataset_id, search_available):
    """Verify record is filtered out by the specified row filter in the search results"""
    params = {"rows_filter": f"ReservoirSimulationRockPhysicsID,neq,{record_id}:"}
    response = api.simulation_rock_physics.search_records(params=params)

    # Assert
    assert record_id not in response["result"]


def test_rsrp_search_record_filtered_in_by_start_date(api, record_id, dataset_id, search_available):
    """Verify record is filtered in by the specified start date filter in the search results"""
    current_date = datetime.date.today()
    params = {"indexed_start_date": current_date}
    response = api.simulation_rock_physics.search_records(params=params)

    # Assert
    assert record_id in response["result"]


def test_rsrp_search_record_filtered_out_by_start_date(api, record_id, dataset_id, search_available):
    """Verify record is filtered out by the specified start date filter in the search results"""
    current_date = datetime.date.today()
    tomorrow_date = current_date + datetime.timedelta(days=1)
    params = {"indexed_start_date": tomorrow_date}
    response = api.simulation_rock_physics.search_records(params=params)

    # Assert
    assert response["result"] == []


def test_rsrp_search_record_filtered_in_by_end_date(api, record_id, dataset_id, search_available):
    """Verify record is filtered in by the specified end date filter in the search results"""
    current_date = datetime.date.today()
    params = {"indexed_end_date": current_date}
    response = api.simulation_rock_physics.search_records(params=params)

    # Assert
    assert record_id in response["result"]


def test_rsrp_search_record_filtered_out_by_end_date(api, record_id, dataset_id, search_available):
    """Verify record is filtered out by the specified end date filter in the search results"""
    current_date = datetime.date.today()
    yesterday_date = current_date - datetime.timedelta(days=1)
    params = {"indexed_end_date": yesterday_date}
    response = api.simulation_rock_physics.search_records(params=params)

    # Assert
    assert record_id not in response["result"]


def test_rsrp_search_record_filtered_out_by_page_limit(api, record_id, dataset_id, search_available):
    """Verify records are filtered out by the specified page limit filter in the search results"""
    params = {"page_limit": 2}
    response = api.simulation_rock_physics.search_records(params=params)

    # Assert
    assert len(response["result"]) == 2


def test_rsrp_search_data_filtered_by_columns(api, helper, tests_data, record_id, dataset_id, search_available):
    """Verify bulk data is filtered out by the specified columns filter in the search results"""
    params = {"columns_filter": "Compressibility,ThermalModelDefinition",
              "rows_filter": f"ReservoirSimulationRockPhysicsID,eq,{record_id}:"}
    response = api.simulation_rock_physics.search_data(params=params)
    result_data = response.get("result", {})

    # Prepare baseline
    baseline = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
    baseline["columns"] = baseline["columns"][2:]
    baseline["data"][0] = baseline["data"][0][2:]

    # Verify expected results match baseline
    helper.compare_responses(result_data, baseline, response_type="json")


def test_rsrp_search_data_filtered_out_by_row(api, record_id, dataset_id, search_available):
    """Verify bulk data is filtered out by row filter in the search results"""
    params = {"rows_filter": "ReservoirSimulationRockPhysicsID,eq,DummyValue"}
    response = api.simulation_rock_physics.search_data(params=params)

    # Assert
    assert response["result"]["columns"] == []
    assert response["result"]["index"] == []
    assert response["result"]["data"] == []


def test_rsrp_search_data_aggregated(api, record_id, dataset_id, search_available):
    """Verify bulk data aggregated in the search results"""
    params = {"columns_aggregation": "ReservoirSimulationRockPhysicsID,describe"}
    response = api.simulation_rock_physics.search_data(params=params)

    # Assert
    assert response["result"]["columns"] == ["describe"]
    assert set(response["result"]["index"]) == {"count", "unique", "top", "freq"}


def test_rsrp_search_data_filtered_in_by_start_date(api, tests_data, record_id, dataset_id, search_available):
    """Verify bulk data is filtered in by the specified start date filter in the search results"""
    current_date = datetime.date.today()
    params = {"indexed_start_date": current_date}
    response = api.simulation_rock_physics.search_data(params=params)

    # Assert
    baseline = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))

    assert set(response["result"]["columns"]).issubset(baseline["columns"])
    assert any(row[0] == f"{record_id}:" for row in response["result"]["data"])


def test_rsrp_search_data_filtered_out_by_start_date(api, record_id, dataset_id, search_available):
    """Verify bulk data is filtered out by the specified start date filter in the search results"""
    current_date = datetime.date.today()
    tomorrow_date = current_date + datetime.timedelta(days=1)
    params = {"indexed_start_date": tomorrow_date}
    response = api.simulation_rock_physics.search_data(params=params)

    # Assert
    assert response["result"]["columns"] == []
    assert response["result"]["index"] == []
    assert response["result"]["data"] == []


def test_rsrp_search_data_filtered_in_by_end_date(api, tests_data, record_id, dataset_id, search_available):
    """Verify bulk data is filtered in by the specified end date filter in the search results"""
    current_date = datetime.date.today()
    params = {"indexed_end_date": current_date}
    response = api.simulation_rock_physics.search_data(params=params)

    # Assert
    baseline = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))

    assert set(response["result"]["columns"]).issubset(baseline["columns"])
    assert any(row[0] == f"{record_id}:" for row in response["result"]["data"])


def test_rsrp_search_data_filtered_out_by_end_date(api, tests_data, record_id, dataset_id, search_available):
    """Verify bulk data is filtered out by the specified end date filter in the search results"""
    current_date = datetime.date.today()
    yesterday_date = current_date - datetime.timedelta(days=1)
    params = {"indexed_end_date": yesterday_date}
    response = api.simulation_rock_physics.search_data(params=params)

    # Assert
    baseline = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))

    assert set(response["result"]["columns"]).issubset(baseline["columns"])
    assert not any(row[0] == f"{record_id}:" for row in response["result"]["data"])


def test_rsrp_search_data_filtered_out_by_page_limit(api, tests_data, record_id, dataset_id, search_available):
    """Verify bulk data is filtered out by the specified page limit filter in the search results"""
    params = {"page_limit": 2}
    response = api.simulation_rock_physics.search_data(params=params)

    # Assert
    baseline = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))

    assert set(response["result"]["columns"]).issubset(baseline["columns"])
    assert len({row[0] for row in response["result"]["data"]}) <= 2


def test_rsrp_add_data_records_format(api, helper, tests_data, record_id):
    """Upload bulk data in records format and verify retrieval in JSON."""
    # Prepare and upload dataset payload
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1_RECORDS_FORMAT))
    data_payload["ReservoirSimulationRockPhysicsID"] = f"{record_id}:"
    post_response = api.simulation_rock_physics.post_data(record_id, [data_payload])
    dataset_id = helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])

    # GET data as JSON and compare with original payload
    params = {"orient": "records"}
    gotten_data = api.simulation_rock_physics.get_data(record_id, dataset_id, params=params)
    helper.compare_responses(gotten_data, [data_payload], response_type="json")


def test_rsrp_search_data_records_format_filtered_in_by_row(
    api, helper, tests_data, record_id, dataset_id, search_available
):
    """Verify bulk data in records_format appears in search results matching baseline."""
    params = {
        "rows_filter": f"ReservoirSimulationRockPhysicsID,eq,{record_id}:",
        "orient": "records",
    }

    # Baseline expected dataset (with concrete record id substituted)
    baseline = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1_RECORDS_FORMAT))
    baseline["ReservoirSimulationRockPhysicsID"] = f"{record_id}:"

    response = api.simulation_rock_physics.search_data(params=params)
    helper.compare_responses(response["result"], [baseline], response_type="json")


def test_rsrp_search_data_records_format_filtered_by_columns(
    api, helper, tests_data, record_id, dataset_id, search_available
):
    """Verify bulk data in record format is filtered out by the specified columns filter in the search results"""
    params = {
        "columns_filter": "Compressibility,ThermalModelDefinition",
        "rows_filter": f"ReservoirSimulationRockPhysicsID,eq,{record_id}:",
        "orient": "records",
    }

    # Prepare baseline
    baseline = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1_RECORDS_FORMAT))
    baseline.pop("ReservoirSimulationRockPhysicsID", None)
    baseline.pop("Meta", None)

    response = api.simulation_rock_physics.search_data(params=params)
    helper.compare_responses(response["result"], [baseline], response_type="json")


def test_rsrp_search_data_records_format_aggregated(api, record_id, dataset_id, search_available):
    """Verify bulk data in record format aggregated in the search results - orient param ignored in response"""
    params = {
        "columns_aggregation": "ReservoirSimulationRockPhysicsID,describe",
        "orient": "records",
    }
    response = api.simulation_rock_physics.search_data(params=params)

    # Assert
    assert response["result"]["columns"] == ["describe"]
    assert set(response["result"]["index"]) == {"count", "unique", "top", "freq"}


def test_rsrp_search_record_filtered_in_by_field(api, record_id, dataset_id, search_available):
    """Verify record is filtered in by the FieldID filter in the search results"""
    params = {"field_id": f"{DATA_PARTITION_ID}:master-data--Field:SomeUniqueFieldID:"}
    response = api.simulation_rock_physics.search_records(params=params)

    # Assert
    assert record_id in response["result"]


def test_rsrp_search_record_filtered_out_by_basin(api, record_id, dataset_id, search_available):
    """Verify record is filtered out by the specified BasinID filter in the search results"""
    params = {"field_id": f"{DATA_PARTITION_ID}:master-data--Field:SomeOtherFieldID:"}
    response = api.simulation_rock_physics.search_records(params=params)

    # Assert
    assert record_id not in response["result"]


def test_rsrp_search_data_filtered_in_by_basin(api, helper, tests_data, record_id, dataset_id, search_available):
    """Verify bulk data filtered by BasinID appears in search results."""
    params = {"basin_id": f"{DATA_PARTITION_ID}:master-data--Basin:SomeUniqueBasinID:"}
    response = api.simulation_rock_physics.search_data(params=params)

    # Assert
    assert any(row[0] == f"{record_id}:" for row in response["result"]["data"])


def test_rsrp_search_data_filtered_out_by_field(api, record_id, dataset_id, search_available):
    """Verify bulk data is filtered out by FieldID filter in the search results"""
    params = {"field_id": f"{DATA_PARTITION_ID}:master-data--Field:SomeOtherFieldID:"}
    response = api.simulation_rock_physics.search_data(params=params)

    # Assert
    assert response["result"]["columns"] == []
    assert response["result"]["index"] == []
    assert response["result"]["data"] == []
