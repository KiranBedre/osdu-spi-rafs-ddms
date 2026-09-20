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


@pytest.fixture(scope="package")
def analysis_type():
    """Analysis type definition"""
    return SamplesAnalysisTypes.SATURATION_TEST


@pytest.fixture(scope="package")
def cce_record_id(create_record):
    """Create a Samples Analysis record per type."""
    record_data, _ = create_record(
        DataTypes.SAMPLE_ANALYSIS,
        DataFiles.SAMPLE_ANALYSIS,
        DataTemplates.ID_SAMPLE_ANALYSIS.format(partition=CONFIG["DATA_PARTITION"]),
        SamplesAnalysisTypes.CCE,
    )
    return record_data["id"]


@pytest.fixture(scope="module")
def dataset_id_v1(api, helper, record_id, tests_data, analysis_type, cce_record_id):
    """Generic fixture to create a V1 dataset."""
    # 1. Lookup the correct data file for this Analysis Type + V1
    file_key = VersionedDataFiles.VALUES.get((analysis_type, SchemaVersions.V1_0_0))

    # 2. Load and Prepare Data
    data_payload = copy.deepcopy(tests_data(file_key))
    data_payload["data"][0][0] = f"{record_id}:"
    data_payload["data"][0][7] = f"{cce_record_id}:"

    # 3. Post
    post_response = api.sample_analysis.post_data(
        record_id=record_id,
        body=data_payload,
        analysis_type=analysis_type,
        schema_version=SchemaVersions.V1_0_0,
    )
    return helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])


@pytest.fixture
def pagination_case_v1(
    api,
    create_isolated_samples_analysis_pagination_case,
    delete_record,
    helper,
    tests_data,
    analysis_type,
):
    """Create isolated Saturation Test pagination data and its CCE dependency."""
    cce_record = copy.deepcopy(
        tests_data(DataFiles.SAMPLE_ANALYSIS, SamplesAnalysisTypes.CCE),
    )
    cce_record["id"] = (
        f"{DataTemplates.ID_SAMPLE_ANALYSIS.format(partition=CONFIG['DATA_PARTITION'])}"
        f"{helper.generate_random_record_id()}"
    )
    api.sample_analysis.post_record([cce_record])
    delete_record(cce_record["id"])

    def _prepare_data(data_payload):
        source_analysis_index = data_payload["columns"].index("SourceAnalysisID")
        for row in data_payload["data"]:
            row[source_analysis_index] = f"{cce_record['id']}:"

    return create_isolated_samples_analysis_pagination_case(
        analysis_type,
        SchemaVersions.V1_0_0,
        prepare_data=_prepare_data,
    )
