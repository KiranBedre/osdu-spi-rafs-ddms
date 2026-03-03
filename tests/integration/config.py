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

from pathlib import Path

CONFIG = {}

SCHEMA_VERSION = "1.0.0"
PARQUET_HEADERS = {"Content-Type": "application/x-parquet"}
ACCEPT_HEADERS = "*/*;version={version}"

DATA_DIR = Path("tests", "integration", "data")
TEST_DATA_STORE = {}


class DataFiles:
    # v2
    OSDU_GENERIC_RECORD = "v2/osdu_generic_record.json"
    SAMPLE = "v2/sample.json"
    SAMPLE_ANALYSIS = "v2/samplesanalysis.json"
    SAR_V2 = "v2/sar.json"
    NMR_DATA = "v2/NMR/nmr_data.json"
    SATURATION_FUNCTION_SET = "v2/saturation_function_set/sfs.json"
    SATURATION_FUNCTION_SET_DATA = "v2/saturation_function_set/sfs_data.json"
    SATURATION_FUNCTION_SET_DATA_RECORDS_FORMAT = "v2/saturation_function_set/sfs_data_records_format.json"
    SATURATION_FUNCTION_SET_SCHEMA = "v2/saturation_function_set/sfs_schema.json"


class DataTemplates:
    ID_DATASET = "{partition}:dataset--File.Generic:"
    ID_SAR = "{partition}:work-product-component--SamplesAnalysesReport:"
    ID_SAMPLE_ANALYSIS = "{partition}:work-product-component--SamplesAnalysis:"
    ID_SATURATION_FUNCTION_SET = "{partition}:work-product-component--SaturationFunctionSet:"


class DataTypes:
    """Values have to be equal to client/api/__init__.py keys for a specific
    data type client api."""
    # v2
    MASTER_DATA = "masterdata"
    SAMPLE_ANALYSIS = "sample_analysis"
    SAR_V2 = "sar_v2"
    SAMPLE = "sample"
    SATURATION_FUNCTION_SET = "saturation_function_set"


class SamplesAnalysisTypes:  # Custom values
    NMR = "nmr"


class DatasetPrefix:
    # v2
    NMR = "nmr"


class Endpoints:

    ALL_ENDPOINTS_ARGS = [
        ("post_record", ()),
        ("get_record", ("record_id",)),
        ("get_record_versions", ("record_id",)),
        ("get_record_version", ("record_id", "version")),
        ("post_data", ("record_id",)),
        ("get_data", ("record_id", "dataset_id")),
        ("get_schema", ()),
        ("search_records", ()),
        ("search_data", ()),
        ("soft_delete_record", ("record_id",)),
    ]

    RECORD_ID_ENDPOINTS = [
        "get_record",
        "get_record_versions",
        "get_record_version",
        "soft_delete_record",
        "post_data",
        "get_data",
    ]

    ENDPOINTS_WITH_FILTERS = [
        "get_data",
        "search_records",
        "search_data",
    ]

    ORIENT_ENDPOINTS = [
        "get_data",
        "search_data",
    ]

    SEARCH_ENDPOINTS = [
        "search_records",
        "search_data",
    ]

    CONTENT_TYPE_ENDPOINTS = [
        "post_record",
        "post_data",
        "get_data",
    ]

    ACCEPT_ENDPOINTS = [
        "post_data",
        "get_data",
        "get_schema",
        "search_records",
        "search_data",
    ]

    RECORD_ID_ENDPOINTS_ARGS = []
    ENDPOINTS_WITH_FILTERS_ARGS = []
    ORIENT_ENDPOINTS_ARGS = []
    CONTENT_TYPE_ENDPOINTS_ARGS = []
    ACCEPT_ENDPOINTS_ARGS = []

    _MAPPING = [
        (RECORD_ID_ENDPOINTS_ARGS, RECORD_ID_ENDPOINTS),
        (ENDPOINTS_WITH_FILTERS_ARGS, ENDPOINTS_WITH_FILTERS),
        (ORIENT_ENDPOINTS_ARGS, ORIENT_ENDPOINTS),
        (CONTENT_TYPE_ENDPOINTS_ARGS, CONTENT_TYPE_ENDPOINTS),
        (ACCEPT_ENDPOINTS_ARGS, ACCEPT_ENDPOINTS),
    ]

    for item in ALL_ENDPOINTS_ARGS:
        endpoint_name = item[0]
        for target_list, source_set in _MAPPING:
            if endpoint_name in source_set:
                target_list.append(item)

