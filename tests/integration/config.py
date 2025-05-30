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


class DataTemplates:
    ID_DATASET = "{partition}:dataset--File.Generic:"
    ID_SAR = "{partition}:work-product-component--SamplesAnalysesReport:"
    ID_SAMPLE_ANALYSIS = "{partition}:work-product-component--SamplesAnalysis:"


class DataTypes:
    """Values have to be equal to client/api/__init__.py keys for a specific
    data type client api."""
    # v2
    MASTER_DATA = "masterdata"
    SAMPLE_ANALYSIS = "sample_analysis"
    SAR_V2 = "sar_v2"
    SAMPLE = "sample"


class SamplesAnalysisTypes:  # Custom values
    NMR = "nmr"


class DatasetPrefix:
    # v2
    NMR = "nmr"
