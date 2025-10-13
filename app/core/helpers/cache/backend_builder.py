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

from importlib import import_module

from fastapi_cache.backends import Backend

from app.core.helpers.cache.backends.base_cache import BaseCacheBackend


class BackendBuilder(object):
    """Import cache layer class from string path inside the CACHE_BACKEND
    variable to get prepared fastapi-cache backend instance."""

    def __init__(self, cache_backend_path: str) -> None:
        self.cache_backend_path = cache_backend_path

    async def build_backend(self) -> Backend:
        """Get prepared fastapi-cache backend instance.

        :return Backend: prepared instance of fastapi-cache backend
        """
        cache_backend = self._get_cache_backend()
        return await cache_backend.get_backend()

    def _get_cache_backend(self) -> BaseCacheBackend:
        """Import backend (cache layer) class from string path.

        :return BaseCacheBackend: instance of cache layer backend
        :raises:
          ImportError: if self.cache_backend_path is empty or cannot be splitted
        """
        try:
            module_path, class_name = self.cache_backend_path.rsplit(".", 1)
        except ValueError:
            raise ImportError(
                f"cache_backend variable value: '{self.cache_backend_path}' doesn't look like a proper module path",
            )

        module = import_module(module_path)
        cache_backend_cls = getattr(module, class_name)
        return cache_backend_cls()
