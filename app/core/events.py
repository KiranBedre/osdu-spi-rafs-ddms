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

from typing import Callable

from fastapi import FastAPI
from loguru import logger

from app.core.helpers.cache_helper import clear_cache, init_cache
from app.core.helpers.pandas_conf import init_pandas
from app.core.settings.app import AppSettings


def create_start_app_handler(
    app: FastAPI,
    settings: AppSettings,
) -> Callable:  # type: ignore

    async def start_app() -> None:
        for setting in settings:
            logger.debug(f"App setting: {setting}")
        await init_cache(settings)
        await init_pandas()

    return start_app


def create_stop_app_handler(
    app: FastAPI,
    settings: AppSettings,
) -> Callable:  # type: ignore
    @logger.catch
    async def stop_app() -> None:
        await clear_cache(settings)

    return stop_app
