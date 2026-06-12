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

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional, Tuple

from loguru import logger

from app.api.routes.utils.search import get_valid_ids_from_ddms_datasets
from app.models.domain.osdu.base import SAMPLESANALYSIS_KIND_BASE
from app.resources.paths import SAMPLESANALYSIS_TYPE_MAPPING
from app.services import search


class DDMSDatasetIdsFetcher(ABC):

    @abstractmethod
    async def get_ids(
        self,
        data_partition_id: str,
        content_type: str,
        target_schema_version: str,
        query_date_range: Tuple[date, date],
        wks_parameters: Optional[dict] = None,
    ) -> List[Tuple[str, str]]:
        raise NotImplementedError()


def build_result_ids(  # noqa: CCR001
    result_records: list,
    target_schema_version: str,
    domain: str,
    content_type: str,
) -> List[Tuple[str, str]]:
    """Build a list of tuples dataset_id, samples_analysis_id."""

    result_ids = []
    for record in result_records:
        if ddms_datasets := record.get("data", {}).get("DDMSDatasets"):  # noqa: WPS332
            logger.debug(f"ddms_datasets: {ddms_datasets}")
            result_ids.extend(
                get_valid_ids_from_ddms_datasets(
                    ddms_datasets=ddms_datasets,
                    analysis_family=domain,
                    analysis_type=content_type,
                    target_schema_version=target_schema_version,
                ),
            )
    logger.debug(f"Result_ids: {result_ids}")
    return result_ids


class SearchServiceSamplesAnalysisTypeIdsFetcher(DDMSDatasetIdsFetcher):

    def __init__(self, search_service: search.SearchService):
        self._search_service = search_service

    async def get_ids(
        self,
        data_partition_id: str,
        analysis_type: str,
        target_schema_version: str,
        query_date_range: Tuple[date, date],
        wks_parameters: Optional[dict] = None,
    ) -> List[Tuple[str, str]]:
        """Performs a query to search service to build a list of tuples
        dataset_id, samples_analysis_id."""
        query = self._build_sampleanalysistype_query(
            data_partition_id,
            SAMPLESANALYSIS_TYPE_MAPPING[analysis_type],
            query_date_range[0],
            query_date_range[1],
        )

        result_records = []
        cursor = None
        while True:
            search_response = await self._search_service.find_records(
                kind=f"{SAMPLESANALYSIS_KIND_BASE}:*",
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
            "samplesanalysis",
            analysis_type,
        )

    def _build_sampleanalysistype_query(
        self,
        data_partition_id: str,
        analysis_types: List[str],
        indexed_start_date: date,
        indexed_end_date: date,
    ) -> str:
        """Build a query to be used within search service for
        SamplesAnalysisType."""
        analysis_types = [
            f'"{data_partition_id}:reference-data--SampleAnalysisType:{analysis_type}"'
            for analysis_type in analysis_types
        ]
        analysis_types_str = " OR ".join(analysis_types)
        query_parts = [
            f"data.SampleAnalysisTypeIDs:({analysis_types_str})",
        ]
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
