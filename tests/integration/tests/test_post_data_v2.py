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
import json
import os
import random
import re

import pytest
from starlette import status

from tests.integration.config import (
    ACCEPT_HEADERS,
    CONFIG,
    SCHEMA_VERSION,
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
@pytest.mark.v2
def test_post_measurements(
    api, create_record, helper, tests_data, measurements_file, dataset_prefix, analysis_type,
):
    record_data, _ = create_record(
        DataTypes.SAMPLE_ANALYSIS, DataFiles.SAMPLE_ANALYSIS,
        DataTemplates.ID_SAMPLE_ANALYSIS.format(partition=CONFIG["DATA_PARTITION"]),
        analysis_type,
    )
    tests_data = tests_data(measurements_file)
    test_data = copy.deepcopy(tests_data)
    test_data["data"][0][0] = f'{record_data["id"]}:'

    response = api.sample_analysis.post_measurements(record_data["id"], test_data, analysis_type)

    # remove when fully migrated to blob storage
    rafs_use_blob_storage = os.getenv("RAFS_USE_BLOB_STORAGE")
    if rafs_use_blob_storage and rafs_use_blob_storage == "True":
        assert f"samplesanalysis/{dataset_prefix}" in response["ddms_urn"]
    else:
        assert f"{dataset_prefix}data" in response["ddms_urn"]

    record = api.sample_analysis.get_record(record_data["id"])
    assert "DDMSDatasets" in record["data"]


@pytest.mark.parametrize(
    "measurements_file, analysis_type", [(DataFiles.NMR_DATA, SamplesAnalysisTypes.NMR)],
)
@pytest.mark.smoke
@pytest.mark.v2
def test_post_measurements_with_non_existent_record_id(
    api, helper, create_record, tests_data, measurements_file, analysis_type,
):
    measurements = copy.deepcopy(tests_data(measurements_file))
    record_data, _ = create_record(
        DataTypes.SAMPLE_ANALYSIS, DataFiles.SAMPLE_ANALYSIS,
        DataTemplates.ID_SAMPLE_ANALYSIS.format(partition=CONFIG["DATA_PARTITION"]),
        analysis_type,
    )
    measurements["data"][0][0] = f'{record_data["id"]}:'
    samples_analysis_id = DataTemplates.ID_SAMPLE_ANALYSIS.format(partition=CONFIG["DATA_PARTITION"])
    api.sample_analysis.post_measurements(
        f"{samples_analysis_id}{helper.generate_random_record_id()}",
        measurements,
        analysis_type,
        allowed_codes=[status.HTTP_404_NOT_FOUND],
    )


@pytest.mark.parametrize(
    "measurements_file, analysis_type", [(DataFiles.NMR_WRONG_ID, SamplesAnalysisTypes.NMR)],
)
@pytest.mark.smoke
@pytest.mark.v2
def test_post_measurements_validation_failed(
        api, tests_data, create_record, measurements_file, analysis_type,
):
    record_data, _ = create_record(
        DataTypes.SAMPLE_ANALYSIS, DataFiles.SAMPLE_ANALYSIS,
        DataTemplates.ID_SAMPLE_ANALYSIS.format(partition=CONFIG["DATA_PARTITION"]),
        analysis_type,
    )
    measurements = tests_data(measurements_file, analysis_type)

    error = api.sample_analysis.post_measurements(
        record_data["id"],
        measurements,
        analysis_type,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_ENTITY],
    )
    json_string = json.dumps(measurements)
    wrong_id_count = len(re.findall(r"WrongID\d+", json_string))
    missing_records = error["errors"]["Missing records in storage"]

    assert error["reason"] == "Data validation failed."
    try:
        assert len(missing_records) == wrong_id_count
    except AssertionError:
        actual_ids = [int(item.split("WrongID")[1]) for item in missing_records]
        missing_ids = list(filter(lambda x: x not in actual_ids, range(min(actual_ids), max(actual_ids) + 1)))
        sorted_list = sorted(missing_records, key=lambda x: int(x.split("WrongID")[1]))
        ordered_list = "\n".join(sorted_list)
        raise AssertionError(
            f"The number of returned WrongIDs is {len(missing_records)} which is less than the expected {wrong_id_count}.\n"
            f"The response {analysis_type.upper()} is missing WrongID{missing_ids}\n\n{ordered_list}",
        )


