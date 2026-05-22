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
from tests.integration.config import DataTypes

COMPARE_RESPONSES_EXCLUDE_PATHS = (
    "root['id']",
    "root['version']",
    "root['createUser']",
    "root['createTime']",
    "root['modifyUser']",
    "root['modifyTime']",
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
        """Generates a random sequence for record_id with a specified
        length."""
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
        :param poll_interval: Delay between retries in seconds
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

    def wait_for_search_data(self, search_func, record_id: str, max_attempts: int = 30, interval: int = 5) -> dict:
        """
        Polls the search function until the specified record_id appears in the results or times out.
        :param search_func: Function with no arguments that returns a search response dict (must have 'result' list)
        :param record_id: Full record ID to look for
        :param max_attempts: Maximum attempts number to wait
        :param poll_interval: Delay between retries in seconds
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
