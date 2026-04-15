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
)

dir_path = os.path.dirname(os.path.abspath(__file__))

TEST_DATASET_RECORD_ID = f"opendes:dataset--File.Generic:slimtube-123:1234"
TEST_DDMS_URN = f"urn://rafs-v2/slimtubedata/partition:work-product-component--SamplesAnalysis:samplesanalysis_test/{TEST_DATASET_RECORD_ID}"
TEST_SCHEMA_VERSION = "1.0.0"
TEST_DDMS_URN_WITH_VERSION = f"{TEST_DDMS_URN}/{TEST_SCHEMA_VERSION}"
RECORD_DATA = {
    **OSDU_GENERIC_RECORD.dict(exclude_none=True), **{
        "data": {
            "DDMSDatasets": [TEST_DDMS_URN],
        },
    },
}
RECORD_DATA_WITH_SCHEMA_VERSION = {
    **OSDU_GENERIC_RECORD.dict(exclude_none=True), **{
        "data": {
            "DDMSDatasets": [TEST_DDMS_URN_WITH_VERSION],
        },
    },
}
RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION = {
    **OSDU_GENERIC_RECORD.dict(exclude_none=True), **{
        "data": {
            "DDMSDatasets": [f"{TEST_DDMS_URN}/2.0.0"],
        },
    },
}
TEST_PARAMS_AGGREGATION = {
    "columns_aggregation": "TestNumber,count",
}
TEST_PARAMS_FILTERS = {
    "columns_filter": "SamplesAnalysisID,SampleID,TestNumber,MinimumMiscibilityPressure",
    "rows_filter": "SamplesAnalysisID,eq,opendes:work-product-component--SamplesAnalysis:samplesanalysis_test:",
}

with open(f"{dir_path}/slimtube_orient_split.json") as fp:
    TEST_DATA = json.load(fp)

TEST_AGGREGATED_DATA = {
    "columns": [
        "TestNumber",
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
        "TestNumber",
        "MinimumMiscibilityPressure",
    ],
    "index": [
        0,
    ],
    "data": [
        [
            "opendes:work-product-component--SamplesAnalysis:samplesanalysis_test:",
            "opendes:master-data--Sample:fluid_sample_test:",
            "1A",
            1.23,
        ],
    ],
}

INCORRECT_SCHEMA_TEST_DATA = {
    "columns": [
        "WrongField",  # Wrong field
        "SampleID",
        # "SamplesAnalysisID",  # Missing mandatory field
    ],
    "index": [0],
    "data": [
        [
            "opendes:work-product-component--SamplesAnalysis:samplesanalysis_test:",
            "opendes:master-data--:1:",  # Incorrect fluid sample value
        ],
    ],
}

INCORRECT_DATAFRAME_TEST_DATA = copy.deepcopy(TEST_DATA)
INCORRECT_DATAFRAME_TEST_DATA["data"][0].pop()  # deleting SlimTubeTestID
EXPECTED_ERROR_REASON = "Data error: 16 columns passed, passed data had 15 columns"


TEST_SCHEMA_VERSION_V2 = "2.0.0"
TEST_DDMS_URN_WITH_VERSION_V2 = f"{TEST_DDMS_URN}/{TEST_SCHEMA_VERSION_V2}"
RECORD_DATA_WITH_SCHEMA_VERSION_V2 = {
    **OSDU_GENERIC_RECORD.dict(exclude_none=True), **{
        "data": {
            "DDMSDatasets": [TEST_DDMS_URN_WITH_VERSION_V2],
        },
    },
}
with open(f"{dir_path}/slimtube_orient_split_2.0.0.json") as fp:
    TEST_DATA_V2 = json.load(fp)

TEST_AGGREGATED_DATA_V2 = {
    "columns": [
        "TestNumber",
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

TEST_PARAMS_FILTERS_V2 = {
    "columns_filter": "SamplesAnalysisID,SampleID,TestNumber,MinimumMiscibilityPressure",
    "rows_filter": "SamplesAnalysisID,eq,namespace:work-product-component--SamplesAnalysis:sample-analysis-001:",
}
TEST_FILTERED_DATA_V2 = {
    "columns": [
        "SamplesAnalysisID",
        "SampleID",
        "TestNumber",
        "MinimumMiscibilityPressure",
    ],
    "index": [
        0,
    ],
    "data": [
        [
            "namespace:work-product-component--SamplesAnalysis:sample-analysis-001:",
            "namespace:master-data--Sample:sample-001:",
            "STT-2026-001",
            1800,
        ],
    ],
}

INCORRECT_DATAFRAME_TEST_DATA_V2 = copy.deepcopy(TEST_DATA_V2)
INCORRECT_DATAFRAME_TEST_DATA_V2["data"][0].pop()
EXPECTED_ERROR_REASON_V_2_0_0 = f"Data error: {len(INCORRECT_DATAFRAME_TEST_DATA['columns'])} columns passed, " \
    f"passed data had {len(INCORRECT_DATAFRAME_TEST_DATA['data'][0])} columns"
