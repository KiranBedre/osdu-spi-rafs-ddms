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

from fastapi_cache import FastAPICache
from loguru import logger

from app.core.helpers.cache.backend_builder import BackendBuilder
from app.core.settings.app import AppSettings


async def init_cache(settings: AppSettings) -> None:  # noqa: ASYNC910
    """Init cache layer for the app.

    :param AppSettings settings: app settings
    """
    backend = None
    cache_backend = settings.cache_backend
    prefix = settings.openapi_prefix
    cache_enable = settings.cache_enable

    if cache_enable:
        backend_builder = BackendBuilder(
            cache_backend_path=cache_backend,
        )
        backend = await backend_builder.build_backend()
        logger.debug("Fastapi cache enabled")
    else:
        logger.debug("Fastapi cache disabled")

    FastAPICache.init(
        backend,
        prefix=prefix,
        enable=cache_enable,
    )
    logger.debug(
        f"Fastapi cache initialized with settings: backend={cache_backend}, prefix={prefix}, enable={cache_enable}",
    )


async def clear_cache(settings: AppSettings) -> None:  # noqa: ASYNC910
    """Clear cache if cache enabled.

    :param settings: app settings
    :type settings: AppSettings
    """
    if settings.cache_enable:
        await FastAPICache.clear()
        logger.debug("Fastapi cache cleared")
