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
from app.providers.helpers.tracing import initialize_tracer, restart_otel_span_processors


def create_start_app_handler(
    app: FastAPI,
    settings: AppSettings,
) -> Callable:  # type: ignore

    async def start_app() -> None:
        for setting in settings:
            logger.debug(f"App setting: {setting}")
        # Each uvicorn worker must own a fresh TracerProvider and OTLPSpanExporter so
        # that the HTTP connection pool is not shared across forked processes.
        # restart_otel_span_processors() handles the case where a provider is already
        # present with a live export thread (no-op).  When it returns False — either
        # no provider yet or the agent's post-fork thread is running — initialize_tracer()
        # creates a fresh per-worker provider regardless of what the master had.
        if not restart_otel_span_processors():
            initialize_tracer(settings)
        await init_cache(settings)
        init_pandas()

    return start_app


def create_stop_app_handler(
    app: FastAPI,
    settings: AppSettings,
) -> Callable:  # type: ignore
    @logger.catch
    async def stop_app() -> None:
        await clear_cache(settings)

    return stop_app
