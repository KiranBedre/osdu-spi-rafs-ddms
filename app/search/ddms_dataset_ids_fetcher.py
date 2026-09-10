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

import asyncio
import re
from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional, Tuple

from loguru import logger

from app.api.routes.utils.search import get_valid_ids_from_ddms_datasets
from app.models.domain.osdu.base import SAMPLE_KIND_BASE, SAMPLESANALYSIS_KIND_BASE, WELLBORE_KIND_BASE
from app.models.schemas.search_scope import SearchScope
from app.resources.paths import SAMPLESANALYSIS_TYPE_MAPPING
from app.search.pending_writes import supplement_with_pending_writes
from app.search.scope import (
    SAMPLE_HOP_SCOPE_KEYS,
    SCOPE_PROFILE_SAMPLE,
    build_search_scope_clauses,
)
from app.search.scope import escape_query_value as _escape_query_value
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


def build_indexed_date_clauses(
    indexed_start_date: Optional[date],
    indexed_end_date: Optional[date],
) -> List[str]:
    """Build an inclusive UTC indexing-date range clause."""
    if not indexed_start_date and not indexed_end_date:
        return []

    start = f'"{indexed_start_date.isoformat()}T00:00:00.000Z"' if indexed_start_date else "*"
    end = f'"{indexed_end_date.isoformat()}T23:59:59.999Z"' if indexed_end_date else "*"

    return [f"index.lastUpdateTime:[{start} TO {end}]"]


