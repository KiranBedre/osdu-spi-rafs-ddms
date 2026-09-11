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

import uuid

import pytest

from tests.integration.config import (
    CONFIG,
    DataFiles,
    DataTemplates,
    DataTypes,
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
