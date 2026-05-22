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

from fastapi_cache.backends.inmemory import InMemoryBackend

from app.core.helpers.cache.backends.base_cache import BaseCacheBackend


class InMemoryCacheBackend(BaseCacheBackend):
    async def get_backend(self) -> InMemoryBackend:  # noqa: ASYNC910
        """Init and return instance of InMemoryBackend from fastapi-cache.

        :return InMemoryBackend: instance of InMemoryBackend
        """
        return InMemoryBackend()  # noqa: ASYNC910