class SearchServiceSamplesAnalysisTypeIdsFetcher(DDMSDatasetIdsFetcher):

    def __init__(self, search_service: search.SearchService):
        self._search_service = search_service

    async def get_ids(  # noqa: CCR001
        self,
        data_partition_id: str,
        analysis_type: str,
        target_schema_version: str,
        query_date_range: Tuple[date, date],
        wks_parameters: Optional[dict] = None,
    ) -> List[Tuple[str, str]]:
        """Performs a query to search service to build a list of tuples
        dataset_id, samples_analysis_id."""
        scope = SearchScope(**wks_parameters) if wks_parameters else None

        # Resolve Sample IDs via hops when basin/field/wellbore/well scope is requested.
        # Those fields live on Sample and Wellbore master-data, not on SamplesAnalysis records.
        sample_id_filter: Optional[List[str]] = None
        if scope and any(getattr(scope, scope_key) for scope_key in SAMPLE_HOP_SCOPE_KEYS):
            sample_id_filter = await self._resolve_sample_ids_by_scope(scope)
            if not sample_id_filter:
                logger.debug("No Sample records matched the scope filter; returning empty result.")
                return []

        query = self._build_sampleanalysistype_query(
            data_partition_id,
            SAMPLESANALYSIS_TYPE_MAPPING[analysis_type],
            query_date_range[0],
            query_date_range[1],
            sample_id_filter=sample_id_filter,
        )

        logger.debug("Executing search query for SamplesAnalysis with query: {0}".format(query))

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

        result_ids = build_result_ids(
            result_records,
            target_schema_version,
            "samplesanalysis",
            analysis_type,
        )
        return await supplement_with_pending_writes(
            result_ids=result_ids,
            data_partition_id=data_partition_id,
            analysis_family="samplesanalysis",
            analysis_type=analysis_type,
            target_schema_version=target_schema_version,
            scope=scope.to_query_dict() if scope else None,
            query_date_range=query_date_range,
        )

    async def _resolve_sample_ids_by_scope(self, scope: SearchScope) -> List[str]:  # noqa: CFQ004
        """Resolve sample IDs via Wellbore hop (if well_id) and then Sample hop.

        When well_id is provided, performs 3-hop resolution:
        1. Query Wellbore with well_id → Get wellbore IDs
        2. Query Sample with wellbore IDs → Get sample IDs
        3. Filter SamplesAnalysis by sample IDs (caller's responsibility)

        When basin/field/wellbore scope is provided, performs 2-hop resolution:
        1. Query Sample with scope → Get sample IDs
        2. Filter SamplesAnalysis by sample IDs (caller's responsibility)
        """
        # Resolve well_id to wellbore IDs first (hop 0)
        if scope.well_id:
            wellbore_ids = await self._resolve_wellbore_ids_by_well(scope.well_id)
            if not wellbore_ids:
                logger.debug("No Wellbore records matched the well_id filter; returning empty.")
                return []
            sample_ids = await self._resolve_sample_ids_for_wellbores(wellbore_ids)
            logger.debug("Well-hop + Sample-hop resolved {0} sample IDs for well_id scope.", len(sample_ids))
            return sample_ids

        # Standard 2-hop for basin/field/wellbore (Hop 1: query Sample master-data)
        scope_clauses = build_search_scope_clauses(scope, scope_profile=SCOPE_PROFILE_SAMPLE)
        query = " AND ".join(scope_clauses) if scope_clauses else "*"
        sample_ids = await self._resolve_sample_ids_for_query(query)
        logger.debug("Sample-hop resolved {0} sample IDs for scope.", len(sample_ids))
        return sample_ids

    async def _resolve_sample_ids_for_wellbores(self, wellbore_ids: List[str]) -> List[str]:
        wellbore_queries = [
            " AND ".join(
                build_search_scope_clauses(
                    SearchScope(wellbore_id=wellbore_id),
                    scope_profile=SCOPE_PROFILE_SAMPLE,
                ),
            )
            for wellbore_id in wellbore_ids
        ]
        sample_id_groups = await asyncio.gather(
            *(self._resolve_sample_ids_for_query(query) for query in wellbore_queries),
        )
        return [sample_id for sample_ids in sample_id_groups for sample_id in sample_ids]

    async def _resolve_sample_ids_for_query(self, query: str) -> List[str]:
        return await self._query_ids_by_kind(f"{SAMPLE_KIND_BASE}:*", query)

    async def _query_ids_by_kind(self, kind: str, query: str) -> List[str]:
        record_ids: List[str] = []
        cursor = None
        while True:
            response = await self._search_service.find_records(
                kind=kind,
                query=query,
                limit=search.QUERY_LIMIT,
                cursor=cursor,
                returnedFields=["id"],
            )
            records = response.get("results", [])
            cursor = response.get("cursor", None)
            record_ids.extend(record["id"] for record in records if record.get("id"))
            if not records:
                break
        return record_ids

    async def _resolve_wellbore_ids_by_well(self, well_id: str) -> List[str]:
        """Query Wellbore master-data to find IDs matching the given well_id (hop 0 for well_id scope)."""
        escaped_well_id = _escape_query_value(well_id)
        query = f'data.WellID:"{escaped_well_id}"'
        wellbore_ids: List[str] = []
        cursor = None
        while True:
            response = await self._search_service.find_records(
                kind=f"{WELLBORE_KIND_BASE}:*",
                query=query,
                limit=search.QUERY_LIMIT,
                cursor=cursor,
                returnedFields=["id"],
            )
            records = response.get("results", [])
            cursor = response.get("cursor", None)
            wellbore_ids.extend(record["id"] for record in records if record.get("id"))
            if not records:
                break
        logger.debug("Wellbore-hop resolved {0} wellbore IDs for well_id scope.", len(wellbore_ids))
        return wellbore_ids

    def _build_sampleanalysistype_query(
        self,
        data_partition_id: str,
        analysis_types: List[str],
        indexed_start_date: date,
        indexed_end_date: date,
        sample_id_filter: Optional[List[str]] = None,
    ) -> str:
        """Build a query to be used within search service for
        SamplesAnalysisType."""
        analysis_type_variants: List[str] = []
        for analysis_type in analysis_types:
            analysis_type_id = f"{data_partition_id}:reference-data--SampleAnalysisType:{analysis_type}"
            analysis_type_variants.extend(self._expand_id_variants(analysis_type_id))
        analysis_types_str = " OR ".join(  # noqa: WPS237
            '"{0}"'.format(_escape_query_value(at_id)) for at_id in _dedupe_preserve_order(analysis_type_variants)
        )
        query_parts = [
            f"data.SampleAnalysisTypeIDs:({analysis_types_str})",
        ]
        if sample_id_filter:
            # Hop 2: restrict to SamplesAnalysis records that reference the resolved sample IDs.
            sample_id_variants: List[str] = []
            for sample_id in sample_id_filter:
                sample_id_variants.extend(self._expand_id_variants(sample_id))
            escaped_sample_ids = [_escape_query_value(sid) for sid in _dedupe_preserve_order(sample_id_variants)]
            sample_ids_str = " OR ".join(f'"{sid}"' for sid in escaped_sample_ids)
            query_parts.append(f"data.SampleIDs:({sample_ids_str})")

        query_parts.extend(
            build_indexed_date_clauses(indexed_start_date, indexed_end_date),
        )
        query = " AND ".join(query_parts)
        logger.debug("Query for search service: {0}", query)
        return query

    @staticmethod
    def _expand_id_variants(record_id: str) -> List[str]:  # noqa: CFQ004
        """Return equivalent ID forms used across RAFS/Storage payloads.

        Includes plain ID, latest ref (`<id>:`), and numeric-version variants.
        """
        if not record_id:
            return []

        variants: List[str] = [record_id]
        if record_id.endswith(":"):
            variants.append(record_id[:-1])
            return _dedupe_preserve_order(variants)

        version_match = re.match(r"^(.*):(\d+)$", record_id)
        if version_match:
            base_id = version_match.group(1)
            variants.extend([base_id, f"{base_id}:"])
            return _dedupe_preserve_order(variants)

        variants.append(f"{record_id}:")
        return _dedupe_preserve_order(variants)


def _dedupe_preserve_order(values: List[str]) -> List[str]:  # noqa: WPS110
    """De-duplicate while preserving insertion order."""
    return list(dict.fromkeys(values))
