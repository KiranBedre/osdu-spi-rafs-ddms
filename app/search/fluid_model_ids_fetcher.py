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


from app.exceptions.exceptions import UnprocessableContentException
from app.models.domain.osdu.base import FLUID_MODEL_KIND_BASE
from app.models.schemas.search_scope import SearchScope
from app.resources.paths import FLUID_MODEL_STR, FLUID_MODEL_TYPE_MAPPING
from app.search.ddms_dataset_ids_fetcher import (
    DDMSDatasetIdsFetcher,
    build_result_ids,
)
from app.search.scope import (
    SCOPE_PROFILE_FLUID_MODEL,
    UnsupportedSearchScopeError,
    build_search_scope_clauses,
)
from app.services import search


class SearchServiceFluidModelIdsFetcher(DDMSDatasetIdsFetcher):

    def __init__(self, search_service: search.SearchService):
        self._search_service = search_service

    async def get_ids(
        self,
        data_partition_id: str,
        fluid_model_type: str,
        target_schema_version: str,
        query_date_range: Tuple[date, date],
        wks_parameters: Optional[dict] = None,
    ) -> List[Tuple[str, str]]:
        """Performs a query to search service to build a list of tuples
        dataset_id, fluid_model_id."""
        query = self._build_query(
            data_partition_id,
            FLUID_MODEL_TYPE_MAPPING[fluid_model_type],
            query_date_range[0],
            query_date_range[1],
            wks_parameters,
        )

        result_records = []
        cursor = None
        while True:
            search_response = await self._search_service.find_records(
                kind=f"{FLUID_MODEL_KIND_BASE}:*",
                query=query,
                limit=search.QUERY_LIMIT,
                cursor=cursor,
            )
            records = search_response.get("results", [])
            if not records:
                break

            result_records.extend(records)

            cursor = search_response.get("cursor", None)
            if not cursor:
                break

        return build_result_ids(
            result_records,
            target_schema_version,
            FLUID_MODEL_STR,
            fluid_model_type,
        )

    def _build_query(
        self,
        data_partition_id: str,
        fluid_model_type: str,
        indexed_start_date: date,
        indexed_end_date: date,
        wks_parameters: Optional[dict] = None,
    ) -> str:
        """Build a query to be used within search service."""

        fluid_model_type_id = f"{data_partition_id}:reference-data--FluidModelType:{fluid_model_type}:"
        query_parts = [
            f"data.FluidModelTypeID:\"{fluid_model_type_id}\"",
        ]
        if wks_parameters:
            try:
                query_parts.extend(
                    build_search_scope_clauses(
                        SearchScope(**wks_parameters),
                        scope_profile=SCOPE_PROFILE_FLUID_MODEL,
                        strict=True,
                    ),
                )
            except UnsupportedSearchScopeError as exc:
                raise UnprocessableContentException(detail=str(exc)) from exc
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
