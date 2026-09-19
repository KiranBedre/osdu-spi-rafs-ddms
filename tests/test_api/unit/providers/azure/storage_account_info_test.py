#  Copyright 2024 ExxonMobil Technology and Engineering Company
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

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pydantic_settings import BaseSettings

from app.core.config import AppSettings
from app.providers.dependencies.az.storage_account_info import (
    STORAGE_ACCOUNT_BLOB_ENDPOINT,
    AzureStorageAccountInfo,
    storage_account_key_builder,
)


class MockCloudProviderConfig(BaseSettings):
    az_use_partition_service: bool = True
    az_keyvault_url: str = "https://test-keyvault.vault.azure.net/"
    az_aad_client_id_key: str = "aad-client-id"
    az_container_name: str = "test-container"


@pytest.fixture
def mock_settings():
    settings = Mock(spec=AppSettings)
    settings.service_host_partition = "https://partition-service.com"
    return settings


@pytest.fixture
def mock_cloud_config():
    return MockCloudProviderConfig()


@pytest.fixture
def storage_account_info(mock_settings, mock_cloud_config):
    return AzureStorageAccountInfo(
        data_partition_id="test-partition",
        settings=mock_settings,
        cloud_provider_config=mock_cloud_config,
    )


def test_initialization(storage_account_info, mock_settings, mock_cloud_config):
    """Test that AzureStorageAccountInfo initializes correctly."""
    assert storage_account_info._credential is None
    assert storage_account_info._data_partition_id == "test-partition"
    assert storage_account_info._settings == mock_settings
    assert storage_account_info._cloud_provider_config == mock_cloud_config


@pytest.mark.asyncio
async def test_aenter_creates_credential(storage_account_info):
    """Test that __aenter__ creates DefaultAzureCredential."""
    with patch("app.providers.dependencies.az.storage_account_info.DefaultAzureCredential") as mock_credential_class:
        mock_credential = Mock()
        mock_credential_class.return_value = mock_credential

        result = await storage_account_info.__aenter__()

        assert result == storage_account_info
        assert storage_account_info._credential == mock_credential
        mock_credential_class.assert_called_once()


@pytest.mark.asyncio
async def test_aexit_closes_credential(storage_account_info):
    """Test that __aexit__ closes the credential."""
    mock_credential = AsyncMock()
    storage_account_info._credential = mock_credential

    await storage_account_info.__aexit__(None, None, None)

    mock_credential.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_info_with_partition_service(mock_settings, mock_cloud_config):
    """Test get_info when using partition service."""
    mock_cloud_config.az_use_partition_service = True

    storage_info = AzureStorageAccountInfo(
        data_partition_id="test-partition",
        settings=mock_settings,
        cloud_provider_config=mock_cloud_config,
    )

    # Mock credentials and secrets
    mock_credential = AsyncMock()
    mock_secret_client = AsyncMock()
    mock_aad_secret = Mock()
    mock_aad_secret.value = "test-client-id"
    mock_access_token = Mock()
    mock_access_token.token = "test-token"

    # Mock partition client
    mock_partition_info = {
        STORAGE_ACCOUNT_BLOB_ENDPOINT: {"value": "blob-endpoint-secret-name"},
    }

    # Mock Key Vault secrets
    mock_blob_endpoint_secret = Mock()
    mock_blob_endpoint_secret.value = "https://test-storage-account.blob.core.windows.net/"

    with patch(
        "app.providers.dependencies.az.storage_account_info.DefaultAzureCredential", return_value=mock_credential
    ), patch("app.providers.dependencies.az.storage_account_info.SecretClient") as mock_secret_client_class, patch(
        "app.providers.dependencies.az.storage_account_info.PartitionServiceApiClient"
    ) as mock_partition_client_class:

        # Setup SecretClient mock
        mock_secret_client_instance = AsyncMock()
        mock_secret_client_instance.__aenter__.return_value = mock_secret_client_instance
        mock_secret_client_instance.__aexit__.return_value = None
        mock_secret_client_class.return_value = mock_secret_client_instance

        # First call to SecretClient returns aad_client_id
        # Second call returns blob_endpoint
        mock_secret_client_instance.get_secret.side_effect = [
            mock_aad_secret,  # First call for aad_client_id
            mock_blob_endpoint_secret,  # Second SecretClient for blob_endpoint
        ]

        mock_credential.get_token.return_value = mock_access_token

        # Setup PartitionServiceApiClient mock
        mock_partition_client_instance = AsyncMock()
        mock_partition_client_instance.get_partition_info.return_value = mock_partition_info
        mock_partition_client_class.return_value = mock_partition_client_instance

        async with storage_info:
            result = await storage_info.get_info()

        assert result["container_name"] == "test-container"
        assert result[STORAGE_ACCOUNT_BLOB_ENDPOINT] == "https://test-storage-account.blob.core.windows.net/"

        mock_partition_client_instance.get_partition_info.assert_called_once_with("test-partition")


