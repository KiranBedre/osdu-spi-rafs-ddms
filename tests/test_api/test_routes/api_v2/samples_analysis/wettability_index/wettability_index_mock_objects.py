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

TEST_DATASET_RECORD_ID = SamplesAnalysisDatasetIDsV2.WETTABILITY_INDEX
TEST_DDMS_URN = SamplesAnalysisDDDMSURNsV2.WETTABILITY_INDEX
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
    "columns_filter": "SamplesAnalysisID,SampleID,WettabilityIndexData",
    "rows_filter": f"SampleID,eq,{TEST_SAMPLE_ID}",
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
            TEST_SAMPLES_ANALYSIS_ID,
            TEST_SAMPLE_ID,
            {
                "BrineDisplacementOilSaturation": 10.0,
                "BrineImbibitionBrineSaturation": 1.0,
                "CapillaryPressureAnalysisID": "partition:work-product-component--SamplesAnalysis:samples_analysis_test_id:",
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
    "index": [
        0,
    ],
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


# V2.0.0 mock objects
TEST_SCHEMA_VERSION_V2 = ContentSchemaVersion.V_2_0_0
TEST_DDMS_URN_WITH_VERSION_V2 = f"{TEST_DDMS_URN}/{TEST_SCHEMA_VERSION_V2}"
RECORD_DATA_WITH_SCHEMA_VERSION_V2 = {
    **OSDU_GENERIC_RECORD.model_dump(exclude_none=True),
    **{
        "data": {
            "SampleIDs": [TEST_SAMPLE_ID],
            "DDMSDatasets": [TEST_DDMS_URN_WITH_VERSION_V2],
        },
    },
}
TEST_PARAMS_AGGREGATION_V2 = {
    "columns_aggregation": "SampleID,count",
}
TEST_PARAMS_FILTERS_V2 = {
    "columns_filter": "SamplesAnalysisID,SampleID,Temperature",
    "rows_filter": f"SampleID,eq,{TEST_SAMPLE_ID}",
}

with open(f"{dir_path}/wettability_index_orient_split_2.0.0.json") as fp:
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
        "Temperature",
    ],
    "index": [
        0,
    ],
    "data": [
        [
            TEST_SAMPLES_ANALYSIS_ID,
            TEST_SAMPLE_ID,
            185.0,
        ],
    ],
}

INCORRECT_DATAFRAME_TEST_DATA_V2 = copy.deepcopy(TEST_DATA_V2)
INCORRECT_DATAFRAME_TEST_DATA_V2["data"][0].pop()
EXPECTED_ERROR_REASON_V2 = (
    f"Data error: {len(INCORRECT_DATAFRAME_TEST_DATA_V2['columns'])} columns passed, "
    f"passed data had {len(INCORRECT_DATAFRAME_TEST_DATA_V2['data'][0])} columns"
)
