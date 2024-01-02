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

TEST_DATASET_RECORD_ID = "opendes:dataset--File.Generic:wettabilityindexdata-123:1234"
TEST_DDMS_URN = f"urn://rafs-v2/wettabilityindexdata/{TEST_SAMPLESANALYSIS_ID}/{TEST_DATASET_RECORD_ID}"
TEST_SCHEMA_VERSION = "1.0.0"
TEST_DDMS_URN_WITH_VERSION = f"urn://rafs-v2/wettabilityindexdata/{TEST_SAMPLESANALYSIS_ID}/{TEST_DATASET_RECORD_ID}/{TEST_SCHEMA_VERSION}"
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
    "columns_aggregation": "SampleID,count",
}
TEST_PARAMS_FILTERS = {
    "columns_filter": "SamplesAnalysisID,SampleID,WettabilityIndexData",
    "rows_filter": "SampleID,eq,opendes:master-data--Sample:WettabilityIndex_Sample:",
}

with open(f"{dir_path}/wettability_index_orient_split.json") as fp:
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
        "WettabilityIndexData",
    ],
    "index": [
        0,
    ],
    "data": [
        [
            "opendes:work-product-component--SamplesAnalysis:WettabilityIndex_WPC:",
            "opendes:master-data--Sample:WettabilityIndex_Sample:",
            {
                "CapillaryPressureAnalysisID": "opendes:work-product-component--SamplesAnalysis:CapillaryPressure_WPC:",
                "ForcedImbibedBrineVolume": {
                    "Value": 12,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:cm3:",
                },
                "ForcedImbibedOilVolume": {
                    "Value": 32,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:cm3:",
                },
                "Temperature": {
                    "Value": 1.0,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:degF:",
                },
                "InitialBrineSaturation": {
                    "Value": 0.457,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:v%2Fv:",
                },
                "InitialOilSaturation": {
                    "Value": 0.98,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:v%2Fv:",
                },
                "SpontaneousImbibedBrineVolume": {
                    "Value": 6,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:cm3:",
                },
                "DisplacedOilVolume": {
                    "Value": 0.7768,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:cm3:",
                },
                "BrineImbibitionBrineSaturation": {
                    "Value": 7,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:v%2Fv:",
                },
                "BrineDisplacementOilSaturation": {
                    "Value": 0.36,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:v%2Fv:",
                },
                "SpontaneousImbibedOilVolume": {
                    "Value": 0.7768,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:cm3:",
                },
                "OilImbibitionBrineSaturation": {
                    "Value": 3.98,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:v%2Fv:",
                },
                "DisplacedBrineVolume": {
                    "Value": 0.24234,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:cm3:",
                },
                "DisplacementRatio": {
                    "Value": 5,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:cm3%2Fcm3:",
                },
                "OilImbibitionOilSaturation": {
                    "Value": 8.1,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:v%2Fv:",
                },
                "WettabilityIndex": [
                    {
                        "Value": 4.67,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:v%2Fv:",
                        "WettabilityIndexType": "opendes:reference-data--WettabilityIndexType:AmottWater:",
                    },
                    {
                        "Value": 3.2,
                        "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:v%2Fv:",
                        "WettabilityIndexType": "opendes:reference-data--WettabilityIndexType:AmottOil:",
                    },
                ],
                "ConfiningPressure": {
                    "Value": 0.453,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:psi:",
                },
                "DesaturationMethod": "opendes:reference-data--DesaturationMethod:CentrifugeOilWater:",
                "DisplacingFluid": "opendes:reference-data--DisplacingFluidType:Decane:",
                "DisplacedFluid": "opendes:reference-data--DisplacedFluidType:Carnation:",
                "FluidSystem": "opendes:reference-data--FluidSystemType:GasOil:",
                "InitialWaterSaturation": {
                    "Value": 32,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:ppk:",
                },
                "InitialCapillaryPressure": {
                    "Value": 65,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:bar:",
                },
                "ForcedWaterImbibition": {
                    "Value": 12,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:v%2Fv:",
                },
                "ForcedOilImbibition": {
                    "Value": 5.9,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:v%2Fv:",
                },
            },
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
INCORRECT_DATAFRAME_TEST_DATA["data"][0].pop()  # deleting WettabilityIndexData in index row 0
EXPECTED_ERROR_REASON = "Data error: 3 columns passed, passed data had 2 columns"
