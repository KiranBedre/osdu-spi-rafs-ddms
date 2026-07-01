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
from typing import Optional

import pytest
from loguru import logger

from tests.integration.config import (
    CONFIG,
    TEST_DATA_STORE,
    DataFiles,
    DataTemplates,
    DataTypes,
    SamplesAnalysisTypes,
)
from tests.integration.helpers.parallel_execution import begin_cross_worker_session, end_cross_worker_session


@pytest.fixture(scope="session", autouse=True)
def create_legal_tag(api, tmp_path_factory):
    """Create a legal tag once across all xdist workers."""
    shared_dir = tmp_path_factory.getbasetemp().parent

    state = begin_cross_worker_session(
        shared_dir,
        name="create_legal_tag",
        setup=lambda: {"legal_tag": api.legal.create_tag()},
    )
    TEST_DATA_STORE["legal_tag"] = state["legal_tag"]

    yield state["legal_tag"]

    end_cross_worker_session(
        shared_dir,
        name="create_legal_tag",
        state=state,
        teardown=lambda s: api.legal.delete_tag(s["legal_tag"]),
    )


@pytest.fixture(scope="session", autouse=True)
def create_referenced_records(api, helper, tests_data, tmp_path_factory, create_legal_tag):
    """Fixture to create referenced records and delete them after a test."""
    partition = CONFIG["DATA_PARTITION"]

    records_with_references = [
        copy.deepcopy(tests_data(DataFiles.SAMPLE)),
        copy.deepcopy(tests_data(DataFiles.SAMPLE_ANALYSIS)),
        copy.deepcopy(tests_data(DataFiles.SAR)),
        copy.deepcopy(tests_data(DataFiles.CAPILLARY_PRESSURE_DATA_V1_1)),
        copy.deepcopy(tests_data(DataFiles.COMPOSITIONAL_ANALYSIS_DATA_V1_1)),
        copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1)),
        copy.deepcopy(tests_data(DataFiles.SLIM_TUBE_DATA_V2)),
        copy.deepcopy(tests_data(DataFiles.PROPPANT_EMBEDMENT_DATA_V1)),
        copy.deepcopy(tests_data(DataFiles.ROLLER_OVEN_TEST_DATA_V1)),
        copy.deepcopy(tests_data(DataFiles.STOCK_TANK_OIL_DATA_V1_1)),
        copy.deepcopy(tests_data(DataFiles.VLE_DATA_V2)),
        copy.deepcopy(tests_data(DataFiles.XRD_DATA_V1_1)),
        copy.deepcopy(tests_data(DataFiles.XRF_DATA_V1_1)),
        copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS)),
        copy.deepcopy(tests_data(DataFiles.FLUID_MODEL)),
        copy.deepcopy(tests_data(DataFiles.DEPTH_SHIFT)),
    ]

    storage_dependencies = set()
    for record in records_with_references:
        if "id" in record:
            del record["id"]
        storage_dependencies.update(helper.find_ids_from_string(json.dumps(record)))

    record_to_create = [
        (DataTypes.SAR, DataFiles.SAR, DataTemplates.ID_SAR.format(partition=partition)),
    ]
    fixed_id_records = [
        DataFiles.SAMPLE,
    ]

    shared_dir = tmp_path_factory.getbasetemp().parent

    state = begin_cross_worker_session(
        shared_dir,
        name="create_referenced_records",
        setup=lambda: helper.create_reference_records(
            api, helper, tests_data, partition, storage_dependencies, record_to_create, fixed_id_records
        ),
    )
    TEST_DATA_STORE.update(state)

    yield

    end_cross_worker_session(
        shared_dir,
        name="create_referenced_records",
        state=state,
        teardown=lambda s: helper.purge_reference_records(
            api, state, storage_dependencies, record_to_create,
        ),
    )


@pytest.fixture(scope="package")
def create_record(api, helper, tests_data):
    """Fixture to create any record with a random unique id and delete it after
    test."""
    record_data = {}
    _api_path = ""
    _to_delete = bool

    def _create_record(
        api_path: DataTypes,
        file_name: str,
        id_template: str,
        analysis_type: Optional[SamplesAnalysisTypes] = None,
        datasets: list = None,
    ) -> [dict | dict]:
        """
        :param api_path: example - DataTypes.RS, DataTypes.CORING, DataTypes.RSA, DataTypes.PVT
        :param file_name: see tests/integration/config.py
        :param id_template: example - ID_RSA_TEMPLATE
        :param analysis_type: example - SamplesAnalysisTypes.RCA
        :param datasets: list of raw data files that can be downloaded
        :return: created record data
        """
        nonlocal record_data, _api_path, _to_delete
        _api_path = api_path
        record_data = copy.deepcopy(tests_data(file_name, analysis_type))
        record_data["id"] = f"{id_template}{helper.generate_random_record_id()}"

        if datasets:
            record_data["data"]["Datasets"] = datasets

        logger.info(f"Creating a record with ID {record_data['id']}")
        created_record = getattr(api, _api_path).post_record([record_data])
        while True:
            logger.info("Check until record is created and registered")
            try:
                getattr(api, _api_path).get_record(record_data["id"])
            except AssertionError:
                logger.info(f"Record {record_data['id']} hasn't been created yet")
            else:
                break
        return record_data, created_record

    yield _create_record

    if record_data.get("id"):
        api.storage.purge_record(record_data["id"])


@pytest.fixture
def delete_record(api, helper):
    """Fixture to delete any record with id after test."""
    container = {"record_id": [], "api_path": ""}

    yield container

    for record_id in container["record_id"]:
        api.storage.purge_record(record_id)


@pytest.fixture(scope="session")
def data_partition_id():
    """Return the data partition ID from the session configuration."""
    return CONFIG["DATA_PARTITION"]
