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


@pytest.fixture(scope="session", autouse=True)
def create_legal_tag(api):
    """Fixture to create a legal tag with a random id and delete it after a
    test."""
    legal_tag = api.legal.create_tag()
    TEST_DATA_STORE["legal_tag"] = legal_tag

    yield legal_tag

    api.legal.delete_tag(legal_tag)


@pytest.fixture(scope="session", autouse=True)
def create_referenced_records(api, helper, tests_data):
    """Fixture to create referenced records and delete them after a test."""
    partition = CONFIG["DATA_PARTITION"]

    records_with_references = [
        copy.deepcopy(tests_data(DataFiles.SAMPLE)),
        copy.deepcopy(tests_data(DataFiles.SAMPLE_ANALYSIS)),
        copy.deepcopy(tests_data(DataFiles.SAR_V2)),
        copy.deepcopy(tests_data(DataFiles.NMR_DATA)),
    ]

    storage_dependencies = set()
    for record in records_with_references:
        if "id" in record:
            del record["id"]
        storage_dependencies.update(helper.find_ids_from_string(json.dumps(record)))

    osdu_generic_record = tests_data(DataFiles.OSDU_GENERIC_RECORD)
    records_to_store = []
    for reference_id in storage_dependencies:
        if "reference-data" in reference_id:  # Don't override reference-data values
            continue
        record_to_store = copy.deepcopy(osdu_generic_record)
        record_to_store["id"] = reference_id
        record_type = reference_id.split(":")[1]
        record_to_store["kind"] = f"osdu:wks:{record_type}:1.0.0"
        records_to_store.append(record_to_store)

    response = api.storage.create_or_update_records(records_to_store)
    logger.debug(response.json())

    record_to_create = [
        (DataTypes.SAR_V2, DataFiles.SAR_V2, DataTemplates.ID_SAR.format(partition=partition)),
    ]
    for data_type, data, id_template in record_to_create:
        record_data = copy.deepcopy(tests_data(data))
        record_data["id"] = f"{id_template}{helper.generate_random_record_id()}"
        getattr(api, data_type).post_record([record_data])
        TEST_DATA_STORE[f"{data_type}_record_id"] = record_data["id"]

    yield

    for data_type, _, _ in record_to_create:
        api.storage.purge_record(TEST_DATA_STORE[f"{data_type}_record_id"])

    for reference_id in storage_dependencies:
        if "reference-data" in reference_id:  # Don't delete reference-data values
            continue
        api.storage.purge_record(reference_id)


@pytest.fixture
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
            logger.info(f"Check until record is created and registered")
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
