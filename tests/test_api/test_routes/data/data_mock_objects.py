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
from typing import List, Optional

import numpy
import pandas as pd

from app.api.routes.utils.query import find_osdu_ids_from_string
from tests.test_api.test_routes.osdu.storage_mock_objects import (
    OSDU_GENERIC_RECORD,
)

TEST_SERVER = "http://testserver"
TEST_DATASET_RECORD_ID = "opendes:dataset--File.Generic:routine-core-analysis-123:1234"
TEST_SCHEMA_VERSION = "1.0.0"
TEST_DDMS_URN = f"urn://rafs-v1/routinecoreanalysisdata/partition:work-product-component--RockSampleAnalysis:rocksampleanalysis_test/{TEST_DATASET_RECORD_ID}"
TEST_DDMS_URN_WITH_VERSION = f"urn://rafs-v1/routinecoreanalysisdata/partition:work-product-component--RockSampleAnalysis:rocksampleanalysis_test/{TEST_DATASET_RECORD_ID}/{TEST_SCHEMA_VERSION}"
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

TEST_HEADERS_JSON = {
    "content-type": "application/json",
    "data-partition-id": "opendes",
    "Authorization": "Bearer token",
    "Accept": f"*/*;version={TEST_SCHEMA_VERSION}",
}
TEST_HEADERS_WITHOUT_SCHEMA_VERSION = {
    "content-type": "application/json",
    "data-partition-id": "opendes",
    "Authorization": "Bearer token",
    "Accept": f"*/*",
}
TEST_HEADERS_IMPROPER_SCHEMA_VERSION = {
    "content-type": "application/json",
    "data-partition-id": "opendes",
    "Authorization": "Bearer token",
    "Accept": f"*/*; version=a.a.a",
}
TEST_HEADERS_PARQUET = {
    "content-type": "application/x-parquet",
    "data-partition-id": "opendes",
    "Authorization": "Bearer token",
    "Accept": f"*/*;version={TEST_SCHEMA_VERSION}",
}
TEST_HEADERS_NO_AUTH = {
    "data-partition-id": "opendes",
    "content-type": "application/json",
    "Accept": f"*/*;version={TEST_SCHEMA_VERSION}",
}
TEST_PARAMS_AGGREGATION = {
    "columns_aggregation": "Remarks,count",
}
TEST_PARAMS_FILTERS = {
    "columns_filter": "RockSampleID,CoringID,WellboreID",
    "rows_filter": "RockSampleID,eq,opendes:master-data--RockSample:1:",
}

TEST_DATA = {
    "columns": [
        "RockSampleID",
        "CoringID",
        "WellboreID",
        "SampleNumber",
        "SampleDepth",
        "Permeability",
        "Porosity",
        "GrainDensity",
        "Saturation",
        "LithologyDescription",
        "Remarks",
    ],
    "index": [0],
    "data": [
        [
            "opendes:master-data--RockSample:1:",
            "opendes:master-data--Coring:1:",
            "opendes:master-data--Wellbore:1:",
            "SampleNumber",
            {
                "Value": 1.0,
                "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:1:",
            },
            [
                {
                    "Value": 1.0,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:1:",
                },
            ],
            [
                {
                    "Value": 1.0,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:1:",
                },
            ],
            [
                {
                    "Value": 1.0,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:1:",
                },
            ],
            [
                {
                    "Value": 1.0,
                    "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:1:",
                },
            ],
            "LithologyDescription",
            "Remarks",
        ],
    ],
}

TEST_AGGREGATED_DATA = {
    "columns": [
        "count(\"Remarks\")",
    ],
    "index": [
        0,
    ],
    "data": [
        [
            1,
        ],
    ],
}

TEST_FILTERED_DATA = {
    "columns": [
        "RockSampleID",
        "CoringID",
        "WellboreID",
    ],
    "index": [
        0,
    ],
    "data": [
        [
            "opendes:master-data--RockSample:1:",
            "opendes:master-data--Coring:1:",
            "opendes:master-data--Wellbore:1:",
        ],
    ],
}

INCORRECT_SCHEMA_TEST_DATA = {
    "columns": [
        "WrongField",  # Wrong field
        # "RockSampleID",  # Missing mandatory field
        "CoringID",
        "WellboreID",
        "SampleNumber",
        "SampleType",
        "SampleDepth",
        "Remarks",
    ],
    "index": [0],
    "data": [
        [
            "opendes:master-data--RockSample:1:",
            "opendes:master-data--:1:",  # Incorrect Coring value
            "opendes:master-data--Wellbore:1:",
            "SampleNumber",
            "opendes:reference-data--RockSampleType:1:",
            {
                "Value": "number required",  # String in place of float value
                "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:1:",
            },
            "Remarks",
        ],
    ],
}

