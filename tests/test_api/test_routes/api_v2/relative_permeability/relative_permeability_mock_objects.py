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
    TEST_SAMPLESANALYSIS_ID,
    BulkDatasetIdV2,
)

dir_path = os.path.dirname(os.path.abspath(__file__))

TEST_DATASET_RECORD_ID = BulkDatasetIdV2.RELATIVE_PERMEABILITY
TEST_DDMS_URN = f"urn://rafs-v2/relativepermeabilitydata/{TEST_SAMPLESANALYSIS_ID}/{TEST_DATASET_RECORD_ID}"
TEST_SCHEMA_VERSION = ContentSchemaVersion.V_1_0_0
TEST_DDMS_URN_WITH_VERSION = f"{TEST_DDMS_URN}/{TEST_SCHEMA_VERSION}"
RECORD_DATA = {
    **OSDU_GENERIC_RECORD.model_dump(exclude_none=True),
    **{
        "data": {
            "DDMSDatasets": [TEST_DDMS_URN],
        },
    },
}
RECORD_DATA_WITH_SCHEMA_VERSION = {
    **OSDU_GENERIC_RECORD.model_dump(exclude_none=True),
    **{
        "data": {
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
    "columns_filter": "SamplesAnalysisID",
    "rows_filter": "SamplesAnalysisID,eq,partition:work-product-component--SamplesAnalysis:samplesanalysis_test:",
}

with open(f"{dir_path}/relative_permeability_orient_split.json") as fp:
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
    ],
    "index": [
        0,
    ],
    "data": [
        [
            "partition:work-product-component--SamplesAnalysis:samplesanalysis_test:",
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


# V1.1.0 mock objects
TEST_SCHEMA_VERSION_V1_1 = ContentSchemaVersion.V_1_1_0
TEST_DDMS_URN_WITH_VERSION_V1_1 = f"{TEST_DDMS_URN}/{TEST_SCHEMA_VERSION_V1_1}"
RECORD_DATA_WITH_SCHEMA_VERSION_V1_1 = {
    **OSDU_GENERIC_RECORD.model_dump(exclude_none=True),
    **{
        "data": {
            "DDMSDatasets": [TEST_DDMS_URN_WITH_VERSION_V1_1],
        },
    },
}
TEST_PARAMS_AGGREGATION_V1_1 = {
    "columns_aggregation": "SampleID,count",
}
TEST_PARAMS_FILTERS_V1_1 = {
    "columns_filter": "SamplesAnalysisID,SampleID,PermeabilityTestSteps",
    "rows_filter": "SamplesAnalysisID,eq,partition:work-product-component--SamplesAnalysis:samplesanalysis_test:",
}

with open(f"{dir_path}/relative_permeability_orient_split_1.1.0.json") as fp:
    TEST_DATA_V1_1 = json.load(fp)

TEST_AGGREGATED_DATA_V1_1 = {
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

TEST_FILTERED_DATA_V1_1 = {
    "columns": [
        "SamplesAnalysisID",
        "SampleID",
        "PermeabilityTestSteps",
    ],
    "index": [
        0,
    ],
    "data": [
        [
            "partition:work-product-component--SamplesAnalysis:samplesanalysis_test:",
            "opendes:master-data--Sample:Sample_200:",
            TEST_DATA_V1_1["data"][0][19],
        ],
    ],
}

INCORRECT_DATAFRAME_TEST_DATA_V1_1 = copy.deepcopy(TEST_DATA_V1_1)
INCORRECT_DATAFRAME_TEST_DATA_V1_1["data"][0].pop()
EXPECTED_ERROR_REASON_V1_1 = (
    f"Data error: {len(INCORRECT_DATAFRAME_TEST_DATA_V1_1['columns'])} columns passed, "
    f"passed data had {len(INCORRECT_DATAFRAME_TEST_DATA_V1_1['data'][0])} columns"
)


# V2.0.0 mock objects
TEST_SCHEMA_VERSION_V2 = ContentSchemaVersion.V_2_0_0
TEST_DDMS_URN_WITH_VERSION_V2 = f"{TEST_DDMS_URN}/{TEST_SCHEMA_VERSION_V2}"
RECORD_DATA_WITH_SCHEMA_VERSION_V2 = {
    **OSDU_GENERIC_RECORD.model_dump(exclude_none=True),
    **{
        "data": {
            "DDMSDatasets": [TEST_DDMS_URN_WITH_VERSION_V2],
        },
    },
}
TEST_PARAMS_AGGREGATION_V2 = {
    "columns_aggregation": "SampleID,count",
}
TEST_PARAMS_FILTERS_V2 = {
    "columns_filter": "SamplesAnalysisID,SampleID,DesaturationMethodID",
    "rows_filter": "SampleID,eq,partition:master-data--Sample:uuuid:12345",
}

with open(f"{dir_path}/relative_permeability_orient_split_2.0.0.json") as fp:
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
            "partition:master-data--Sample:uuuid:12345",
            "partition:reference-data--DesaturationMethod:CentrifugeGasWater:",
        ],
    ],
}

INCORRECT_DATAFRAME_TEST_DATA_V2 = copy.deepcopy(TEST_DATA_V2)
INCORRECT_DATAFRAME_TEST_DATA_V2["data"][0].pop()
EXPECTED_ERROR_REASON_V2 = (
    f"Data error: {len(INCORRECT_DATAFRAME_TEST_DATA_V2['columns'])} columns passed, "
    f"passed data had {len(INCORRECT_DATAFRAME_TEST_DATA_V2['data'][0])} columns"
)
