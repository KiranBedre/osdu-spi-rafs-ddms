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

from fastapi import Depends
from loguru import logger

from app.api.dependencies.request import require_data_partition_id
from app.core.config import get_app_settings
from app.core.settings.app import AppSettings
from app.dev.core.helpers.redis_index import init_samplesanalysis_index


async def init_index(
    settings: AppSettings = Depends(get_app_settings),
    partition: str = Depends(require_data_partition_id),
) -> bool:
    if settings.redis_index_enable:
        logger.debug(f"Initializing Redis index for partition: {partition}")
        await init_samplesanalysis_index(partition)
    else:
        logger.debug("Redis index disabled")
    return bool(settings.redis_index_enable)