INCORRECT_DATAFRAME_TEST_DATA = {
    "columns": [
        "RockSampleID",
        "CoringID",
        "WellboreID",
        "SampleNumber",
        "SampleDepth",
    ],
    "index": [0],
    "data": [
        [
            "opendes:master-data--RockSample:1:",
            "opendes:master-data--Coring:1:",
            "opendes:master-data--Wellbore:1:",
            "SampleNumber",
            "opendes:reference-data--RockSampleType:1:",
            {
                "Value": 1.0,
                "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:1:",
            },
        ],
    ],
}
EXPECTED_ERROR_REASON = "Data error: 5 columns passed, passed data had 6 columns"

INTEGRITY_ERROR_DATAFRAME_DATA = {
    "columns": [
        "RockSampleID",
        "CoringID",
        "WellboreID",
        "SampleNumber",
        "SampleType",
        "SampleDepth",
    ],
    "index": [0],
    "data": [
        [
            "opendes:master-data--RockSample:does_not_exist:",
            "opendes:master-data--Coring:1:",
            "opendes:master-data--Wellbore:1:",
            "SampleNumber",
            "opendes:reference-data--RockSampleType:1:",
            {
                "Value": 1.0,
                "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:1:",
            },
        ],
    ],
}

TEST_WRONG_COLUMNS_FILTERS = [
    {"columns_filter": "unvalid_column_1,unvalid_column_2"},
    {"columns_filter": "SampleNumber,"},
]
TEST_WRONG_ROWS_FILTERS = [
    {"rows_filter": "wrong_syntax"},
    {"rows_filter": "unvalid_column,gt,0"},
    {"rows_filter": "RockSampleID,wrong_operator,test_id"},
    {"rows_filter": "RockSampleID,eq,wrong_pattern"},
]
TEST_WRONG_AGGREGATION = [
    {"columns_aggregation": "wrong_syntax"},
    {"columns_aggregation": "unvalid_column,avg"},
    {"columns_aggregation": "RockSampleID,wrong_operator"},
]

TEST_WRONG_COLUMNS_FILTERS_REASONS = [
    r"^Invalid columns: {'unvalid_column_[1-2]', 'unvalid_column_[1-2]'}. Select one of {.+}$",
    r"^Invalid columns: {''}. Select one of .+$",
]
TEST_WRONG_ROWS_FILTERS_REASONS = [
    r"^Bad rows_filter expression. Correct form 'ColumnName\[\.FieldName\],operator,value'$",
    r"^For filter column select one of {.+}$",
    r"^Invalid comparison operator not in: .+$",
    r"^(.*[\n]*)+ wrong_pattern$",
]
TEST_WRONG_AGGREGATION_REASONS = [
    r"^Bad aggregation expression. Correct form 'ColumnName\[\.FieldName\],operator'$",
    r"^For aggregation column select one of {.+}$",
    r"^Invalid aggregation operator not in: {.+}$",
]

MULTIPLE_DATASETS_STORAGE_SIDE_EFFECT = [
    {
        **OSDU_GENERIC_RECORD.dict(exclude_none=True),
        **{"data": {"Datasets": ["partition:entity-type:d1:", "partition:entity-type:d2:"]}},
    },
    {
        **OSDU_GENERIC_RECORD.dict(exclude_none=True),
        **{"data": {"EncodingFormatTypeID": "partition:entity-type:application/pdf:"}},
    },
    {
        **OSDU_GENERIC_RECORD.dict(exclude_none=True),
        **{"data": {"EncodingFormatTypeID": "partition:entity-type:application/xlsx:"}},
    },
]
SINGLE_DATASET_STORAGE_SIDE_EFFECT = [
    {
        **OSDU_GENERIC_RECORD.dict(exclude_none=True),
        **{"data": {"Datasets": ["partition:entity-type:d1:"]}},
    },
    {
        **OSDU_GENERIC_RECORD.dict(exclude_none=True),
        **{"data": {"EncodingFormatTypeID": "partition:entity-type:application/pdf:"}},
    },
]
NO_DATASETS_STORAGE_SIDE_EFFECT = [
    {
        **OSDU_GENERIC_RECORD.dict(exclude_none=True),
        **{"data": {"Datasets": []}},
    },
]