@pytest.mark.parametrize(
    "analysis_type", [SamplesAnalysisTypes.NMR],
)
@pytest.mark.smoke
@pytest.mark.v2
def test_post_measurements_with_empty_body(
        api, create_record, analysis_type,
):
    record_data, _ = create_record(
        DataTypes.SAMPLE_ANALYSIS, DataFiles.SAMPLE_ANALYSIS,
        DataTemplates.ID_SAMPLE_ANALYSIS.format(partition=CONFIG["DATA_PARTITION"]),
        analysis_type,
    )

    api.sample_analysis.post_measurements(
        record_data["id"],
        {},
        analysis_type,
        allowed_codes=[status.HTTP_400_BAD_REQUEST],
    )


@pytest.mark.parametrize(
    "measurements_file, analysis_type", [
        (DataFiles.NMR_DATA, SamplesAnalysisTypes.NMR),
    ],
)
@pytest.mark.smoke
@pytest.mark.v2
def test_post_measurements_with_empty_dataset_version(
        api, helper, measurements_file, analysis_type,
):
    samples_analysis_id = DataTemplates.ID_SAMPLE_ANALYSIS.format(partition=CONFIG["DATA_PARTITION"])
    error = api.sample_analysis.post_measurements(
        f"{samples_analysis_id}{helper.generate_random_record_id()}",
        measurements_file,
        analysis_type,
        schema_version_header=None,
        allowed_codes=[status.HTTP_400_BAD_REQUEST],
    )

    assert "No schema version specified or invalid schema format. " \
           "Check if the schema version is specified in the 'Accept' header. " \
           f"Example: --header 'Accept: */*;version={SCHEMA_VERSION}" in error["reason"]


@pytest.mark.parametrize(
    "measurements_file, analysis_type", [
        (DataFiles.NMR_DATA, SamplesAnalysisTypes.NMR),
    ],
)
@pytest.mark.smoke
@pytest.mark.v2
def test_post_measurements_with_wrong_dataset_version(
        api, helper, measurements_file, analysis_type,
):
    version = random.choice(["0.0.0", "1.11.0", "11.111.000.", "100000000.1000000.100000000"])
    samples_analysis_id = DataTemplates.ID_SAMPLE_ANALYSIS.format(partition=CONFIG["DATA_PARTITION"])
    error = api.sample_analysis.post_measurements(
        f"{samples_analysis_id}{helper.generate_random_record_id()}",
        measurements_file,
        analysis_type,
        schema_version_header=ACCEPT_HEADERS.format(version=version),
        allowed_codes=[status.HTTP_400_BAD_REQUEST],
    )

    assert "There is no model for given version. " \
           f"Schema version {version.rstrip('.')} is not one of proper versions: {{'{SCHEMA_VERSION}'}}" in error[
               "reason"
           ]


@pytest.mark.skip(reason="issues/66")
@pytest.mark.parametrize(
    "measurements_file, analysis_type, mandatory_fields", [
        (
            DataFiles.NMR_DATA, SamplesAnalysisTypes.NMR, ["SamplesAnalysisID", "SampleID"],
        ),
    ],
)
@pytest.mark.smoke
@pytest.mark.v2
def test_post_measurements_mandatory_columns_missing(api, tests_data, create_record, analysis_type, measurements_file, mandatory_fields):
    record_data, created_record = create_record(
        DataTypes.SAMPLE_ANALYSIS,
        DataFiles.SAMPLE_ANALYSIS,
        DataTemplates.ID_SAMPLE_ANALYSIS.format(partition=CONFIG["DATA_PARTITION"]),
    )

    tests_data = tests_data(measurements_file)
    test_data = copy.deepcopy(tests_data)

    # Find the indices of the columns to be removed from test_data.
    indices = [test_data["columns"].index(key) for key in mandatory_fields]

    # Remove the columns and their corresponding data from test_data.
    for column_index in sorted(indices, reverse=True):
        del test_data["columns"][column_index]
        for data_index in range(len(test_data["index"])):
            del test_data["data"][data_index][column_index]

    error = api.sample_analysis.post_measurements(
        record_data["id"],
        test_data,
        analysis_type,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_ENTITY],
    )

    assert error["reason"] == "Data validation failed."
    assert error["errors"] == {
        "Mandatory parameters missing": mandatory_fields,
    }
