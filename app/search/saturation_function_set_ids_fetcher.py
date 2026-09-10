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
from app.models.schemas.search_scope import SearchScope
from app.resources.paths import SATURATION_FUNCTION_SET_STR
from app.search.ddms_dataset_ids_fetcher import (
    DDMSDatasetIdsFetcher,
    build_indexed_date_clauses,
    build_result_ids,
)
from app.search.pending_writes import supplement_with_pending_writes
from app.search.scope import (
    SCOPE_PROFILE_SATURATION_FUNCTION_SET,
    build_search_scope_clauses,
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
        scope = SearchScope(**wks_parameters) if wks_parameters else None
        query = self._build_query(
            data_partition_id,
            query_date_range[0],
            query_date_range[1],
            scope,
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
            logger.debug(f"SaturationFunctionSet search response: {search_response}")

            records = search_response.get("results", [])
            if not records:
                break

            result_records.extend(records)

            cursor = search_response.get("cursor")
            if not cursor:
                break

        result_ids = build_result_ids(
            result_records,
            target_schema_version,
            SATURATION_FUNCTION_SET_STR,
            content_type,
        )
        return await supplement_with_pending_writes(
            result_ids=result_ids,
            data_partition_id=data_partition_id,
            analysis_family=SATURATION_FUNCTION_SET_STR,
            analysis_type=content_type,
            target_schema_version=target_schema_version,
            scope=scope.to_query_dict() if scope else None,
        )

    def _build_query(
        self,
        data_partition_id: str,
        indexed_start_date: date,
        indexed_end_date: date,
        scope: Optional[SearchScope] = None,
    ) -> str:
        """Build a query to be used within search service."""
        logger.debug(f"Unused params {data_partition_id}")

        query_parts = []
        if scope:
            # Use saturation_function_set profile which supports basin_id and field_id only.
            query_parts.extend(
                build_search_scope_clauses(
                    scope,
                    scope_profile=SCOPE_PROFILE_SATURATION_FUNCTION_SET,
                )
            )
        query_parts.extend(
            build_indexed_date_clauses(indexed_start_date, indexed_end_date),
        )
        query = " AND ".join(query_parts)
        logger.debug(f"Query for search service: {query}")
        return query
