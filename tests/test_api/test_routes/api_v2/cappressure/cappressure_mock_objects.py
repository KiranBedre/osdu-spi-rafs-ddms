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

from tests.test_api.test_routes.osdu.storage_mock_objects import (
    OSDU_GENERIC_RECORD,
    TEST_SAMPLESANALYSIS_ID,
)

dir_path = os.path.dirname(os.path.abspath(__file__))

TEST_DATASET_RECORD_ID = "opendes:dataset--File.Generic:capillarypressuredata-12345:1234"
TEST_DDMS_URN = f"urn://rafs-v2/capillarypressuredata/{TEST_SAMPLESANALYSIS_ID}/{TEST_DATASET_RECORD_ID}"
TEST_SCHEMA_VERSION = "1.0.0"
TEST_DDMS_URN_WITH_VERSION = (
    f"urn://rafs-v2/capillarypressuredata/{TEST_SAMPLESANALYSIS_ID}/{TEST_DATASET_RECORD_ID}/{TEST_SCHEMA_VERSION}"
)
RECORD_DATA = {
    **OSDU_GENERIC_RECORD.dict(exclude_none=True),
    **{
        "data": {
            "DDMSDatasets": [TEST_DDMS_URN],
        },
    },
}
RECORD_DATA_WITH_SCHEMA_VERSION = {
    **OSDU_GENERIC_RECORD.dict(exclude_none=True),
    **{
        "data": {
            "DDMSDatasets": [TEST_DDMS_URN_WITH_VERSION],
        },
    },
}
RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION = {
    **OSDU_GENERIC_RECORD.dict(exclude_none=True),
    **{
        "data": {
            "DDMSDatasets": [f"{TEST_DDMS_URN}/2.0.0"],
        },
    },
}
TEST_PARAMS_AGGREGATION = {
    "columns_aggregation": "SampleID,count",
}
TEST_PARAMS_FILTERS = {
    "columns_filter": "SamplesAnalysisID,SampleID,DesaturationMethodID",
    "rows_filter": "SamplesAnalysisID,eq,partition:work-product-component--SamplesAnalysis:samplesanalysis_test:",
}

with open(f"{dir_path}/cappressure_orient_split.json") as fp:
    TEST_DATA = json.load(fp)

TEST_AGGREGATED_DATA = {
    "columns": [
        "SampleID",
    ],
    "index": [
        "count",
    ],
    "data": [
        [
            1,
        ],
    ],
}

TEST_FILTERED_DATA = {
    "columns": [
        "SamplesAnalysisID",
        "SampleID",
        "DesaturationMethodID",
    ],
    "index": [
        0,
    ],
    "data": [
        [
            "partition:work-product-component--SamplesAnalysis:samplesanalysis_test:",
            "opendes:master-data--Sample:CapillaryPressure_Sample:",
            "opendes:reference-data--DesaturationMethod:Centrifuge:",
        ],
    ],
}

INCORRECT_SCHEMA_TEST_DATA = {
    "columns": [
        "WrongField",  # Wrong field
        "data",
        # "MultiStageSeparatorTestSteps",  # Missing mandatory field
    ],
    "index": [0],
    "data": [
        [
            "partition:work-product-component--SamplesAnalysis:samplesanalysis_test:",
            "opendes:master-data--:1:",  # Incorrect master-data value
        ],
    ],
}

INCORRECT_DATAFRAME_TEST_DATA = copy.deepcopy(TEST_DATA)
INCORRECT_DATAFRAME_TEST_DATA["data"][0].pop()  # deleting TestData in index row 0
EXPECTED_ERROR_REASON = "Data error: 24 columns passed, passed data had 23 columns"

# V1.1.0 mock objects
TEST_SCHEMA_VERSION_V2 = "1.1.0"
TEST_DDMS_URN_WITH_VERSION_V2 = f"{TEST_DDMS_URN}/{TEST_SCHEMA_VERSION_V2}"
RECORD_DATA_WITH_SCHEMA_VERSION_V2 = {
    **OSDU_GENERIC_RECORD.dict(exclude_none=True),
    **{
        "data": {
            "DDMSDatasets": [TEST_DDMS_URN_WITH_VERSION_V2],
        },
    },
}
with open(f"{dir_path}/cappressure_orient_split_v2.json") as fp:
    TEST_DATA_V2 = json.load(fp)

TEST_AGGREGATED_DATA_V2 = {
    "columns": [
        "SampleID",
    ],
    "index": [
        "count",
    ],
    "data": [
        [
            1,
        ],
    ],
}

TEST_FILTERED_DATA_V2 = {
    "columns": [
        "SamplesAnalysisID",
        "SampleID",
        "DesaturationMethodID",
    ],
    "index": [
        0,
    ],
    "data": [
        [
            "partition:work-product-component--SamplesAnalysis:samplesanalysis_test:",
            "opendes:master-data--Sample:CapillaryPressure_Sample:",
            "opendes:reference-data--DesaturationMethod:Centrifuge:",
        ],
    ],
}

INCORRECT_DATAFRAME_TEST_DATA_V2 = copy.deepcopy(TEST_DATA_V2)
INCORRECT_DATAFRAME_TEST_DATA_V2["data"][0].pop()
TEST_DATA_COLUMNS_V2 = len(TEST_DATA_V2["data"][0])
EXPECTED_ERROR_REASON_V2 = (
    f"Data error: {TEST_DATA_COLUMNS_V2} columns passed, passed data had {TEST_DATA_COLUMNS_V2 - 1} columns"
)
