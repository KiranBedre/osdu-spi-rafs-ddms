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
import os
import time

import pytest

from client.api_client import APIClient
from tests.integration.config import (
    CONFIG,
    DataFiles,
    DataTemplates,
    DataTypes,
    SamplesAnalysisTypes,
    SchemaVersions,
    VersionedDataFiles,
)


@pytest.fixture(scope="session")
def add_search_scope():
    """Return a helper that scopes search_data to the current test case."""

    def _add_search_scope(params, endpoint, case):
        scoped_params = dict(params)

        if endpoint == "search_data":
            scoped_params.update(
                {
                    "wellbore_id": case["wellbore_id"],
                    "rows_filter": ("SamplesAnalysisID,eq," f"{case['sample_analysis_record_id']}:"),
                }
            )

        return scoped_params

    return _add_search_scope


@pytest.fixture(scope="session")
def search_api():
    """Create the Search client needed only by integration-test polling."""
    return APIClient(
        os.environ["SERVICE_HOST_SEARCH"],
        "",  # no API-path prefix
        "",  # no API version segment
        CONFIG["DATA_PARTITION"],
        CONFIG["TOKEN"],
    )


@pytest.fixture
def depth_shift_create_record(api, create_record):
    """Create a Depth Shift record."""
    record_data, _ = create_record(
        DataTypes.DEPTH_SHIFT,
        DataFiles.DEPTH_SHIFT,
        DataTemplates.ID_DEPTH_SHIFT.format(partition=CONFIG["DATA_PARTITION"]),
    )
    yield record_data
    api.storage.purge_record(record_data["id"])


@pytest.fixture(scope="function")
def depth_shift_create_fresh_record(api, create_record):
    """Create a fresh Depth Shift record."""
    record_data, _ = create_record(
        DataTypes.DEPTH_SHIFT,
        DataFiles.DEPTH_SHIFT,
        DataTemplates.ID_DEPTH_SHIFT.format(partition=CONFIG["DATA_PARTITION"]),
    )
    yield record_data
    api.storage.purge_record(record_data["id"])


@pytest.fixture
def depth_shift_record_id(depth_shift_create_record):
    """Return Depth Shift record_id."""
    return depth_shift_create_record["id"]


@pytest.fixture(scope="function")
def fresh_depth_shift_record_id(depth_shift_create_fresh_record):
    """Return fresh Depth Shift record_id."""
    return depth_shift_create_fresh_record["id"]


@pytest.fixture
def create_depth_shift_dataset(api, helper, tests_data):
    """Create and track exactly the Depth Shift datasets requested by a test."""
    dataset_ids = []

    def _create(record_id, data_payload=None):
        payload = copy.deepcopy(data_payload or tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA))
        if isinstance(payload, dict) and "data" in payload:
            payload["data"][0][0] = f"{record_id}:"
        elif isinstance(payload, list):
            payload[0]["DepthShiftWPCID"] = f"{record_id}:"
        else:
            payload["DepthShiftWPCID"] = f"{record_id}:"

        post_response = api.depth_shift.post_data(record_id, payload)
        dataset_id = helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])
        dataset_ids.append(dataset_id)
        return dataset_id

    yield _create

    for dataset_id in reversed(dataset_ids):
        api.storage.purge_record(dataset_id)


@pytest.fixture
def depth_shift_dataset_id(depth_shift_record_id, create_depth_shift_dataset):
    """Create the default Depth Shift dataset and return its ID."""
    return create_depth_shift_dataset(depth_shift_record_id)


@pytest.fixture(scope="function")
def fresh_depth_shift_dataset_id(api, helper, fresh_depth_shift_record_id, tests_data):
    """Create a fresh dataset and return dataset_id."""
    data_payload = copy.deepcopy(tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA))
    data_payload["data"][0][0] = f"{fresh_depth_shift_record_id}:"
    post_response = api.depth_shift.post_data(
        fresh_depth_shift_record_id,
        data_payload,
    )
    dataset_id = helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])
    yield dataset_id
    api.storage.purge_record(dataset_id)


