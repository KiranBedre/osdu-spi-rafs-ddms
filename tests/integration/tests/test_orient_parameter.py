#  Copyright 2025 ExxonMobil Technology and Engineering Company
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

"""Integration tests for orient query parameter (#680).

Tests that the orient parameter on GET data endpoints returns data in the
correct format (split or records).
"""

import copy

import pytest

from tests.integration.config import (
    CONFIG,
    DataFiles,
    DataTemplates,
    DataTypes,
    SamplesAnalysisTypes,
)


@pytest.mark.parametrize(
    "analysis_type,measurements_file", [
        (SamplesAnalysisTypes.NMR, DataFiles.NMR_DATA_V1),
    ],
)
def test_get_measurements_orient_split(
    api, create_record, helper, tests_data, analysis_type, measurements_file,
):
    """Test that orient=split and default (no orient) return split format."""
    record_data, _ = create_record(
        DataTypes.SAMPLE_ANALYSIS,
        DataFiles.SAMPLE_ANALYSIS,
        DataTemplates.ID_SAMPLE_ANALYSIS.format(partition=CONFIG["DATA_PARTITION"]),
        analysis_type,
    )
    tests_data_content = tests_data(measurements_file)
    test_data = copy.deepcopy(tests_data_content)
    test_data["data"][0][0] = f'{record_data["id"]}:'

    full_dataset_id = api.sample_analysis.post_measurements(
        record_data["id"], test_data, analysis_type,
    )["ddms_urn"]
    content_id = helper.get_content_id_from_ddms_urn(full_dataset_id)

    # Get with orient=split
    params = {"orient": "split"}

    response = api.sample_analysis.get_measurements(
        record_data["id"], content_id, analysis_type, params=params,
    )

    # Verify split format structure
    assert isinstance(response, dict), "Split format should return a dict"
    assert "columns" in response, "Split format should have 'columns' key"
    assert "index" in response, "Split format should have 'index' key"
    assert "data" in response, "Split format should have 'data' key"
    assert isinstance(response["columns"], list), "'columns' should be a list"
    assert isinstance(response["index"], list), "'index' should be a list"
    assert isinstance(response["data"], list), "'data' should be a list"

    # Verify default (no orient) also returns split
    default_response = api.sample_analysis.get_measurements(
        record_data["id"], content_id, analysis_type,
    )
    assert isinstance(default_response, dict), "Default format should return a dict (split)"
    assert "columns" in default_response, "Default format should have 'columns' key"


@pytest.mark.parametrize(
    "analysis_type,measurements_file", [
        (SamplesAnalysisTypes.NMR, DataFiles.NMR_DATA_V1),
    ],
)
def test_get_measurements_orient_records(
    api, create_record, helper, tests_data, analysis_type, measurements_file,
):
    """Test that orient=records returns data in records format."""
    record_data, _ = create_record(
        DataTypes.SAMPLE_ANALYSIS,
        DataFiles.SAMPLE_ANALYSIS,
        DataTemplates.ID_SAMPLE_ANALYSIS.format(partition=CONFIG["DATA_PARTITION"]),
        analysis_type,
    )
    tests_data_content = tests_data(measurements_file)
    test_data = copy.deepcopy(tests_data_content)
    test_data["data"][0][0] = f'{record_data["id"]}:'

    full_dataset_id = api.sample_analysis.post_measurements(
        record_data["id"], test_data, analysis_type
    )["ddms_urn"]
    content_id = helper.get_content_id_from_ddms_urn(full_dataset_id)

    # Get with orient=records
    params = {"orient": "records"}

    response = api.sample_analysis.get_measurements(
        record_data["id"], content_id, analysis_type, params=params,
    )

    # Verify records format structure
    assert isinstance(response, list), "Records format should return a list"
    assert len(response) > 0, "Records format should have at least one record"
    assert isinstance(response[0], dict), "Each record should be a dict"
    assert "SamplesAnalysisID" in response[0], "Record should have expected field"
