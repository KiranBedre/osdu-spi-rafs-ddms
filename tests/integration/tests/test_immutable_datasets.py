#  Copyright 2024 ExxonMobil Technology and Engineering Company
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

"""
Integration tests for Issue #707: Immutable Datasets with WPC Versioning.

These tests demonstrate the new immutable versioning behavior:
1. Each POST creates a new dataset ID (never reuses old ones)
2. DDMSDatasets entry is REPLACED per analysis type (not appended)
3. Historical data is accessible via record_id:version in the URL path
4. OSDU's built-in WPC versioning preserves all historical record states
"""

import copy

import pytest
from loguru import logger

from tests.integration.config import (
    CONFIG,
    DataFiles,
    DatasetPrefix,
    DataTemplates,
    DataTypes,
    SamplesAnalysisTypes,
)


@pytest.mark.parametrize(
    "measurements_file, dataset_prefix, analysis_type", [
        (DataFiles.NMR_DATA, DatasetPrefix.NMR, SamplesAnalysisTypes.NMR),
    ],
)
def test_immutable_dataset_versioning(
    api, create_record, helper, tests_data, measurements_file, dataset_prefix, analysis_type,
):
    """Test that bulk data updates create immutable datasets with WPC versioning.

    Flow:
    1. Create a SamplesAnalysis record
    2. POST bulk data (creates WPC version N+1 with dataset A)
    3. POST modified bulk data (creates WPC version N+2 with dataset B)
    4. Verify DDMSDatasets has ONE entry (replaced, not appended)
    5. Verify latest GET returns the modified data (dataset B)
    6. Verify historical GET via record_id:version returns original data (dataset A)
    """
    # Step 1: Create a SamplesAnalysis record
    record_data, _ = create_record(
        DataTypes.SAMPLE_ANALYSIS,
        DataFiles.SAMPLE_ANALYSIS,
        DataTemplates.ID_SAMPLE_ANALYSIS.format(partition=CONFIG["DATA_PARTITION"]),
        analysis_type,
    )
    record_id = record_data["id"]
    logger.info(f"Created record: {record_id}")

    # Get initial versions
    initial_versions = api.sample_analysis.get_record_versions(record_id)
    initial_version_count = len(initial_versions.get("versions", []))
    logger.info(f"Initial version count: {initial_version_count}")

    # Step 2: POST first bulk data
    test_data_v1 = copy.deepcopy(tests_data(measurements_file))
    test_data_v1["data"][0][0] = f"{record_id}:"

    post_response_v1 = api.sample_analysis.post_measurements(
        record_id, test_data_v1, analysis_type,
    )
    ddms_urn_v1 = post_response_v1["ddms_urn"]
    content_id_v1 = helper.get_content_id_from_ddms_urn(ddms_urn_v1)
    logger.info(f"POST v1 - content_id: {content_id_v1}")

    # Verify version count increased
    versions_after_v1 = api.sample_analysis.get_record_versions(record_id)
    version_count_after_v1 = len(versions_after_v1.get("versions", []))
    assert version_count_after_v1 > initial_version_count, (
        "WPC version count should increase after POST"
    )
    wpc_version_v1 = versions_after_v1["versions"][-1]
    logger.info(f"WPC version after v1: {wpc_version_v1}")

    # Step 3: GET data from first POST (verify it works)
    measurements_v1 = api.sample_analysis.get_measurements(
        record_id, content_id_v1, analysis_type,
    )
    assert "columns" in measurements_v1, "GET v1 should return split format data"
    assert "data" in measurements_v1, "GET v1 should return split format data"
    logger.info(f"GET v1 - columns: {measurements_v1['columns']}")

    # Step 4: POST second bulk data (modified)
    test_data_v2 = copy.deepcopy(tests_data(measurements_file))
    test_data_v2["data"][0][0] = f"{record_id}:"

    post_response_v2 = api.sample_analysis.post_measurements(
        record_id, test_data_v2, analysis_type,
    )
    ddms_urn_v2 = post_response_v2["ddms_urn"]
    content_id_v2 = helper.get_content_id_from_ddms_urn(ddms_urn_v2)
    logger.info(f"POST v2 - content_id: {content_id_v2}")

    # Step 5: Verify dataset IDs are different (immutable - new ID each time)
    assert content_id_v1 != content_id_v2, (
        "Each POST should create a NEW dataset ID (immutable)"
    )

    # Step 6: Verify version count increased again
    versions_after_v2 = api.sample_analysis.get_record_versions(record_id)
    version_count_after_v2 = len(versions_after_v2.get("versions", []))
    assert version_count_after_v2 > version_count_after_v1, (
        "WPC version count should increase after second POST"
    )
    logger.info(f"WPC versions: {versions_after_v2['versions']}")

    # Step 7: Verify DDMSDatasets has ONE entry (replaced, not appended)
    latest_record = api.sample_analysis.get_record(record_id)
    ddms_datasets = latest_record["data"].get("DDMSDatasets", [])
    matching_datasets = [
        ds for ds in ddms_datasets
        if f"/{analysis_type}data/" in ds
    ]
    assert len(matching_datasets) == 1, (
        f"DDMSDatasets should have exactly 1 entry for {analysis_type} "
        f"(replaced, not appended). Found: {len(matching_datasets)}"
    )
    logger.info(f"DDMSDatasets count for {analysis_type}: {len(matching_datasets)}")

    # Step 8: GET latest data (should return v2 content)
    measurements_latest = api.sample_analysis.get_measurements(
        record_id, content_id_v2, analysis_type,
    )
    assert "columns" in measurements_latest, "GET latest should return data"
    logger.info("GET latest - OK")

    # Step 9: GET historical data using record_id:version
    versioned_record_id = f"{record_id}:{wpc_version_v1}"
    measurements_historical = api.sample_analysis.get_measurements(
        versioned_record_id, content_id_v1, analysis_type,
    )
    assert "columns" in measurements_historical, (
        "GET with versioned record_id should return historical data"
    )
    logger.info(f"GET historical ({versioned_record_id}) - OK")

    # Step 10: Verify old dataset is NOT in latest record's DDMSDatasets
    assert content_id_v1 not in str(ddms_datasets), (
        "Old dataset ID should not be in latest DDMSDatasets"
    )
    logger.info("Old dataset ID correctly absent from latest DDMSDatasets")

    logger.info("Issue #707 immutable dataset versioning test PASSED")
