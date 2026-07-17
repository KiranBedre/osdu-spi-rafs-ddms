#  Copyright 2023 ExxonMobil Technology and Engineering Company
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

import pytest

from tests.integration.config import (
    CONFIG,
    DataFiles,
    DataTemplates,
    DataTypes,
    SamplesAnalysisTypes,
    SchemaVersions,
    VersionedDataFiles,
)


@pytest.fixture(scope="module")
def depth_shift_create_record(api, create_record):
    """Create a Depth Shift record."""
    record_data, _ = create_record(
        DataTypes.DEPTH_SHIFT,
        DataFiles.DEPTH_SHIFT,
        DataTemplates.ID_DEPTH_SHIFT.format(partition=CONFIG["DATA_PARTITION"]),
    )
    yield record_data
    api.storage.purge_record(record_data["id"])


@pytest.fixture(scope="function")
def depth_shift_create_fresh_record(api, create_record):
    """Create a fresh Depth Shift record."""
    record_data, _ = create_record(
        DataTypes.DEPTH_SHIFT,
        DataFiles.DEPTH_SHIFT,
        DataTemplates.ID_DEPTH_SHIFT.format(partition=CONFIG["DATA_PARTITION"]),
    )
    yield record_data
    api.storage.purge_record(record_data["id"])


@pytest.fixture(scope="module")
def depth_shift_record_id(depth_shift_create_record):
    """Return Depth Shift record_id."""
    return depth_shift_create_record["id"]


@pytest.fixture(scope="function")
def fresh_depth_shift_record_id(depth_shift_create_fresh_record):
    """Return fresh Depth Shift record_id."""
    return depth_shift_create_fresh_record["id"]


@pytest.fixture(scope="module")
def depth_shift_dataset_id(api, helper, depth_shift_record_id, tests_data):
    """Create a dataset and return dataset_id."""
    data_payload = copy.deepcopy(tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA))
    data_payload["data"][0][0] = f"{depth_shift_record_id}:"
    post_response = api.depth_shift.post_data(depth_shift_record_id, data_payload)
    return helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])


@pytest.fixture(scope="function")
def fresh_depth_shift_dataset_id(api, helper, fresh_depth_shift_record_id, tests_data):
    """Create a fresh dataset and return dataset_id."""
    data_payload = copy.deepcopy(tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA))
    data_payload["data"][0][0] = f"{fresh_depth_shift_record_id}:"
    post_response = api.depth_shift.post_data(fresh_depth_shift_record_id, data_payload)
    return helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])


@pytest.fixture(scope="package")
def analysis_type():
    """Default analysis type; can be overridden via parametrization."""
    return SamplesAnalysisTypes.NMR


@pytest.fixture(scope="module")
def sample_analysis_create_record(api, create_record, analysis_type):
    """Create a Samples Analysis record per type."""
    record_data, _ = create_record(
        DataTypes.SAMPLE_ANALYSIS,
        DataFiles.SAMPLE_ANALYSIS,
        DataTemplates.ID_SAMPLE_ANALYSIS.format(partition=CONFIG["DATA_PARTITION"]),
        analysis_type
    )
    yield record_data
    api.storage.purge_record(record_data["id"])


@pytest.fixture(scope="module")
def sample_analysis_record_id(sample_analysis_create_record):
    """Return Samples Analysis record_id."""
    return sample_analysis_create_record["id"]


@pytest.fixture(scope="module")
def sample_analysis_dataset_id(api, helper, sample_analysis_record_id, tests_data, analysis_type):
    """Generic fixture to create a V1 dataset."""
    # 1. Lookup the correct data file for this Analysis Type + V1
    file_key = VersionedDataFiles.VALUES.get((analysis_type, SchemaVersions.V1_0_0))

    # 2. Load and Prepare Data
    data_payload = copy.deepcopy(tests_data(file_key))
    data_payload["data"][0][0] = f"{sample_analysis_record_id}:"

    # 3. Post
    post_response = api.sample_analysis.post_data(
        record_id=sample_analysis_record_id,
        body=data_payload,
        analysis_type=analysis_type,
        schema_version=SchemaVersions.V1_0_0
    )

    return helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])

@pytest.fixture(scope="function")
def search_available(api, helper, sample_analysis_record_id, analysis_type):
    """Verify if record is available in search results - workaround for issue #729."""
    params = {"rows_filter": f"SamplesAnalysisID,eq,{sample_analysis_record_id}:"}

    # Wait until search returns the record_id in its result set
    helper.wait_for_search_record(
        lambda: api.sample_analysis.search_records(
            analysis_type=analysis_type,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        ),
        sample_analysis_record_id,
        max_attempts=5,
    )