@pytest.fixture(scope="package")
def analysis_type():
    """Default analysis type; can be overridden via parametrization."""
    return SamplesAnalysisTypes.NMR


@pytest.fixture
def create_apply_depth_shift_case(
    api,
    delete_record,
    helper,
    request,
    search_api,
    tests_data,
    analysis_type,
):
    """Create an invocation-scoped Sample, SamplesAnalysis record, and dataset."""

    def _wait_for_sample_visibility(
        sample_id,
        sample_kind,
        sample_version,
        definitive_depth_shift_id,
        timeout_seconds=120,
        interval_seconds=5,
    ):
        deadline = time.monotonic() + timeout_seconds
        field_visibility_started_at = None
        field_visibility_timeout_seconds = 30
        last_response = None

        while time.monotonic() < deadline:
            last_response = search_api.post(
                path="/query",
                json={
                    "kind": sample_kind,
                    "query": f'id:"{sample_id}"',
                    "returnedFields": [
                        "id",
                        "version",
                        "data.DefinitiveDepthShift.DefinitiveDepthShiftID",
                    ],
                    "limit": 1,
                },
            ).json()

            matching_record = next(
                (
                    record
                    for record in last_response.get("results", [])
                    if record.get("id", "").rstrip(":") == sample_id
                ),
                None,
            )
            if matching_record:
                visible_version = str(matching_record.get("version"))
                record_data = matching_record.get("data", {})
                visible_depth_shift_id = record_data.get("DefinitiveDepthShift.DefinitiveDepthShiftID")
                if visible_depth_shift_id is None:
                    visible_depth_shift_id = record_data.get("DefinitiveDepthShift", {}).get("DefinitiveDepthShiftID")
                version_matches = visible_version == str(sample_version)
                depth_shift_matches = (
                    definitive_depth_shift_id is None or visible_depth_shift_id == definitive_depth_shift_id
                )
                if version_matches and depth_shift_matches:
                    return matching_record
                if version_matches and definitive_depth_shift_id is not None:
                    if field_visibility_started_at is None:
                        field_visibility_started_at = time.monotonic()
                    elif time.monotonic() - field_visibility_started_at >= field_visibility_timeout_seconds:
                        break
                else:
                    field_visibility_started_at = None

            if time.monotonic() < deadline:
                time.sleep(interval_seconds)

        raise AssertionError(
            "Expected the invocation-scoped Sample version and definitive "
            "depth-shift ID to become visible in Search.\n"
            f"Sample ID: {sample_id}\n"
            f"Expected version: {sample_version}\n"
            "Expected definitive depth-shift ID: "
            f"{definitive_depth_shift_id}\n"
            f"Version visibility timeout: {timeout_seconds}s\n"
            "Definitive depth-shift field timeout after version visibility: "
            f"{field_visibility_timeout_seconds}s\n"
            f"Last Search response: {last_response}"
        )

    def _create_case(sample_definition=None, wait_for_search=False):
        worker_id = getattr(request.config, "workerinput", {}).get(
            "workerid",
            "master",
        )
        invocation_id = f"{worker_id}_{helper.generate_random_record_id()}"

        sample_record = copy.deepcopy(sample_definition or tests_data(DataFiles.SAMPLE))
        sample_kind_base = sample_record["kind"].rsplit(":", 1)[0]
        sample_record["kind"] = f"{sample_kind_base}:{SchemaVersions.V3_1_0}"
        definitive_depth_shift = sample_record["data"].get(
            "DefinitiveDepthShift",
        )
        if definitive_depth_shift and definitive_depth_shift.get("DefinitiveDepthShiftID") is None:
            sample_record["data"].pop("DefinitiveDepthShift")
        sample_id = f"{DataTemplates.ID_SAMPLE.format(partition=CONFIG['DATA_PARTITION'])}" f"{invocation_id}"
        sample_value = f"{sample_id}:"
        sample_record["id"] = sample_id

        sample_response = api.storage.create_or_update_records([sample_record])
        delete_record(sample_id)
        sample_full_id = sample_response.json()["recordIdVersions"][0]
        sample_version = sample_full_id.rsplit(":", 1)[1]

        sample_analysis_record = copy.deepcopy(tests_data(DataFiles.SAMPLE_ANALYSIS, analysis_type))
        sample_analysis_record_id = (
            f"{DataTemplates.ID_SAMPLE_ANALYSIS.format(partition=CONFIG['DATA_PARTITION'])}" f"{invocation_id}"
        )
        sample_analysis_record["id"] = sample_analysis_record_id
        sample_analysis_record["data"]["SampleIDs"] = [sample_value]
        api.sample_analysis.post_record([sample_analysis_record])
        delete_record(sample_analysis_record_id)

        data_file = VersionedDataFiles.VALUES[(analysis_type, SchemaVersions.V1_0_0)]
        data_payload = copy.deepcopy(tests_data(data_file))
        record_id_index = data_payload["columns"].index("SamplesAnalysisID")
        sample_id_index = data_payload["columns"].index("SampleID")
        for row in data_payload["data"]:
            row[record_id_index] = f"{sample_analysis_record_id}:"
            row[sample_id_index] = sample_value

        post_response = api.sample_analysis.post_data(
            record_id=sample_analysis_record_id,
            body=data_payload,
            analysis_type=analysis_type,
            schema_version=SchemaVersions.V1_0_0,
        )
        sample_analysis_dataset_id = helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])
        delete_record(sample_analysis_dataset_id)

        wellbore_id = sample_record["data"]["SampleAcquisition"]["SampleAcquisitionDetail"]["WellboreID"]
        definitive_depth_shift_id = (
            sample_record["data"]
            .get(
                "DefinitiveDepthShift",
                {},
            )
            .get("DefinitiveDepthShiftID")
        )

        if wait_for_search:
            _wait_for_sample_visibility(
                sample_id=sample_id,
                sample_kind=sample_record["kind"],
                sample_version=sample_version,
                definitive_depth_shift_id=definitive_depth_shift_id,
            )
            helper.wait_for_search_record(
                lambda: api.sample_analysis.search_records(
                    analysis_type=analysis_type,
                    schema_version=SchemaVersions.V1_0_0,
                    params={"rows_filter": ("SamplesAnalysisID,eq," f"{sample_analysis_record_id}:")},
                ),
                sample_analysis_record_id,
            )
            helper.wait_for_exact_search_data(
                lambda: api.sample_analysis.search_data(
                    analysis_type=analysis_type,
                    schema_version=SchemaVersions.V1_0_0,
                    params={
                        "wellbore_id": wellbore_id,
                        "rows_filter": ("SamplesAnalysisID,eq," f"{sample_analysis_record_id}:"),
                    },
                ),
                expected_record_ids={sample_analysis_record_id},
                id_column="SamplesAnalysisID",
            )

        return {
            "sample_id": sample_id,
            "sample_value": sample_value,
            "sample_version": sample_version,
            "wellbore_id": wellbore_id,
            "definitive_depth_shift_id": definitive_depth_shift_id,
            "sample_analysis_record_id": sample_analysis_record_id,
            "sample_analysis_dataset_id": sample_analysis_dataset_id,
            "analysis_type": analysis_type,
        }

    return _create_case


@pytest.fixture(scope="function", autouse=True)
def restore_sample_definition(api, tests_data):
    """Restore the fixed Sample record after tests that mutate it."""
    sample_id = copy.deepcopy(tests_data(DataFiles.SAMPLE))["id"]
    sample_snapshot_response = api.storage.get(
        path=f"/records/{sample_id}",
        allowed_codes=[200, 404],
    )
    sample_snapshot = None
    if sample_snapshot_response.status_code == 200:
        sample_snapshot = sample_snapshot_response.json()

    yield

    if sample_snapshot is not None:
        api.storage.create_or_update_records([sample_snapshot])
