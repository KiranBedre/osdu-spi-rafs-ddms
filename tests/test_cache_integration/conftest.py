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

"""
Conftest for cache integration tests.

This conftest STOPS the cache mock from the parent conftest.py,
allowing real cache behavior to be tested.
"""

from unittest import mock

import pytest

# The parent tests/conftest.py mocks the cache decorator globally.
# We need to stop that mock for cache integration tests to work properly.
# This finds and stops the active cache decorator mock.


@pytest.fixture(scope="session", autouse=True)
def unmock_cache_decorator():
    """Stop the cache decorator mock for integration tests."""
    # Stop any active mocks on fastapi_cache.decorator.cache
    mock.patch.stopall()
    yield
    # Note: We don't restart the mock here because these are isolated integration tests
