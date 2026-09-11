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
import uuid

import pytest

from tests.integration.config import (
    CONFIG,
    DataFiles,
    DataTemplates,
    DataTypes,
)


@pytest.fixture(scope="module")
def saturation_function_set_create_record(api, create_record):
    """Create a SaturationFunctionSet record."""
    record_data, _ = create_record(
        DataTypes.SATURATION_FUNCTION_SET,
        DataFiles.SATURATION_FUNCTION_SET,
        DataTemplates.ID_SATURATION_FUNCTION_SET.format(partition=CONFIG["DATA_PARTITION"]),
    )
    yield record_data
    api.storage.purge_record(record_data["id"])


@pytest.fixture(scope="function")
def saturation_function_set_create_fresh_record(api, create_record):
    """Create a fresh SaturationFunctionSet record per test."""
    record_data, _ = create_record(
        DataTypes.SATURATION_FUNCTION_SET,
        DataFiles.SATURATION_FUNCTION_SET,
        DataTemplates.ID_SATURATION_FUNCTION_SET.format(partition=CONFIG["DATA_PARTITION"]),
    )
    yield record_data
    api.storage.purge_record(record_data["id"])


@pytest.fixture(scope="module")
def record_id(saturation_function_set_create_record):
    """Return SaturationFunctionSet record_id."""
    return saturation_function_set_create_record["id"]


@pytest.fixture(scope="function")
def fresh_record_id(saturation_function_set_create_fresh_record):
    """Return SaturationFunctionSet record_id."""
    return saturation_function_set_create_fresh_record["id"]


@pytest.fixture(scope="module")
def version(api, record_id):
    """Return SaturationFunctionSet record's version."""
    response = api.saturation_function_set.get_record_versions(record_id)
    versions = response.get("versions", [])
    return versions[-1]


@pytest.fixture(scope="module")
def dataset_id(api, helper, record_id, tests_data):
    """Create a fresh dataset and return dataset_id."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1))
    data_payload["data"][0][0] = f"{record_id}:"
    post_response = api.saturation_function_set.post_data(record_id, data_payload)
    return helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])


@pytest.fixture(scope="function")
def fresh_dataset_id(api, helper, fresh_record_id, tests_data):
    """Create a fresh dataset and return dataset_id."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1))
    data_payload["data"][0][0] = f"{fresh_record_id}:"
    post_response = api.saturation_function_set.post_data(record_id=fresh_record_id, body=data_payload)
    return helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])


@pytest.fixture(scope="function")
def search_available(api, helper, record_id):
    """Verify if record is available in search results - workaround for issue #729."""
    params = {"rows_filter": f"SaturationFunctionSetID,eq,{record_id}:"}

    # Wait until search returns the record_id in its result set
    helper.wait_for_search_record(
        lambda: api.saturation_function_set.search_records(params=params),
        record_id,
        max_attempts=5,
    )


@pytest.fixture(scope="module")
def spec_char_record_id(data_partition_id):
    """Generate a unique record ID that includes the required special characters."""
    base_id = f"{data_partition_id}:work-product-component--SaturationFunctionSet:7%2F12-A-7%20D_"
    unique_suffix = str(uuid.uuid4().int)[:8]
    return f"{base_id}{unique_suffix}"


@pytest.fixture
def pagination_case(create_isolated_pagination_case):
    """Create two SFS records isolated by a unique field."""
    return create_isolated_pagination_case(
        api_path=DataTypes.SATURATION_FUNCTION_SET,
        record_file=DataFiles.SATURATION_FUNCTION_SET,
        data_file=DataFiles.SATURATION_FUNCTION_SET_DATA_V1,
        id_template=DataTemplates.ID_SATURATION_FUNCTION_SET.format(
            partition=CONFIG["DATA_PARTITION"],
        ),
        scope_kind="Field",
    )
