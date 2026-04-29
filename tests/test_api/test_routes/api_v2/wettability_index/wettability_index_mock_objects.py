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
TEST_DDMS_URN_WITH_VERSION = (
    f"urn://rafs-v2/wettabilityindexdata/{TEST_SAMPLESANALYSIS_ID}/{TEST_DATASET_RECORD_ID}/{TEST_SCHEMA_VERSION}"
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
            "partition:work-product-component--SamplesAnalysis:samplesanalysis_test:",
            "opendes:master-data--Sample:WettabilityIndex_Sample:",
            {
                "BrineDisplacementOilSaturation": 10.0,
                "BrineImbibitionBrineSaturation": 1.0,
                "CapillaryPressureAnalysisID": "opendes:work-product-component--SamplesAnalysis:CapillaryPressure_WPC:",
                "ConfiningPressure": 9.0,
                "DesaturationMethod": "opendes:reference-data--DesaturationMethod:AmottOil:",
                "DisplacedBrineVolume": 4.0,
                "DisplacedFluidID": "opendes:reference-data--DisplacedFluidType:Brine:",
                "DisplacedOilVolume": 2.0,
                "DisplacementRatio": 5.0,
                "FluidSystem": "opendes:reference-data--FluidSystemAnalysisType:Gas:",
                "ForcedImbibedBrineVolume": 6.0,
                "ForcedImbibedOilVolume": 10.0,
                "ForcedOilImbibition": 3.0,
                "ForcedWaterImbibition": 9.0,
                "InitialBrineSaturation": 5.0,
                "InitialCapillaryPressure": 8.0,
                "InitialOilSaturation": 9.0,
                "InitialWaterSaturation": 7.0,
                "InjectionFluidID": "opendes:reference-data--SampleInjectionFluidType:GasUnspecified:",
                "OilImbibitionBrineSaturation": 6.0,
                "OilImbibitionOilSaturation": 9.0,
                "Remarks": [
                    {
                        "Remark": "ABCDEFGHIJKLMNOPQRSTUVW",
                        "RemarkDate": "2024-10-10",
                        "RemarkSequenceNumber": 6.0,
                        "RemarkSource": "ABCDEFGHIJKLMNOPQRSTUVWXY",
                    },
                ],
                "SpontaneousImbibedBrineVolume": 4.0,
                "SpontaneousImbibedOilVolume": 7.0,
                "Temperature": 8.0,
                "WettabilityIndex": [
                    {
                        "Value": 9.0,
                        "WettabilityIndexTypeID": "opendes:reference-data--WettabilityIndexType:AmottWater:",
                    },
                    {
                        "Value": 9.0,
                        "WettabilityIndexTypeID": "opendes:reference-data--WettabilityIndexType:AmottWater:",
                    },
                    {
                        "Value": 9.0,
                        "WettabilityIndexTypeID": "opendes:reference-data--WettabilityIndexType:AmottWater:",
                    },
                ],
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
            "partition:work-product-component--SamplesAnalysis:samplesanalysis_test:",
            "opendes:master-data--:1:",  # Incorrect master-data value
        ],
    ],
}

INCORRECT_DATAFRAME_TEST_DATA = copy.deepcopy(TEST_DATA)
INCORRECT_DATAFRAME_TEST_DATA["data"][0].pop()  # deleting WettabilityIndexData in index row 0
EXPECTED_ERROR_REASON = "Data error: 4 columns passed, passed data had 3 columns"
