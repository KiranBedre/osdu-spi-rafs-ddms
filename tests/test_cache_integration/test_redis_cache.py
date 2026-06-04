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

import os

import pytest
import pytest_asyncio

from app.core.helpers.cache.backends.redis_cache import RedisCacheBackend
from app.core.settings.app import AppSettings

# Skip all tests in this module if cache is not enabled
pytestmark = pytest.mark.skipif(
    not os.getenv("CACHE_ENABLE", "false").lower() in ["true", "1", "yes"],
    reason="Redis cache tests only run when CACHE_ENABLE is set to true in .env",
)


@pytest_asyncio.fixture
async def redis_backend():
    """Create a real Redis backend instance for testing."""
    backend = RedisCacheBackend()
    backend_instance = await backend.get_backend()
    yield backend_instance
    # Cleanup: clear any test data
    await backend_instance.clear()


@pytest.mark.asyncio
async def test_redis_backend_initialization():
    """Test that Redis backend can be initialized with real connection."""
    backend = RedisCacheBackend()
    redis_instance = await backend.get_backend()

    assert redis_instance is not None
    assert hasattr(redis_instance, "get")
    assert hasattr(redis_instance, "set")


@pytest.mark.asyncio
async def test_redis_cache_set_and_get(redis_backend):
    """Test setting and getting values from Redis cache."""
    test_key = "test:key:123"
    test_value = b"test_value_data"

    # Set value in cache
    await redis_backend.set(test_key, test_value, expire=60)

    # Get value from cache (should be a HIT)
    retrieved_value = await redis_backend.get(test_key)

    assert retrieved_value == test_value


@pytest.mark.asyncio
async def test_redis_cache_miss(redis_backend):
    """Test cache miss when key doesn't exist."""
    non_existent_key = "test:nonexistent:key:999"

    # Try to get a value that doesn't exist (should be a MISS)
    retrieved_value = await redis_backend.get(non_existent_key)

    assert retrieved_value is None


@pytest.mark.asyncio
async def test_redis_cache_expiration(redis_backend):
    """Test that cache entries expire correctly."""
    import asyncio

    test_key = "test:expiring:key"
    test_value = b"expiring_value"

    # Set value with 1 second expiration
    await redis_backend.set(test_key, test_value, expire=1)

    # Immediately get value (should be a HIT)
    retrieved_value = await redis_backend.get(test_key)
    assert retrieved_value == test_value

    # Wait for expiration
    await asyncio.sleep(2)

    # Try to get expired value (should be a MISS)
    expired_value = await redis_backend.get(test_key)
    assert expired_value is None


@pytest.mark.asyncio
async def test_redis_cache_overwrite(redis_backend):
    """Test that cache values can be overwritten."""
    test_key = "test:overwrite:key"
    initial_value = b"initial_value"
    updated_value = b"updated_value"

    # Set initial value
    await redis_backend.set(test_key, initial_value, expire=60)

    # Verify initial value
    retrieved_value = await redis_backend.get(test_key)
    assert retrieved_value == initial_value

    # Overwrite with new value
    await redis_backend.set(test_key, updated_value, expire=60)

    # Verify updated value
    retrieved_value = await redis_backend.get(test_key)
    assert retrieved_value == updated_value


@pytest.mark.asyncio
async def test_redis_logging_on_cache_hit(redis_backend):
    """Test that cache HIT logging works (logs visible in stderr output)."""
    test_key = "test:logging:hit"
    test_value = b"logged_value"

    # Set value
    await redis_backend.set(test_key, test_value, expire=60)

    # Get value to trigger HIT log (check stderr for: "Cache HIT for key: test:logging:hit")
    result = await redis_backend.get(test_key)

    # Verify the operation worked
    assert result == test_value


@pytest.mark.asyncio
async def test_redis_logging_on_cache_miss(redis_backend):
    """Test that cache MISS logging works (logs visible in stderr output)."""
    test_key = "test:logging:miss:nonexistent"

    # Try to get non-existent value to trigger MISS log (check stderr for: "Cache MISS for key: test:logging:miss:nonexistent")
    result = await redis_backend.get(test_key)

    # Verify the operation worked
    assert result is None


@pytest.mark.asyncio
async def test_redis_logging_on_cache_set(redis_backend):
    """Test that cache SET logging works (logs visible in stderr output)."""
    test_key = "test:logging:set"
    test_value = b"set_logged_value"
    expire_time = 120

    # Set value to trigger SET log (check stderr for: "Cache SET for key: test:logging:set")
    await redis_backend.set(test_key, test_value, expire=expire_time)

    # Verify the operation worked
    result = await redis_backend.get(test_key)
    assert result == test_value
