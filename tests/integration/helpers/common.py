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
import os
import secrets
import string
import time
from io import BytesIO

import pandas
from deepdiff import DeepDiff
from jsonpointer import JsonPointerException, resolve_pointer, set_pointer
from loguru import logger

from app.api.routes.utils.query import find_osdu_ids_from_string
from tests.integration.config import DataFiles, DataTypes

COMPARE_RESPONSES_EXCLUDE_PATHS = (
    "root['id']",
    "root['version']",
    "root['createUser']",
    "root['createTime']",
    "root['modifyUser']",
    "root['modifyTime']",
    "root['meta']",
)


class CommonHelper:
    """Methods to work with all test."""

    def __init__(self, api):
        self.api = api

    @staticmethod
    def extract_only_created_tests_ids(record_id_versions: list) -> list:
        """Extract only tests from created records without updated/created PVT
        id."""
        return [el for el in record_id_versions if "PVT" not in el]

    @staticmethod
    def generate_random_record_id(length: int = 10) -> str:
        """Generates a random sequence for record_id with a specified length."""
        characters = string.ascii_letters + string.digits  # Include uppercase and lowercase letters, as well as digits
        random_id = f"autotest_{''.join(secrets.choice(characters) for _ in range(length))}"
        return random_id

    def create_data_copies(self, original_data, num_copies) -> list:
        """Creates data copies of data objects with generated id."""
        copies = [copy.deepcopy(original_data) for _ in range(num_copies)]
        for copy_index, copy_data in enumerate(copies):
            copy_data["id"] = f"{copy_data['id']}_{self.generate_random_record_id()}"
        return copies

    @staticmethod
    def get_content_id_from_ddms_urn(ddms_urn: str) -> str:
        """Gets the content_id part from full urn."""
        # remove when fully migrated to blob storage
        rafs_use_blob_storage = os.getenv("RAFS_USE_BLOB_STORAGE")
        if rafs_use_blob_storage and rafs_use_blob_storage == "True":
            return ddms_urn.split("/")[-1]
        return ddms_urn.split("/")[-2]

    @staticmethod
    def parse_full_record_id(record_urn: str) -> dict:
        """Parse a full record ID from a given URN and extract its components.

        :param record_urn: The URN representing the full record ID.

        :return: A dictionary containing the parsed components of the full record ID.
                 The dictionary has the following keys:
                    - "partition_id" (str): The partition ID of the record.
                    - "record_type" (str): The type of the record.
                    - "record_id" (str): The ID of the record.
                    - "version" (int): The version of the record.
                    - "record_without_version" (str): Parts without version
        """
        full_id = record_urn.split(":")
        return {
            "partition_id": full_id[0],
            "record_type": full_id[1],
            "record_id": full_id[2],
            "version": int(full_id[3]),
            "record_without_version": ":".join(full_id[:3]),
        }

    @staticmethod
    def find_ids_from_string(input_string: str) -> set:
        """Takes a string and returns the set of ids that match osdu id regex.

        :param input_string: data string
        :type input_string: str
        :return: the set of osdu ids present in the string
        :rtype: set
        """
        return find_osdu_ids_from_string(input_string)

    @staticmethod
    def load_parquet_data(body: bytes, content_type: str) -> dict | None:
        """Converts the input body to a unified dictionary format.

        If content_type is 'parquet', parses it and converts to dict in
        'split' format.
        """
        if content_type == "parquet":
            df = pandas.read_parquet(BytesIO(body))
            return json.loads(df.to_json(orient="split"))

        raise ValueError(f"Unsupported content type: {content_type}")

    def compare_responses(self, json_body: dict, response_body, response_type="parquet"):
        """
        Compares request body to actual response (both JSON or Parquet), ignoring dynamic fields.

        :param json_body: The actual response body (dict).
        :param response_body: The expected response body (dict for JSON, bytes for Parquet).
        :param response_type: Type of expected response ('json' or 'parquet').
        """
        if response_type == "parquet":
            response_data = self.load_parquet_data(response_body, content_type="parquet")
        elif response_type == "json":
            response_data = response_body
        else:
            raise ValueError(f"Unsupported expected_type: {response_type}")

        diff = DeepDiff(
            json_body,
            response_data,
            ignore_order=True,
            significant_digits=6,
            exclude_paths=COMPARE_RESPONSES_EXCLUDE_PATHS,
        )

        if diff:
            assert False, f"Responses do not match!\n{diff.to_json(indent=2)}\n"

    def compare_response_fields(self, actual: dict, expected: dict) -> None:
        """
        Assert that every key in ``expected`` exists in ``actual`` with the same value.

        :param actual: Section of an API response.
        :param expected: Dict of expected field values.
        :raises AssertionError: With the offending field name and values.
        """
        for key, expected_value in expected.items():
            assert key in actual, f"Missing field: {key}"
            assert actual[key] == expected_value, f"{key}: expected {expected_value!r}, got {actual[key]!r}"

    def delete_by_path(self, json_body: dict, path: str) -> None:
        """
        Delete key/element addressed by JSON Pointer.
        :param json_body: json body (dict).
        :param path: path to field.
        """
        parent_path, _, last = path.rpartition("/")
        parent_path = parent_path or ""  # root
        try:
            parent = resolve_pointer(json_body, parent_path)
        except JsonPointerException:
            return  # if parent path doesn't exist

        if isinstance(parent, dict):
            parent.pop(last, None)
        elif isinstance(parent, list):
            try:
                idx = int(last)
            except ValueError as exc:
                raise ValueError(f"List index must be int in pointer: {path}: {exc}") from exc
            if 0 <= idx < len(parent):
                parent.pop(idx)

    def set_by_path(self, json_body: dict, path: str, value) -> None:
        """
        Set value addressed by JSON Pointer.
        :param json_body: json body (dict).
        :param path: path to field.
        """
        try:
            set_pointer(json_body, path, value)
        except JsonPointerException as exc:
            raise AssertionError(f"Invalid JSON pointer '{path}': {exc}") from exc

    def wait_for_search_record(self, search_func, record_id: str, max_attempts: int = 30, interval: int = 5) -> dict:
        """
        Polls the search function until the specified record_id appears in the results or times out.
        :param search_func: Function with no arguments that returns a search response dict (must have 'result' list)
        :param record_id: Full record ID to look for
        :param max_attempts: Maximum attempts number to wait
        :param interval: Delay between retries in seconds
        :return: The last search response containing the record
        :raises AssertionError: If the record is not found within the timeout
        """
        last_response: dict | None = None

        for attempt in range(max_attempts):
            last_response = search_func()
            results = last_response.get("result", [])
            if any(record_id in entry for entry in results):
                logger.info(f"Record '{record_id}' found in search results.")
                return last_response

            logger.info(
                f"Record '{record_id}' not found yet; retrying in {interval}s (Attempt {attempt + 1}/{max_attempts})"
            )
            if attempt < max_attempts - 1:
                time.sleep(interval)

        raise AssertionError(
            f"Record '{record_id}' not found in search results within {max_attempts*interval}s. "
            f"Last response: {last_response}"
        )

    def wait_for_exact_search_records(
        self,
        search_func,
        expected_record_ids: set[str],
        max_attempts: int = 30,
        interval: int = 5,
        required_consecutive_matches: int = 2,
    ) -> dict:
        """Poll until search stably returns exactly the test-owned records."""
        last_response: dict | None = None
        consecutive_matches = 0

        for attempt in range(max_attempts):
            last_response = search_func()
            actual_record_ids = set(last_response.get("result", []))
            if actual_record_ids == expected_record_ids:
                consecutive_matches += 1
                if consecutive_matches >= required_consecutive_matches:
                    return last_response
            else:
                consecutive_matches = 0

            logger.info(
                "Expected records are not stably searchable yet; retrying in "
                f"{interval}s (attempt {attempt + 1}/{max_attempts}). "
                f"Expected: {expected_record_ids}; actual: {actual_record_ids}; "
                f"consecutive matches: {consecutive_matches}/"
                f"{required_consecutive_matches}"
            )
            if attempt < max_attempts - 1:
                time.sleep(interval)

        raise AssertionError(
            "Expected records were not returned within "
            f"{max_attempts * interval}s. Expected: {expected_record_ids}; "
            f"last response: {last_response}"
        )

    def wait_for_exact_search_data(
        self,
        search_func,
        expected_record_ids: set[str],
        id_column: str,
        max_attempts: int = 30,
        interval: int = 5,
        required_consecutive_matches: int = 2,
    ) -> dict:
        """Poll until search_data stably exposes all test-owned datasets."""
        last_response: dict | None = None
        consecutive_matches = 0

        for attempt in range(max_attempts):
            last_response = search_func()
            result = last_response.get("result") or {}
            columns = result.get("columns", [])
            rows = result.get("data", [])
            actual_record_ids = set()

            if id_column in columns:
                id_column_index = columns.index(id_column)
                actual_record_ids = {row[id_column_index].removesuffix(":") for row in rows}

            if actual_record_ids == expected_record_ids and last_response.get("total_size") == len(expected_record_ids):
                consecutive_matches += 1
                if consecutive_matches >= required_consecutive_matches:
                    return last_response
            else:
                consecutive_matches = 0

            logger.info(
                "Expected datasets are not stably searchable yet; retrying in "
                f"{interval}s (attempt {attempt + 1}/{max_attempts}). "
                f"Expected: {expected_record_ids}; actual: {actual_record_ids}; "
                f"total_size: {last_response.get('total_size')}; "
                f"consecutive matches: {consecutive_matches}/"
                f"{required_consecutive_matches}"
            )
            if attempt < max_attempts - 1:
                time.sleep(interval)

        raise AssertionError(
            "Expected datasets were not returned within "
            f"{max_attempts * interval}s. ID column: {id_column}; "
            f"expected: {expected_record_ids}; last response: {last_response}"
        )

    @staticmethod
    def verify_record_pagination(search_func, pagination_case: dict) -> None:
        """Verify a complete two-record page and two distinct one-record pages."""
        base_params = pagination_case["params"]
        expected_record_ids = pagination_case["record_ids"]

        full_page = search_func({**base_params, "offset": 0, "page_limit": 2})
        first_page = search_func({**base_params, "offset": 0, "page_limit": 1})
        second_page = search_func({**base_params, "offset": 1, "page_limit": 1})

        context = (
            f"Params: {base_params}\n"
            f"Expected IDs: {expected_record_ids}\n"
            f"Full page: {full_page}\n"
            f"First page: {first_page}\n"
            f"Second page: {second_page}"
        )

        assert full_page["page_limit"] == 2, context
        assert full_page["offset"] == 0, context
        assert full_page["total_size"] == 2, context
        assert set(full_page["result"]) == expected_record_ids, context
        assert len(full_page["result"]) == 2, context

        assert first_page["page_limit"] == 1, context
        assert first_page["offset"] == 0, context
        assert len(first_page["result"]) == 1, context

        assert second_page["page_limit"] == 1, context
        assert second_page["offset"] == 1, context
        assert len(second_page["result"]) == 1, context
        assert set(first_page["result"] + second_page["result"]) == expected_record_ids, context

    @staticmethod
    def verify_data_pagination(search_func, pagination_case: dict) -> None:
        """Verify dataset pagination using only records created by the test."""
        base_params = pagination_case["params"]
        expected_record_ids = pagination_case["record_ids"]
        id_column = pagination_case["id_column"]

        full_page = search_func({**base_params, "offset": 0, "page_limit": 2})
        first_page = search_func({**base_params, "offset": 0, "page_limit": 1})
        second_page = search_func({**base_params, "offset": 1, "page_limit": 1})

        def _record_ids(response: dict) -> set[str]:
            result = response["result"]
            assert id_column in result["columns"], (
                f"Expected ID column '{id_column}' in search_data response.\n"
                f"Params: {base_params}\n"
                f"Response: {response}"
            )
            id_column_index = result["columns"].index(id_column)
            return {row[id_column_index].removesuffix(":") for row in result["data"]}

        context = (
            f"Params: {base_params}\n"
            f"Expected IDs: {expected_record_ids}\n"
            f"ID column: {id_column}\n"
            f"Full page: {full_page}\n"
            f"First page: {first_page}\n"
            f"Second page: {second_page}"
        )

        assert full_page["page_limit"] == 2, context
        assert full_page["offset"] == 0, context
        assert full_page["total_size"] == 2, context
        assert _record_ids(full_page) == expected_record_ids, context
        assert len(_record_ids(full_page)) == 2, context

        assert first_page["page_limit"] == 1, context
        assert first_page["offset"] == 0, context
        assert len(_record_ids(first_page)) == 1, context

        assert second_page["page_limit"] == 1, context
        assert second_page["offset"] == 1, context
        assert len(_record_ids(second_page)) == 1, context
        assert (_record_ids(first_page) | _record_ids(second_page)) == expected_record_ids, context

    def wait_for_search_data(self, search_func, record_id: str, max_attempts: int = 30, interval: int = 5) -> dict:
        """
        Polls the search function until the specified record_id appears in the results or times out.
        :param search_func: Function with no arguments that returns a search response dict (must have 'result' list)
        :param record_id: Full record ID to look for
        :param max_attempts: Maximum attempts number to wait
        :param interval: Delay between retries in seconds
        :return: The last search response containing the record
        :raises AssertionError: If the record is not found within the timeout
        """
        last_response: dict | None = None

        for attempt in range(max_attempts):
            last_response = search_func()
            result = last_response.get("result", {})
            columns = result.get("columns", [])
            data = result.get("data", [])

            if not data:
                logger.warning(f"No results yet (attempt {attempt + 1}/{max_attempts}).")
            else:
                for row in data:
                    if row[0] == f"{record_id}:":
                        logger.info(f"Record '{record_id}' found in search results.")
                        return last_response

            logger.info(
                f"Record '{record_id}' not found; retrying in {interval}s (attempt {attempt + 1}/{max_attempts})."
            )
            if attempt < max_attempts - 1:
                time.sleep(interval)

        raise AssertionError(
            f"Record '{record_id}' not found in search results within {max_attempts * interval}s. "
            f"Last response: {last_response}"
        )

    def create_reference_records(
        self,
        api,
        helper,
        tests_data,
        partition: str,
        storage_dependencies: set,
        record_to_create: list,
        fixed_id_records: list,
    ) -> dict:
        """Create reference records and SAR record; return IDs to share across workers."""
        osdu_generic_record = tests_data(DataFiles.OSDU_GENERIC_RECORD)
        records_to_store = []
        for reference_id in storage_dependencies:
            if "reference-data" in reference_id:
                continue
            api.storage.purge_record(reference_id)
            record_to_store = copy.deepcopy(osdu_generic_record)
            record_to_store["id"] = reference_id
            record_type = reference_id.split(":")[1]
            record_to_store["kind"] = f"{partition}:wks:{record_type}:1.0.0"
            records_to_store.append(record_to_store)

        response = api.storage.create_or_update_records(records_to_store)
        logger.debug(response.json())

        created_ids = {}
        for data_type, data, id_template in record_to_create:
            record_data = copy.deepcopy(tests_data(data))
            record_data["id"] = f"{id_template}{helper.generate_random_record_id()}"
            getattr(api, data_type).post_record([record_data])
            created_ids[f"{data_type}_record_id"] = record_data["id"]

        for data in fixed_id_records:
            record_data = copy.deepcopy(tests_data(data))
            created_ids[f"{data}_fixed_id"] = record_data["id"]
            record_response = api.storage.get(
                path=f"/records/{record_data['id']}",
                allowed_codes=[200, 404],
            )
            fixed_record_was_created = record_response.status_code == 404
            created_ids[f"{data}_fixed_id_created"] = fixed_record_was_created

            if fixed_record_was_created:
                api.storage.create_or_update_records([record_data])

        return created_ids

    def purge_reference_records(
        self,
        api,
        state: dict,
        storage_dependencies: set,
        record_to_create: list,
        fixed_id_records: list = None,
    ) -> None:
        """Purge SAR record and reference records."""
        for data_type, _, _ in record_to_create:
            api.storage.purge_record(state[f"{data_type}_record_id"])
        for data in fixed_id_records or []:
            if state.get(f"{data}_fixed_id_created"):
                api.storage.purge_record(state[f"{data}_fixed_id"])
        for reference_id in storage_dependencies:
            if "reference-data" in reference_id:
                continue
            api.storage.purge_record(reference_id)
