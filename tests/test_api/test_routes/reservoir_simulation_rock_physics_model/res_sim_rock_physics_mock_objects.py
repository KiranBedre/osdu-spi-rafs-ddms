#  Copyright 2025 ExxonMobil Technology and Engineering Company
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

from app.resources.paths import RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR
from tests.test_api.test_routes.osdu.storage_mock_objects import (
    OSDU_GENERIC_RECORD,
    TEST_RESERVOIR_SIMULATION_ROCK_PHYSICS_ID,
    BulkDatasetIdV2,
)

dir_path = os.path.dirname(os.path.abspath(__file__))


TEST_DATASET_RECORD_ID = BulkDatasetIdV2.RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL
TEST_DDMS_URN = f"urn://rafs-v2/{RESERVOIR_SIMULATION_ROCK_PHYSICS_MODEL_STR}data/{TEST_RESERVOIR_SIMULATION_ROCK_PHYSICS_ID}/{TEST_DATASET_RECORD_ID}"
TEST_SCHEMA_VERSION = "1.0.0"
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
    "columns_aggregation": "ReservoirSimulationRockPhysicsID,count",
}
TEST_PARAMS_FILTERS = {
    "columns_filter": "ReservoirSimulationRockPhysicsID,ThermalModelDefinition",
    "rows_filter": "ReservoirSimulationRockPhysicsID,eq,partition:work-product-component--ReservoirSimulationRockPhysicsModel:reservoirsimulationrockphysics_test_id:",  # matches row 0 only
}

with open(f"{dir_path}/reservoir_simulation_rock_physics_model_orient_split.json") as fp:
    TEST_DATA = json.load(fp)
    TRIMMED_TEST_DATA = {  # data used for x-parquet ingestion, only one type per request
        "columns": TEST_DATA["columns"],
        "index": [0],
        "data": [TEST_DATA["data"][0]],
    }

TEST_AGGREGATED_DATA = {
    "columns": [
        "ReservoirSimulationRockPhysicsID",
    ],
    "index": [
        "count",
    ],
    "data": [
        [
            3,
        ],
    ],
}

TEST_FILTERED_DATA = {
    "columns": [
        "ReservoirSimulationRockPhysicsID",
        "ThermalModelDefinition",
    ],
    "index": [
        0,
        1,
        2,
    ],
    "data": [
        [
            "partition:work-product-component--ReservoirSimulationRockPhysicsModel:reservoirsimulationrockphysics_test_id:",
            {
                "ThermalConductivity": 2.5,
                "HeatCapacity": 900,
            },
        ],
        [
            "partition:work-product-component--ReservoirSimulationRockPhysicsModel:reservoirsimulationrockphysics_test_id:",
            {
                "ThermalConductivity": 2.8,
                "HeatCapacity": 950,
            },
        ],
        [
            "partition:work-product-component--ReservoirSimulationRockPhysicsModel:reservoirsimulationrockphysics_test_id:",
            {
                "ThermalConductivity": 3,
                "HeatCapacity": 1000,
            },
        ],
    ],
}

INCORRECT_SCHEMA_TEST_DATA = {
    "columns": [
        "WrongField",  # Wrong field
        "data",
        # Missing mandatory field
    ],
    "index": [0],
    "data": [
        [
            "incorrect-data",
            "opendes:master-data--:1:",  # Incorrect master-data value
        ],
    ],
}

INCORRECT_DATAFRAME_TEST_DATA = copy.deepcopy(TRIMMED_TEST_DATA)
INCORRECT_DATAFRAME_TEST_DATA["data"][0].pop()  # deleting
TEST_DATA_COLUMNS = len(TRIMMED_TEST_DATA["data"][0])
EXPECTED_ERROR_REASON = (
    f"Data error: {TEST_DATA_COLUMNS} columns passed, passed data had {TEST_DATA_COLUMNS - 1} columns"
)
