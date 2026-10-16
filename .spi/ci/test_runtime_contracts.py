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

"""SPI runtime contract tests."""

import pytest

from app.core.helpers.cache.config import RedisCacheConfig


def test_stack_redis_password_binding(monkeypatch):
    expected = f"runtime-value-{id(monkeypatch)}"
    monkeypatch.setenv("REDIS_PASSWORD", expected)

    if RedisCacheConfig().redis_password != expected:
        pytest.fail("REDIS_PASSWORD did not bind to redis_password")
