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

TEST_DATASET_RECORD_ID = "opendes:dataset--File.Generic:triaxialdata-123:1234"
TEST_DDMS_URN = f"urn://rafs-v2/triaxialdata/{TEST_SAMPLESANALYSIS_ID}/{TEST_DATASET_RECORD_ID}"
TEST_SCHEMA_VERSION = "1.0.0"
TEST_DDMS_URN_WITH_VERSION = f"urn://rafs-v2/triaxialdata/{TEST_SAMPLESANALYSIS_ID}/{TEST_DATASET_RECORD_ID}/{TEST_SCHEMA_VERSION}"
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
    "columns_aggregation": "SamplesAnalysisID,count",
}
TEST_PARAMS_FILTERS = {
    "columns_filter": "SamplesAnalysisID,SampleID,BulkDensityAsReceived,TestPorePressure,MassAsReceived,TestSteps",
    "rows_filter": "SampleID,eq,opendes:master-data--Sample:TriaxialTest_Sample:",
}

with open(f"{dir_path}/triaxial_test_orient_split.json") as fp:
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
        "SampleID",
        "BulkDensityAsReceived",
        "TestPorePressure",
        "MassAsReceived",
        "TestSteps",
    ],
    "index": [
        0,
    ],
    "data": [
        [
            "opendes:work-product-component--SamplesAnalysis:TriaxialTest_WPC:",
            "opendes:master-data--Sample:TriaxialTest_Sample:",
            {
                "Value": 0.47,
                "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:g%2Fcm3:",
            },
            {
                "Value": 23,
                "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:psi:",
            },
            {
                "Value": 3.21,
                "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:mg:",
            },
            [
                {
                    "Time": {
                        "Value": 65,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:s:",
                    },
                    "PorePressure": {
                        "Value": 32,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:psi:",
                    },
                    "ConfiningPressure": {
                        "Value": 44,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:psi:",
                    },
                    "AxialStrain": {
                        "Value": 65,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:psi:",
                    },
                    "RadialStrain": {
                        "Value": 87,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:psi:",
                    },
                    "AxialStress": {
                        "Value": 122,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:psi:",
                    },
                    "DifferentialStress": {
                        "Value": 21,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:psi:",
                    },
                    "AxialPWaveVelocity": {
                        "Value": 5,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:m%2Fs:",
                    },
                    "AxialSWaveVelocity": {
                        "Value": 3,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:m%2Fs:",
                    },
                },
            ],
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
            "opendes:work-product-component--SamplesAnalysis:1:",
            "opendes:master-data--:1:",  # Incorrect master-data value
        ],
    ],
}

INCORRECT_DATAFRAME_TEST_DATA = copy.deepcopy(TEST_DATA)
INCORRECT_DATAFRAME_TEST_DATA["data"][0].pop()  # deleting Interpretation in index row 0
EXPECTED_ERROR_REASON = "Data error: 18 columns passed, passed data had 17 columns"
