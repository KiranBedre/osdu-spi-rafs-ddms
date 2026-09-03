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

import pytest

from tests.integration.config import DataFiles, FluidModelTypes, SchemaVersions


@pytest.fixture(scope="package")
def fluid_model_type():
    """Return Black Oil FluidModel content type."""
    return FluidModelTypes.BLACK_OIL_FLUID_MODEL


@pytest.fixture(scope="module")
def dataset_id(api, helper, record_id, tests_data, fluid_model_type):
    """Create a Black Oil dataset and return its dataset_id."""
    data_payload = copy.deepcopy(tests_data(DataFiles.BLACK_OIL_FLUID_MODEL_DATA_V1))
    data_payload["data"][0][0] = f"{record_id}:"
    post_response = api.fluid_model.post_data(
        record_id=record_id,
        body=data_payload,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
    )
    return helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])


@pytest.fixture(scope="function")
def fresh_dataset_id(api, helper, fresh_record_id, tests_data, fluid_model_type):
    """Create a Black Oil dataset for a fresh FluidModel record and return its dataset_id."""
    data_payload = copy.deepcopy(tests_data(DataFiles.BLACK_OIL_FLUID_MODEL_DATA_V1))
    data_payload["data"][0][0] = f"{fresh_record_id}:"
    post_response = api.fluid_model.post_data(
        record_id=fresh_record_id,
        body=data_payload,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
    )
    return helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])
