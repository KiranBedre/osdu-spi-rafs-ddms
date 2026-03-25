#  Copyright 2026 Microsoft Corporation
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

"""Tests for Redis factory resolver pattern."""

import pytest
from unittest import mock

from app.core.helpers.cache.redis_client_factory import RedisClientFactory
from app.providers.dependencies.az.redis_client_factory import AzureRedisClientFactory
from app.providers.dependencies.redis_factory import get_redis_factory


class TestRedisFactoryResolver:
    """Test suite for get_redis_factory function."""

    @pytest.mark.parametrize("use_index_database", [False, True])
    def test_returns_azure_factory_when_azure_provider(self, use_index_database):
        """Should return AzureRedisClientFactory when cloud_provider is azure."""
        # Arrange
        mock_settings = mock.Mock()
        mock_settings.cloud_provider = "azure"

        # Act
        factory = get_redis_factory(mock_settings, use_index_database=use_index_database)

        # Assert
        assert isinstance(factory, AzureRedisClientFactory)
        # Config and flag are stored in factory
        assert factory.config is not None
        assert factory.use_index_database == use_index_database

    @pytest.mark.parametrize("cloud_provider", ["aws", "gcp", "unknown", ""])
    def test_returns_base_factory_for_non_azure_providers(self, cloud_provider):
        """Should return base RedisClientFactory for non-azure providers."""
        # Arrange
        mock_settings = mock.Mock()
        mock_settings.cloud_provider = cloud_provider

        # Act
        factory = get_redis_factory(mock_settings, use_index_database=False)

        # Assert
        assert isinstance(factory, RedisClientFactory)
        # Make sure it's the base class, not a subclass
        assert type(factory).__name__ == "RedisClientFactory"
        # Config is stored in factory
        assert factory.config is not None
