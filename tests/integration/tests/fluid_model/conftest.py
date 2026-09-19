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
import uuid

import pytest
from loguru import logger

from tests.integration.config import (
    CONFIG,
    DataFiles,
    DataTemplates,
    DataTypes,
    SchemaVersions,
)


@pytest.fixture(scope="module")
def fluid_create_record(api, create_record):
    """Create a FluidModel record."""
    record_data, _ = create_record(
        DataTypes.FLUID_MODEL,
        DataFiles.FLUID_MODEL,
        DataTemplates.ID_FLUID_MODEL.format(partition=CONFIG["DATA_PARTITION"]),
    )
    yield record_data
    api.storage.purge_record(record_data["id"])


@pytest.fixture(scope="function")
def fluid_create_fresh_record(api, create_record):
    """Create a fresh FluidModel record."""
    record_data, _ = create_record(
        DataTypes.FLUID_MODEL,
        DataFiles.FLUID_MODEL,
        DataTemplates.ID_FLUID_MODEL.format(partition=CONFIG["DATA_PARTITION"]),
    )
    yield record_data
    api.storage.purge_record(record_data["id"])


@pytest.fixture(scope="module")
def record_id(fluid_create_record):
    """Return FluidModel record_id."""
    return fluid_create_record["id"]


@pytest.fixture(scope="function")
def fresh_record_id(fluid_create_fresh_record):
    """Return fresh FluidModel record_id."""
    return fluid_create_fresh_record["id"]


@pytest.fixture(scope="module")
def version(api, record_id):
    """Return FluidModel record's version."""
    response = api.fluid_model.get_record_versions(record_id)
    versions = response.get("versions", [])
    return versions[-1]


@pytest.fixture(scope="function")
def search_available(api, helper, record_id, dataset_id, fluid_model_type):
    """Wait until the created FluidModel record and data are available in search results."""
    params = {"rows_filter": f"FluidModelID,eq,{record_id}:"}

    # Wait until search returns the record_id in its result set
    helper.wait_for_search_record(
        lambda: api.fluid_model.search_records(
            fluid_model_type=fluid_model_type,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        ),
        record_id,
        max_attempts=5,
    )
    helper.wait_for_search_data(
        lambda: api.fluid_model.search_data(
            fluid_model_type=fluid_model_type,
            schema_version=SchemaVersions.V1_0_0,
            params=params,
        ),
        record_id,
    )


@pytest.fixture(scope="module")
def spec_char_record_id(data_partition_id):
    """Generate a unique record ID that includes the required special characters."""
    base_id = f"{data_partition_id}:work-product-component--FluidModel:7%2F12-A-7%20D_"
    unique_suffix = str(uuid.uuid4().int)[:8]
    return f"{base_id}{unique_suffix}"


@pytest.fixture(scope="module")
def x_collaboration_header():
    """Generate a unique namespace."""
    namespace = str(uuid.uuid4())
    return f"id={namespace},application=rafddms"


@pytest.fixture(scope="function")
def fluid_model_collaboration_dependencies(api, helper, tests_data, x_collaboration_header):
    """Clone FluidModel dependencies into the test collaboration namespace."""
    fluid_model = tests_data(DataFiles.FLUID_MODEL)
    dependency_ids = sorted(helper.find_ids_from_string(json.dumps(fluid_model)))
    headers = {"x-collaboration": x_collaboration_header}
    cloned_ids = []

    def _purge_cloned_records():
        cleanup_errors = []
        for record_id in reversed(cloned_ids):
            try:
                api.storage.purge_record(record_id, headers=headers)
            except Exception as exception:
                logger.exception(f"Failed to purge collaboration dependency {record_id}")
                cleanup_errors.append((record_id, exception))

        if cleanup_errors:
            details = "\n".join(f"- {record_id}: {exception}" for record_id, exception in cleanup_errors)
            raise RuntimeError(f"Failed to purge collaboration dependencies:\n{details}")

    try:
        for record_id in dependency_ids:
            record = copy.deepcopy(api.storage.get(path=f"/records/{record_id}").json())
            for field in ("version", "createTime", "createUser", "modifyTime", "modifyUser"):
                record.pop(field, None)
            api.storage.create_or_update_records([record], headers=headers)
            cloned_ids.append(record_id)
    except Exception:
        try:
            _purge_cloned_records()
        except Exception:
            logger.exception("Failed to clean up collaboration dependencies after fixture setup failure")
        raise

    try:
        yield tuple(cloned_ids)
    finally:
        _purge_cloned_records()
