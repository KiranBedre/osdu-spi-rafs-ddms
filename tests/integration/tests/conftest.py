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
import time
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
    SchemaVersions,
)
from tests.integration.helpers.parallel_execution import (
    begin_cross_worker_session,
    end_cross_worker_session,
)


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
def create_referenced_records(
    api, helper, tests_data, tmp_path_factory, create_legal_tag
):
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
        (
            DataTypes.SAR,
            DataFiles.SAR,
            DataTemplates.ID_SAR.format(partition=partition),
        ),
    ]
    fixed_id_records = [
        DataFiles.SAMPLE,
    ]
    fixed_record_ids = {
        copy.deepcopy(tests_data(data))["id"] for data in fixed_id_records
    }
    storage_dependencies.difference_update(fixed_record_ids)

    shared_dir = tmp_path_factory.getbasetemp().parent

    state = begin_cross_worker_session(
        shared_dir,
        name="create_referenced_records",
        setup=lambda: helper.create_reference_records(
            api,
            helper,
            tests_data,
            partition,
            storage_dependencies,
            record_to_create,
            fixed_id_records,
        ),
    )
    TEST_DATA_STORE.update(state)

    yield

    end_cross_worker_session(
        shared_dir,
        name="create_referenced_records",
        state=state,
        teardown=lambda s: helper.purge_reference_records(
            api,
            state,
            storage_dependencies,
            record_to_create,
        ),
    )


@pytest.fixture(scope="package")
def create_record(api, helper, tests_data):
    """Fixture to create any record with a random unique id and delete it after
    test."""
    created_record_ids = []

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
        record_data = copy.deepcopy(tests_data(file_name, analysis_type))
        record_data["id"] = f"{id_template}{helper.generate_random_record_id()}"

        if datasets:
            record_data["data"]["Datasets"] = datasets

        logger.info(f"Creating a record with ID {record_data['id']}")
        resource = getattr(api, api_path)
        created_record = resource.post_record([record_data])
        created_record_ids.append(record_data["id"])

        max_attempts = 30
        for attempt in range(max_attempts):
            logger.info(
                "Checking whether record is available "
                f"(attempt {attempt + 1}/{max_attempts})"
            )
            try:
                resource.get_record(record_data["id"])
            except AssertionError as exception:
                if attempt == max_attempts - 1:
                    raise AssertionError(
                        "Created record did not become available within "
                        f"{max_attempts}s: {record_data['id']}"
                    ) from exception
                time.sleep(1)
            else:
                break
        return record_data, created_record

    yield _create_record

    cleanup_errors = []
    for record_id in reversed(created_record_ids):
        try:
            api.storage.purge_record(record_id)
        except Exception as exception:
            logger.exception(f"Failed to purge test-owned record {record_id}")
            cleanup_errors.append((record_id, exception))

    if cleanup_errors:
        details = "\n".join(
            f"- {record_id}: {exception}" for record_id, exception in cleanup_errors
        )
        pytest.fail(f"Failed to purge test-owned resources:\n{details}")


@pytest.fixture
def delete_record(api):
    """Fixture to delete any record with id after test."""
    tracked_ids = []

    def _register(record_id: str):
        """Register a record ID for cleanup after the test."""
        tracked_ids.append(record_id)

    yield _register

    cleanup_errors = []
    for record_id in reversed(tracked_ids):
        try:
            api.storage.purge_record(record_id)
        except Exception as exception:
            logger.exception(f"Failed to purge test-owned record {record_id}")
            cleanup_errors.append((record_id, exception))

    if cleanup_errors:
        details = "\n".join(
            f"- {record_id}: {exception}" for record_id, exception in cleanup_errors
        )
        pytest.fail(f"Failed to purge test-owned resources:\n{details}")


@pytest.fixture
def create_isolated_pagination_case(api, delete_record, helper, request, tests_data):
    """Create two records and datasets isolated by a unique search scope."""

    def _create_case(
        api_path: DataTypes,
        record_file: str,
        data_file: str,
        id_template: str,
        schema_version: str = SchemaVersions.DEFAULT,
        analysis_type: Optional[SamplesAnalysisTypes] = None,
        resource_kwargs: Optional[dict] = None,
        record_data_updates: Optional[dict] = None,
        scope_kind: str = "Wellbore",
    ) -> dict:
        resource = getattr(api, api_path)
        scope_param = "wellbore_id" if scope_kind == "Wellbore" else "field_id"
        worker_id = getattr(request.config, "workerinput", {}).get(
            "workerid",
            "master",
        )
        invocation_id = f"{worker_id}_{helper.generate_random_record_id()}"
        scope_id = (
            f"{CONFIG['DATA_PARTITION']}:master-data--{scope_kind}:" f"{invocation_id}"
        )
        scope_value = f"{scope_id}:"

        scope_record = copy.deepcopy(tests_data(DataFiles.OSDU_GENERIC_RECORD))
        scope_record["id"] = scope_id
        scope_record["kind"] = (
            f"{CONFIG['DATA_PARTITION']}:wks:master-data--{scope_kind}:1.0.0"
        )
        api.storage.create_or_update_records([scope_record])
        delete_record(scope_id)

        resource_kwargs = dict(resource_kwargs or {})
        resource_kwargs["schema_version"] = schema_version
        if analysis_type:
            resource_kwargs["analysis_type"] = analysis_type

        record_ids = []
        id_column = None
        for _ in range(2):
            record = copy.deepcopy(tests_data(record_file, analysis_type))
            record["id"] = (
                f"{id_template}{invocation_id}_{helper.generate_random_record_id()}"
            )
            if record_data_updates:
                record["data"].update(record_data_updates)

            if scope_kind == "Wellbore":
                record["data"]["WellboreID"] = scope_value
            else:
                geo_contexts = record["data"].setdefault("GeoContexts", [])
                field_context = next(
                    (context for context in geo_contexts if "FieldID" in context),
                    None,
                )
                if field_context:
                    field_context["FieldID"] = scope_value
                else:
                    geo_contexts.append(
                        {
                            "FieldID": scope_value,
                            "GeoTypeID": "Field",
                        },
                    )

            resource.post_record([record])
            delete_record(record["id"])
            record_ids.append(record["id"])

            data_payload = copy.deepcopy(tests_data(data_file))
            id_column = data_payload["columns"][
                0
            ]  # convention: first column is always the record ID
            data_payload["data"][0][0] = f"{record['id']}:"
            post_response = resource.post_data(
                record_id=record["id"],
                body=data_payload,
                **resource_kwargs,
            )
            dataset_id = helper.get_content_id_from_ddms_urn(
                post_response["ddms_urn"],
            )
            delete_record(dataset_id)

        scope_params = {scope_param: scope_value}
        expected_record_ids = set(record_ids)
        helper.wait_for_exact_search_records(
            lambda: resource.search_records(
                params={**scope_params, "page_limit": 2},
                **resource_kwargs,
            ),
            expected_record_ids,
        )
        helper.wait_for_exact_search_data(
            lambda: resource.search_data(
                params={**scope_params, "page_limit": 2},
                **resource_kwargs,
            ),
            expected_record_ids,
            id_column=id_column,
        )

        return {
            "params": scope_params,
            "record_ids": expected_record_ids,
            "id_column": id_column,
        }

    return _create_case


@pytest.fixture(scope="session")
def data_partition_id():
    """Return the data partition ID from the session configuration."""
    return CONFIG["DATA_PARTITION"]
