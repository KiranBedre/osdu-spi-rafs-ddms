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
import time

import pytest

from tests.integration.config import (
    CONFIG,
    DataFiles,
    DataTemplates,
    DataTypes,
    FluidModelTypes,
    SchemaVersions,
)

RECORD_AVAILABILITY_MAX_ATTEMPTS = 5
RECORD_AVAILABILITY_RETRY_INTERVAL = 5


def _create_compositional_fluid_model(api, helper, tests_data):
    """Create a Compositional FluidModel record."""
    record_data = copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))
    record_data["id"] = (
        f"{DataTemplates.ID_FLUID_MODEL.format(partition=CONFIG['DATA_PARTITION'])}"
        f"{helper.generate_random_record_id()}"
    )
    record_data["data"][
        "FluidModelTypeID"
    ] = f"{CONFIG['DATA_PARTITION']}:reference-data--FluidModelType:Compositional:"

    api.fluid_model.post_record([record_data])
    for attempt in range(RECORD_AVAILABILITY_MAX_ATTEMPTS):
        try:
            api.fluid_model.get_record(record_data["id"])
        except AssertionError:
            if attempt < RECORD_AVAILABILITY_MAX_ATTEMPTS - 1:
                time.sleep(RECORD_AVAILABILITY_RETRY_INTERVAL)
        else:
            break
    else:
        raise AssertionError(
            f"Compositional FluidModel record '{record_data['id']}' did not become available "
            f"after {RECORD_AVAILABILITY_MAX_ATTEMPTS} attempts."
        )
    return record_data


@pytest.fixture(scope="package")
def fluid_model_type():
    """Return Compositional FluidModel content type."""
    return FluidModelTypes.COMPOSITIONAL_FLUID_MODEL


@pytest.fixture(scope="module")
def fluid_create_record(api, helper, tests_data):
    """Create a Compositional FluidModel record."""
    record_data = _create_compositional_fluid_model(api, helper, tests_data)
    yield record_data
    api.storage.purge_record(record_data["id"])


@pytest.fixture(scope="function")
def fluid_create_fresh_record(api, helper, tests_data):
    """Create a fresh Compositional FluidModel record."""
    record_data = _create_compositional_fluid_model(api, helper, tests_data)
    yield record_data
    api.storage.purge_record(record_data["id"])


@pytest.fixture(scope="module")
def dataset_id(api, helper, record_id, tests_data, fluid_model_type):
    """Create a Compositional dataset and return its content_id."""
    data_payload = copy.deepcopy(
        tests_data(DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1)
    )
    data_payload["data"][0][0] = f"{record_id}:"
    post_response = api.fluid_model.post_data(
        record_id=record_id,
        body=data_payload,
        fluid_model_type=fluid_model_type,
        schema_version=SchemaVersions.V1_0_0,
    )
    return helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])


@pytest.fixture
def pagination_case(create_isolated_pagination_case, fluid_model_type):
    """Create two Compositional FluidModel records isolated by a unique field."""
    return create_isolated_pagination_case(
        api_path=DataTypes.FLUID_MODEL,
        record_file=DataFiles.FLUID_MODEL,
        data_file=DataFiles.COMPOSITIONAL_FLUID_MODEL_DATA_V1,
        id_template=DataTemplates.ID_FLUID_MODEL.format(
            partition=CONFIG["DATA_PARTITION"],
        ),
        schema_version=SchemaVersions.V1_0_0,
        resource_kwargs={"fluid_model_type": fluid_model_type},
        record_data_updates={
            "FluidModelTypeID": (
                f"{CONFIG['DATA_PARTITION']}:reference-data--FluidModelType:Compositional:"
            ),
        },
        scope_kind="Field",
    )
