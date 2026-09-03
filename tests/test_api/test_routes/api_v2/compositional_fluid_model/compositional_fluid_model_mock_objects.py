#  Copyright 2026 ExxonMobil Technology and Engineering Company
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
from app.resources.paths import FLUID_MODEL_STR
from tests.test_api.test_routes.osdu.storage_mock_objects import (
    OSDU_GENERIC_RECORD,
    TEST_FLUID_MODEL_ID,
    BulkDatasetIdV2,
)

dir_path = os.path.dirname(os.path.abspath(__file__))


TEST_DATASET_RECORD_ID = BulkDatasetIdV2.COMPOSITIONAL_FLUID_MODEL
TEST_DDMS_URN = f"urn://rafs-v2/compositional{FLUID_MODEL_STR}data/{TEST_FLUID_MODEL_ID}/{TEST_DATASET_RECORD_ID}"
TEST_SCHEMA_VERSION = ContentSchemaVersion.V_1_0_0
TEST_DDMS_URN_WITH_VERSION = f"{TEST_DDMS_URN}/{TEST_SCHEMA_VERSION}"
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
    "columns_aggregation": "FluidModelID,count",
}
TEST_PARAMS_FILTERS = {
    "columns_filter": "FluidModelID",
    "rows_filter": f"FluidModelID,eq,{TEST_FLUID_MODEL_ID}:",
}

with open(f"{dir_path}/compositional_fluid_model_orient_split.json") as fp:
    TEST_DATA = json.load(fp)
    TRIMMED_TEST_DATA = {  # data used for x-parquet ingestion, only one type per request
        "columns": TEST_DATA["columns"],
        "index": [
            0
        ],
        "data": [
            TEST_DATA["data"][0]
        ],
    }

TEST_AGGREGATED_DATA = {
    "columns": [
        "FluidModelID"
    ],
    "index": [
        "count"
    ],
    "data": [
        [
            1
        ]
    ],
}

TEST_FILTERED_DATA = {
    "columns": [
        "FluidModelID"
    ],
    "index": [
        0
    ],
    "data": [
        [
            f"{TEST_FLUID_MODEL_ID}:"
        ]
    ],
}

INCORRECT_SCHEMA_TEST_DATA = {
    "columns": [
        "WrongField",  # Wrong field
        "data",
        # "FluidModelID"   # Missing mandatory field
    ],
    "index": [
        0
    ],
    "data": [
        [
            "partition:work-product-component--FluidModel:fluid_model_test_id",
            "opendes:master-data--:1:",  # Incorrect master-data value
        ],
    ],
}

INCORRECT_DATAFRAME_TEST_DATA = copy.deepcopy(TRIMMED_TEST_DATA)
INCORRECT_DATAFRAME_TEST_DATA["data"][0].pop()
TEST_DATA_COLUMNS = len(TRIMMED_TEST_DATA["data"][0])
EXPECTED_ERROR_REASON = (
    f"Data error: {TEST_DATA_COLUMNS} columns passed, passed data had {TEST_DATA_COLUMNS - 1} columns"
)
