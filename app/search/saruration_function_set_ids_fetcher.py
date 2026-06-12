#  Copyright 2025 ExxonMobil Technology and Engineering Company
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

from datetime import date
from typing import List, Optional, Tuple

from loguru import logger

from app.models.domain.osdu.base import SATURATION_FUNCTION_SET_KIND_BASE
from app.resources.paths import SATURATION_FUNCTION_SET_STR
from app.search.ddms_dataset_ids_fetcher import (
    DDMSDatasetIdsFetcher,
    build_result_ids,
)
from app.services import search


class SearchServiceSaturationFunctionSetIdsFetcher(DDMSDatasetIdsFetcher):

    def __init__(self, search_service: search.SearchService):
        self._search_service = search_service

    async def get_ids(
        self,
        data_partition_id: str,
        content_type: str,
        target_schema_version: str,
        query_date_range: Tuple[date, date],
        wks_parameters: Optional[dict] = None,
    ) -> List[Tuple[str, str]]:
        """Performs a query to search service to build a list of tuples
        dataset_id, samples_analysis_id."""
        query = self._build_query(
            data_partition_id,
            query_date_range[0],
            query_date_range[1],
            wks_parameters,
        )

        result_records = []
        cursor = None
        while True:
            search_response = await self._search_service.find_records(
                kind=f"{SATURATION_FUNCTION_SET_KIND_BASE}:*",
                query=query,
                limit=search.QUERY_LIMIT,
                cursor=cursor,
            )
            records = search_response.get("results", [])
            cursor = search_response.get("cursor", None)
            if not records:
                break
            result_records.extend(records)

        return build_result_ids(
            result_records,
            target_schema_version,
            SATURATION_FUNCTION_SET_STR,
            content_type,
        )

    def _build_query(
        self,
        data_partition_id: str,
        indexed_start_date: date,
        indexed_end_date: date,
        wks_parameters: Optional[dict] = None,
    ) -> str:
        """Build a query to be used within search service."""
        logger.debug(f"Unused params {data_partition_id}, {wks_parameters}")

        query_parts = []
        # Append time filters based on start and end dates
        if indexed_start_date and indexed_end_date:
            query_parts.append(
                f"index.lastUpdateTime:[{indexed_start_date.isoformat()} TO {indexed_end_date.isoformat()}]",
            )
        elif indexed_start_date:
            query_parts.append(
                f"index.lastUpdateTime:[{indexed_start_date.isoformat()} TO *]",
            )
        elif indexed_end_date:
            query_parts.append(
                f"index.lastUpdateTime:[* TO {indexed_end_date.isoformat()}]",
            )
        query = " AND ".join(query_parts)
        logger.debug(f"Query for search service: {query}")
        return query
