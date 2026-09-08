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

import sys
from unittest.mock import MagicMock, create_autospec

import pytest
from loguru import logger

from app.core.config import get_app_settings
from app.models.schemas.user import User
from app.providers.dependencies.blob_loader import IBlobLoader
from app.resources.common_headers import CORRELATION_ID
from app.services.dataset import DatasetService, create_default_dataset_record
from app.services.osdu_clients.dataset_client import DatasetServiceApiClient
from tests.test_api.test_routes.osdu.storage_mock_objects import (
    OSDU_GENERIC_RECORD,
)

# Constants for string literals
TEST_URL = "test-url"
TEST_FILE_SOURCE = "test-file-source"
TEST_ID = "test-id"
TEST_VERSION = "test-version"
TEST_DATA_PARTITION_ID = "test-data-partition-id"
TEST_DATASET_ID = "test-dataset-id"
TEST_PARENT_ID = "test-parent-id"
TEST_PARENT_KIND = "test-parent-kind"
TEST_FIELD_VALUE = "test-value"
TEST_KIND_SUB_TYPE = "dataset--File.Generic"
TEST_TOKEN = "token"
RESOURCE_SECURITY_KEY = "ResourceSecurityClassification"
TEST_CORRELATION_ID = "test_id"


class TestDatasetService:

    @pytest.fixture
    def mock_settings(self):
        settings = get_app_settings()
        return settings

    @pytest.fixture
    def mock_dataset_client(self):
        return MagicMock(spec=DatasetServiceApiClient)

    @pytest.fixture
    def mock_blob_loader(self):
        return create_autospec(IBlobLoader, spec_set=True)

    @pytest.mark.asyncio
    async def test_upload_file(self, mock_settings, mock_dataset_client, mock_blob_loader, monkeypatch):
        mock_get_loader = MagicMock()
        monkeypatch.setattr("app.services.dataset.get_blob_loader", mock_get_loader)

        mock_dataset_client.storage_instructions.return_value = {
            "storageLocation": {
                "signedUrl": TEST_URL,
                "fileSource": TEST_FILE_SOURCE,
            },
        }
        mock_dataset_client.create_or_update_dataset_registry.return_value = {
            "datasetRegistries": [
                {
                    "id": TEST_ID,
                    "version": TEST_VERSION,
                },
            ],
        }
        ds = DatasetService(
            TEST_DATA_PARTITION_ID,
            mock_settings,
            User(access_token=TEST_TOKEN),
            extra_headers={CORRELATION_ID: TEST_CORRELATION_ID},
        )
        ds.dataset_client = mock_dataset_client
        ds.blob_loader = mock_blob_loader

        # Create a mock parent record
        parent_record = {
            **OSDU_GENERIC_RECORD.model_dump(exclude_none=True),
            **{
                "data": {
                    RESOURCE_SECURITY_KEY: TEST_FIELD_VALUE,
                },
            },
        }

        # Create a mock blob file
        blob_file = b"test-blob-file"

        # Call the upload_file method
        response = await ds.upload_file(blob_file=blob_file, dataset_id=TEST_DATASET_ID, parent_record=parent_record)

        # Check that the result matches the expected output
        assert response == f"{TEST_ID}:{TEST_VERSION}"

        # Check upload blob was actually called
        mock_blob_loader.upload_blob.assert_called_once_with(
            TEST_URL,
            blob_file,
        )

        # Check that the client method was called with the correct arguments
        mock_dataset_client.storage_instructions.assert_called_once_with(
            kind_subtype=TEST_KIND_SUB_TYPE,
        )

        # Check that the registry client method was called with the correct arguments
        expected_record_list = [
            create_default_dataset_record(
                TEST_DATASET_ID,
                TEST_FILE_SOURCE,
                str(sys.getsizeof(blob_file)),
                parent_record,
                "osdu",
            ),
        ]
        assert len(mock_dataset_client.create_or_update_dataset_registry.call_args_list) == 1

        # Get the arguments used in the first call to create_or_update_dataset_registry
        register_args = mock_dataset_client.create_or_update_dataset_registry.call_args_list[0][1]
        dataset_registries = register_args["dataset_registries"]
        actual_data = dataset_registries[0]["data"]

        # assert data has been updated properly
        assert actual_data == expected_record_list[0]["data"]
        assert RESOURCE_SECURITY_KEY in actual_data