@pytest.mark.asyncio
async def test_get_info_without_partition_service(mock_settings, mock_cloud_config):
    """Test get_info when not using partition service (fallback mode)."""
    mock_cloud_config.az_use_partition_service = False

    storage_info = AzureStorageAccountInfo(
        data_partition_id="test-partition",
        settings=mock_settings,
        cloud_provider_config=mock_cloud_config,
    )

    mock_credential = AsyncMock()
    mock_blob_endpoint_secret = Mock()
    mock_blob_endpoint_secret.value = "https://test-storage-account.blob.core.windows.net/"

    with patch(
        "app.providers.dependencies.az.storage_account_info.DefaultAzureCredential", return_value=mock_credential
    ), patch("app.providers.dependencies.az.storage_account_info.SecretClient") as mock_secret_client_class:

        mock_secret_client_instance = AsyncMock()
        mock_secret_client_instance.__aenter__.return_value = mock_secret_client_instance
        mock_secret_client_instance.__aexit__.return_value = None
        mock_secret_client_class.return_value = mock_secret_client_instance

        mock_secret_client_instance.get_secret.side_effect = [
            mock_blob_endpoint_secret,
        ]

        async with storage_info:
            result = await storage_info.get_info()

        assert result["container_name"] == "test-container"
        assert result[STORAGE_ACCOUNT_BLOB_ENDPOINT] == "https://test-storage-account.blob.core.windows.net/"

        # Verify fallback partition info was used
        calls = mock_secret_client_instance.get_secret.call_args_list
        assert calls[0][0][0] == f"test-partition-{STORAGE_ACCOUNT_BLOB_ENDPOINT}"


def test_storage_account_key_builder_with_partition_id():
    """Test that storage_account_key_builder includes partition_id in cache key."""
    mock_func = Mock()
    mock_func.__module__ = "test.module"
    mock_func.__name__ = "test_function"

    mock_instance = Mock()
    mock_instance._data_partition_id = "dp1"

    with patch("app.providers.dependencies.az.storage_account_info.FastAPICache") as mock_cache:
        mock_cache.get_prefix.return_value = "test-prefix"

        key1 = storage_account_key_builder(
            func=mock_func,
            namespace="test",
            args=(mock_instance,),
        )

        # Change partition ID
        mock_instance._data_partition_id = "dp2"
        key2 = storage_account_key_builder(
            func=mock_func,
            namespace="test",
            args=(mock_instance,),
        )

        # Keys should be different for different partitions
        assert key1 != key2
        assert "test-prefix:test:" in key1
        assert "test-prefix:test:" in key2


def test_storage_account_key_builder_without_partition_id():
    """Test storage_account_key_builder when instance has no partition_id."""
    mock_func = Mock()
    mock_func.__module__ = "test.module"
    mock_func.__name__ = "test_function"

    mock_instance = Mock(spec=[])  # Instance without _data_partition_id

    with patch("app.providers.dependencies.az.storage_account_info.FastAPICache") as mock_cache:
        mock_cache.get_prefix.return_value = "test-prefix"

        key = storage_account_key_builder(
            func=mock_func,
            namespace="test",
            args=(mock_instance,),
        )

        assert "test-prefix:test:" in key


def test_storage_account_key_builder_with_empty_args():
    """Test storage_account_key_builder with no args."""
    mock_func = Mock()
    mock_func.__module__ = "test.module"
    mock_func.__name__ = "test_function"

    with patch("app.providers.dependencies.az.storage_account_info.FastAPICache") as mock_cache:
        mock_cache.get_prefix.return_value = "test-prefix"

        key = storage_account_key_builder(
            func=mock_func,
            namespace="test",
            args=None,
        )

        assert "test-prefix:test:" in key


def test_storage_account_key_builder_consistency():
    """Test that the same partition ID generates the same cache key."""
    mock_func = Mock()
    mock_func.__module__ = "test.module"
    mock_func.__name__ = "test_function"

    mock_instance = Mock()
    mock_instance._data_partition_id = "consistent-partition"

    with patch("app.providers.dependencies.az.storage_account_info.FastAPICache") as mock_cache:
        mock_cache.get_prefix.return_value = "test-prefix"

        key1 = storage_account_key_builder(
            func=mock_func,
            namespace="test",
            args=(mock_instance,),
        )

        key2 = storage_account_key_builder(
            func=mock_func,
            namespace="test",
            args=(mock_instance,),
        )

        # Same partition should generate the same key
        assert key1 == key2