MULTIPLE_DATASETS_DATASET_SIDE_EFFECT = [b"pdf_content", b"xlsx_content"]
SINGLE_DATASET_DATASET_SIDE_EFFECT = [b"pdf_content"]
NO_DATASETS_DATASET_SIDE_EFFECT = []


def build_get_test_data(mime_type: str, test_data: dict = TEST_DATA):
    if mime_type == "x-parquet":
        dataframe = pd.DataFrame(test_data["data"], columns=test_data["columns"])
        return dataframe.to_parquet()
    elif mime_type == "json":
        return json.dumps(test_data)


class DatasetServiceMock:
    def __init__(self, test_dataset_record_id: str, mime_type: str, test_data: dict) -> None:
        self.mime_type = mime_type
        self.schema_authority = "osdu"
        self.test_dataset_record_id = test_dataset_record_id
        self.test_data = test_data

    async def download_file(self, file_id: str):
        return build_get_test_data(self.mime_type, self.test_data)

    async def upload_file(
            self,
            blob_file: bytes,
            dataset_id: Optional[str] = None,
            parent_record: Optional[dict] = None,
    ):
        return self.test_dataset_record_id


SEARCH_RESPONSE = {
    "results": [
        {"id": "opendes:master-data--Coring:1"},
        {"id": "opendes:reference-data--UnitOfMeasure:1"},
        {"id": "opendes:reference-data--RockSampleType:1"},
        {"id": "opendes:master-data--RockSample:1"},
        {"id": "opendes:reference-data--PermeabilityMeasurementType:1"},
        {"id": "opendes:reference-data--PorosityMeasurementType:1"},
        {"id": "opendes:reference-data--GrainDensityMeasurementType:1"},
        {"id": "opendes:master-data--Wellbore:1"},
        {"id": "opendes:reference-data--SaturationMethodType:1"},
    ],
    "aggregations": [],
    "totalCount": 9,
}

QUERY_RECORDS_RESPONSE = {
    "records": [],
    "invalidRecords": ["partition:entity-type:entity-id"],
    "retryRecords": [],
}


class SearchService:
    def __init__(self, search_response=SEARCH_RESPONSE):
        self.search_response = search_response

    async def find_records(self, kind: str = "*:*:*:*", query: str = "*", limit: str = None) -> dict:
        return self.search_response


class StorageService:
    def __init__(self, record_data: dict, query_records_response=None):
        self.record_data = record_data
        self.query_records_response = query_records_response

    async def get_record(self, record_id: str, version: Optional[str] = None) -> Optional[dict]:
        return self.record_data

    async def upsert_records(self, records: List[dict]) -> Optional[dict]:
        return self.record_data

    async def query_records(self, records_list: List[str]) -> Optional[dict]:
        return self.query_records_response


def build_mock_get_dataset_service(
    test_dataset_record_id: str,
    mime_type: str = "x-parquet",
    test_data: dict = TEST_DATA,
):
    async def mock_get_dataset_service():
        return DatasetServiceMock(test_dataset_record_id, mime_type, test_data)

    return mock_get_dataset_service


def build_mock_get_storage_service(record_data: dict, data_payload=None):
    data_string = None
    if isinstance(data_payload, pd.DataFrame):
        data_string = data_payload.to_string()
    elif isinstance(data_payload, dict):
        data_string = json.dumps(data_payload)

    query_records_response = copy.deepcopy(QUERY_RECORDS_RESPONSE)
    if data_string:
        ids_to_check = find_osdu_ids_from_string(data_string)
        query_records_response["results"] = [{"id": id_} for id_ in ids_to_check]
        query_records_response["invalidRecords"] = []

    async def mock_get_storage_service():
        return StorageService(record_data, query_records_response)

    return mock_get_storage_service


INVALID_DATA_WITH_NAN = {
    "columns": [
        "bad_column",
    ],
    "index": [
        0,
    ],
    "data": [
        [numpy.NaN],
    ],
}

INVALID_DATA_EMPTY = {
    "columns": [
    ],
    "index": [
    ],
    "data": [
    ],
}

INVALID_DATA_INCONSISTENT = {
    "columns": [
        "some_column",
    ],
    "index": [
        0,
        1,
    ],
    "data": [
        [
            "column_value",
        ],
    ],
}

ORIENT_SPLIT_400_PAYLOADS = [{}, [{}], INVALID_DATA_INCONSISTENT, INVALID_DATA_EMPTY]
