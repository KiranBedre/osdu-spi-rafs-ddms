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
def test_validate_file_data_content(
    api, create_record, helper, tests_data, measurements_file, dataset_prefix, analysis_type,
):
    record_data, _ = create_record(
        DataTypes.SAMPLE_ANALYSIS,
        DataFiles.SAMPLE_ANALYSIS,
        DataTemplates.ID_SAMPLE_ANALYSIS.format(partition=CONFIG["DATA_PARTITION"]),
        analysis_type,
    )
    tests_data = tests_data(measurements_file)
    test_data = copy.deepcopy(tests_data)
    test_data["data"][0][0] = f'{record_data["id"]}:'

    full_dataset_id = api.sample_analysis.post_measurements(record_data["id"], test_data, analysis_type)["ddms_urn"]
    content_id = helper.get_content_id_from_ddms_urn(full_dataset_id)

    measurements_json = api.sample_analysis.get_measurements(record_data["id"], content_id, analysis_type)
    measurements_parquet = api.sample_analysis.get_measurements(
        record_data["id"], content_id, analysis_type, json=False, content_type="application/x-parquet",
    ).content

    helper.compare_responses(measurements_json, measurements_parquet)
