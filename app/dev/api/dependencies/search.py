#  Copyright 2024 ExxonMobil Technology and Engineering Company
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
from app.api.dependencies.services import get_async_search_service
from app.core.config import get_app_settings
from app.dev.api.dependencies.services import get_async_entitlements_service
from app.dev.core.helpers.redis_index import (
    SAMPLESANALYSIS_IX,
    get_redis_client,
    is_index_initialized,
)
from app.dev.search.analysis_type_ids_fetcher import (
    AnalysisTypeIdsFetcher,
    OsduAnalysisTypeIdsFetcher,
    RedisAnalysisTypeIdsFetcher,
)
from app.dev.services import entitlements
from app.services import search


async def get_analysis_type_ids_fetcher(
    search_service: search.SearchService = Depends(get_async_search_service),
    partition: str = Depends(require_data_partition_id),
    entitlements_service: entitlements.EntitlementsService = Depends(get_async_entitlements_service),
) -> AnalysisTypeIdsFetcher:
    is_index_initialized_flag = await is_index_initialized(SAMPLESANALYSIS_IX.format(partition=partition))
    if get_app_settings().redis_index_enable and is_index_initialized_flag:
        logger.info("Using redis index to fetch ids")
        fetcher = RedisAnalysisTypeIdsFetcher(await get_redis_client(), entitlements_service)
    else:
        logger.info("Using search service to fetch ids")
        fetcher = OsduAnalysisTypeIdsFetcher(search_service)
    return fetcher
