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
import secrets
import string

from app.api.routes.utils.query import find_osdu_ids_from_string
from tests.integration.config import DataTypes


class CommonHelper(object):
    """Methods to work with all test."""

    def __init__(self, api):
        self.api = api

    @staticmethod
    def extract_only_created_tests_ids(record_id_versions: list) -> list:
        """Extract only tests from created records without updated/created PVT
        id."""
        return [el for el in record_id_versions if DataTypes.PVT.upper() not in el]

    @staticmethod
    def generate_random_record_id(length: int = 10) -> str:
        """Generates a random sequence for record_id with a specified
        length."""
        characters = string.ascii_letters + string.digits  # Include both uppercase and lowercase letters, as well as digits
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
        else:
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
