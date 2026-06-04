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

from unittest.mock import AsyncMock, patch

import pytest

from app.core.helpers.cache.backend_builder import BackendBuilder
from app.core.helpers.cache.backends.inmemory_cache import InMemoryCacheBackend


@pytest.mark.asyncio
async def test_get_backend():
    mock_backend = AsyncMock()
    mock_cache_backend = AsyncMock()
    mock_cache_backend.get_backend.return_value = mock_backend
    with patch.object(
        BackendBuilder,
        "_get_cache_backend",
        return_value=mock_cache_backend,
    ) as mock_get_cache_backend:

        backend = await BackendBuilder("test_path").build_backend()

        mock_get_cache_backend.assert_called()
        assert mock_backend == backend


def test_get_cache_backend():
    backend_path = "app.core.helpers.cache.backends.inmemory_cache.InMemoryCacheBackend"

    backend = BackendBuilder(backend_path)._get_cache_backend()

    assert isinstance(backend, InMemoryCacheBackend)


@pytest.mark.parametrize(
    "backend_path",
    (
        "test_wrong_path",
        "",
    ),
)
def test_get_cache_backend_import_error(backend_path):
    with pytest.raises(ImportError):
        BackendBuilder(backend_path)._get_cache_backend()
