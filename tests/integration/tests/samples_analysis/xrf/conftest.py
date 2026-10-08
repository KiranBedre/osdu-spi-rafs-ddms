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

import pytest

from tests.integration.config import (
    SamplesAnalysisTypes,
    SchemaVersions,
)


@pytest.fixture(scope="package")
def analysis_type():
    """Analysis type definition"""
    return SamplesAnalysisTypes.XRF


@pytest.fixture
def row_pagination_case_v1_1(
    create_isolated_samples_analysis_pagination_case,
):
    """Create two isolated XRF datasets with three identifiable rows each."""

    def _prepare_data(data_payload):
        mass_balance_index = data_payload["columns"].index("MassBalance")
        source_row = data_payload["data"][0]
        data_payload["data"] = []
        data_payload["index"] = [0, 1, 2]
        for mass_balance in (10.0, 20.0, 30.0):
            row = copy.deepcopy(source_row)
            row[mass_balance_index] = mass_balance
            data_payload["data"].append(row)

    return create_isolated_samples_analysis_pagination_case(
        SamplesAnalysisTypes.XRF,
        SchemaVersions.V1_1_0,
        prepare_data=_prepare_data,
    )
