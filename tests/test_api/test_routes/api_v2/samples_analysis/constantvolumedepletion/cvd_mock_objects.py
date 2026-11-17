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

from app.models.data_schemas.version import ContentSchemaVersion
from tests.test_api.test_routes.osdu.storage_mock_objects import (
    OSDU_GENERIC_RECORD,
    TEST_SAMPLES_ANALYSIS_ID,
    TEST_SAMPLE_ID,
)
from tests.test_api.test_routes.api_v2.samples_analysis.samples_analysis_mock_objects import (
    SamplesAnalysisDatasetIDsV2,
    SamplesAnalysisDDDMSURNsV2,
)

dir_path = os.path.dirname(os.path.abspath(__file__))

TEST_DATASET_RECORD_ID = SamplesAnalysisDatasetIDsV2.CVD
TEST_DDMS_URN = SamplesAnalysisDDDMSURNsV2.CVD
TEST_SCHEMA_VERSION = ContentSchemaVersion.V_1_0_0
TEST_DDMS_URN_WITH_VERSION = f"{TEST_DDMS_URN}/{TEST_SCHEMA_VERSION}"
RECORD_DATA = {
    **OSDU_GENERIC_RECORD.model_dump(exclude_none=True),
    **{
        "data": {
            "SampleIDs": [TEST_SAMPLE_ID],
            "DDMSDatasets": [TEST_DDMS_URN],
        },
    },
}
RECORD_DATA_WITH_SCHEMA_VERSION = {
    **OSDU_GENERIC_RECORD.model_dump(exclude_none=True),
    **{
        "data": {
            "SampleIDs": [TEST_SAMPLE_ID],
            "DDMSDatasets": [TEST_DDMS_URN_WITH_VERSION],
        },
    },
}
RECORD_DATA_WITH_IMPROPER_SCHEMA_VERSION = {
    **OSDU_GENERIC_RECORD.model_dump(exclude_none=True),
    **{
        "data": {
            "DDMSDatasets": [f"{TEST_DDMS_URN}/2.0.0"],
        },
    },
}
TEST_PARAMS_AGGREGATION = {
    "columns_aggregation": "SamplesAnalysisID,count",
}
TEST_PARAMS_FILTERS = {
    "columns_filter": "SamplesAnalysisID",
    "rows_filter": f"SamplesAnalysisID,eq,{TEST_SAMPLES_ANALYSIS_ID}",
}

with open(f"{dir_path}/cvd_orient_split.json") as fp:
    TEST_DATA = json.load(fp)

TEST_AGGREGATED_DATA = {
    "columns": [
        "SamplesAnalysisID",
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
    ],
    "index": [
        0,
    ],
    "data": [
        [
            TEST_SAMPLES_ANALYSIS_ID,
        ],
    ],
}

INCORRECT_SCHEMA_TEST_DATA = {
    "columns": [
        # "SamplesAnalysisID",  # Missing mandatory field
        "WrongField",  # Wrong field
        "TestNumber",
        "FluidSampleID",
    ],
    "index": [0],
    "data": [
        [
            "partition:work-product-component--SamplesAnalysis:samplesanalysis_test:",
            "1",
            "opendes:master-data--:1:",  # Incorrect Value
        ],
    ],
}

INCORRECT_DATAFRAME_TEST_DATA = copy.deepcopy(TEST_DATA)
INCORRECT_DATAFRAME_TEST_DATA["data"][0].pop()
EXPECTED_ERROR_REASON = (
    f"Data error: {len(INCORRECT_DATAFRAME_TEST_DATA['columns'])} columns passed, "
    f"passed data had {len(INCORRECT_DATAFRAME_TEST_DATA['data'][0])} columns"
)
