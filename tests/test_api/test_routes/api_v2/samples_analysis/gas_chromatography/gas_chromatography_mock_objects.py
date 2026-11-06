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
    TEST_SAMPLE_ID_2,
)
from tests.test_api.test_routes.api_v2.samples_analysis.samples_analysis_mock_objects import (
    SamplesAnalysisDatasetIDsV2,
    SamplesAnalysisDDDMSURNsV2,
    TEST_MISMATCHED_SAMPLE_ID, 
)

dir_path = os.path.dirname(os.path.abspath(__file__))

TEST_DATASET_RECORD_ID = SamplesAnalysisDatasetIDsV2.GAS_CHROMATOGRAPHY
TEST_DDMS_URN = SamplesAnalysisDDDMSURNsV2.GAS_CHROMATOGRAPHY
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
    "columns_aggregation": "SampleID,count",
}
TEST_PARAMS_FILTERS = {
    "columns_filter": "SamplesAnalysisID,SampleID",
    "rows_filter": f"SampleID,eq,{TEST_SAMPLE_ID}",
}

with open(f"{dir_path}/gas_chromatography_orient_split.json") as fp:
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
    ],
    "index": [
        0,
    ],
    "data": [
        [
            TEST_SAMPLES_ANALYSIS_ID,
            TEST_SAMPLE_ID,
        ],
    ],
}

INCORRECT_SCHEMA_TEST_DATA = {
    "columns": [
        "WrongField",  # Wrong field
        "data",
        # "SamplesAnalysisID",  # Missing mandatory field
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
INCORRECT_DATAFRAME_TEST_DATA["data"][0].pop()
EXPECTED_ERROR_REASON = (
    f"Data error: {len(INCORRECT_DATAFRAME_TEST_DATA['columns'])} columns passed, "
    f"passed data had {len(INCORRECT_DATAFRAME_TEST_DATA['data'][0])} columns"
)

# ==============================================================================
# Mock objects for testing SampleID consistency between content data and the 
# associated OSDU record's SampleIDs.
#
# Most models share standard mock objects from sample_analysis_mock_objects. 
# However, gas chromatography uses custom mock objects to include the required 
# SampleMass field.
# ==============================================================================

TEST_DATA_PAYLOAD_WITH_MISMATCHED_SAMPLE_ID = {
    "columns":[
        "SamplesAnalysisID",
        "SampleID",
        "SampleMass",
        "Meta",
    ],
    "index":[
        0,
    ],
    "data":[
        [
            TEST_SAMPLES_ANALYSIS_ID,
            TEST_MISMATCHED_SAMPLE_ID, 
            1,
            [],
        ]
    ]
}

TEST_MULTI_ROW_DATA_PAYLOAD_WITH_MISMATCHED_SAMPLE_ID = {
    "columns":[
        "SamplesAnalysisID",
        "SampleID",
        "SampleMass",
        "Meta", 
    ],
    "index":[
        0, 
        1, 
    ],
    "data":[
        [
            TEST_SAMPLES_ANALYSIS_ID,
            TEST_SAMPLE_ID, 
            1,
            [],
        ], 
        [
            TEST_SAMPLES_ANALYSIS_ID,
            TEST_MISMATCHED_SAMPLE_ID, 
            7,
            [], 
        ], 
    ]
}

TEST_MULTI_ROW_DATA_PAYLOAD = {
    "columns":[
        "SamplesAnalysisID",
        "SampleID",
        "SampleMass",
        "Meta",
    ],
    "index":[
        0, 
        1, 
    ],
    "data":[
        [
            TEST_SAMPLES_ANALYSIS_ID,
            TEST_SAMPLE_ID, 
            1,
            [], 
        ], 
        [
            TEST_SAMPLES_ANALYSIS_ID,
            TEST_SAMPLE_ID_2, 
            1,
            [], 
        ], 
    ]
}

TEST_DATA_PAYLOAD = {
    "columns":[
        "SamplesAnalysisID",
        "SampleID",
        "SampleMass",
        "Meta",
    ],
    "index":[
        0, 
    ],
    "data":[
        [
            TEST_SAMPLES_ANALYSIS_ID,
            TEST_SAMPLE_ID, 
            1,
            [], 
        ], 
    ]
}

TEST_DATA_PAYLOAD_WITH_NULL_SAMPLE_ID = {
    "columns":[
        "SamplesAnalysisID",
        "SampleID",
        "SampleMass",
        "Meta",
    ],
    "index":[
        0, 
    ],
    "data":[
        [
            TEST_SAMPLES_ANALYSIS_ID,
            None, 
            1,
            [], 
        ], 
    ]
}
