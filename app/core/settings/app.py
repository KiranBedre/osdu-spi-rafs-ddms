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

import logging
from typing import Any, Dict, List, Tuple

from loguru import logger

from app.core.helpers.app_filter_logging import AppFilterLogging
from app.core.logging import InterceptHandler
from app.core.settings.base import BaseAppSettings


class AppSettings(BaseAppSettings):
    debug: bool = False

    app_name: str = "Rock and Fluid Sample DDMS"

    app_version: str = "0.2.0"

    ddms_id: str = "rafs"

    openapi_prefix: str = "/api/os-rafs-ddms"

    allowed_hosts: List[str] = ["*"]

    logging_level: int = logging.INFO

    loggers: Tuple[str, str, str] = (
        "uvicorn.asgi",
        "uvicorn.access",
        "uvicorn.error",
    )

    service_host_search: str = None

    service_host_storage: str = None

    service_host_entitlements: str = None

    service_host_dataset: str = None

    service_host_schema: str = None

    service_host_partition: str = None

    user_token: str = None

    cache_enable: bool = False

    cache_backend: str = ""

    storage_query_limit: int = 100

    service_readiness_urls: str = None

    redis_index_enable: bool = False

    @property
    def fastapi_kwargs(self) -> Dict[str, Any]:
        return {
            "debug": self.debug,
            "title": self.app_name,
            "version": self.app_version,
            "openapi_url": f"{self.openapi_prefix}/openapi.json",
            "docs_url": f"{self.openapi_prefix}/docs",
            "redoc_url": f"{self.openapi_prefix}/redoc",
            "description": "OSDU Rock and Fluid Sample DDMS",
            "license_info": {
                "name": "Apache 2.0",
                "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
            },
        }

    def configure_logging(self) -> None:
        logging.getLogger().handlers = [InterceptHandler()]
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level=self.logging_level)
        console_handler.addFilter(AppFilterLogging())
        formatter = logging.Formatter(
            "%(asctime)s [%(process)d][%(levelname)s] --- {correlation-id=%(correlation_id)s} %(name)s: %(message)s",
        )
        console_handler.setFormatter(formatter)

        for logger_name in self.loggers:
            logging_logger = logging.getLogger(logger_name)
            logging_logger.handlers.clear()
            logging_logger.propagate = False
            logging_logger.addHandler(console_handler)

        logger.remove()
        logger.add(
            console_handler,
            level=self.logging_level,
            filter=AppFilterLogging,
            format="{message}",
        )
