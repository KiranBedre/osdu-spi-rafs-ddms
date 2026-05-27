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

import json
from datetime import date
from typing import List, Optional, Tuple

from loguru import logger
from redis.asyncio.client import Redis
from redis.commands.search.query import Query as RedisQuery

from app.api.routes.utils.search import get_valid_ids_from_ddms_datasets
from app.dev.core.helpers.redis_index import SAMPLESANALYSIS_IX
from app.resources.paths import SAMPLESANALYSIS_TYPE_MAPPING
from app.search.ddms_dataset_ids_fetcher import DDMSDatasetIdsFetcher
from app.services import entitlements


class RedisSamplesAnalysisTypeIdsFetcher(DDMSDatasetIdsFetcher):

    def __init__(self, redis_client: Redis, entitlements_service: entitlements.EntitlementsService):
        self._redis_client = redis_client
        self._entitlements_service = entitlements_service

    async def get_ids(
        self,
        data_partition_id: str,
        analysis_type: str,
        target_schema_version: str,
        query_date_range: Tuple[date, date] = (None, None),
        wks_parameters: Optional[dict] = None,
    ) -> List[Tuple[str, str]]:
        """Performs a query to get a list of tuples (dataset_id,
        sample_analys_id)

        :param data_partition_id: data partition id
        :type data_partition_id: str
        :param analysis_type: analysis type as per rafsddms
        :type analysis_type: str
        :param target_schema_version: target schema version
        :type target_schema_version: str
        :param wks_parameters: a dictionary with search params, defaults
            to None
        :type wks_parameters: Optional[dict], optional
        :return: a list of tuple id records that matches the analysis
            type and wks_parameters
        :rtype: List[Tuple[str, str]]
        """
        index_name = SAMPLESANALYSIS_IX.format(partition=data_partition_id)
        data_acl_groups = await self._entitlements_service.get_data_groups()

        query = self._build_sampleanalysis_query(
            data_partition_id,
            SAMPLESANALYSIS_TYPE_MAPPING[analysis_type],
            wks_parameters,
        )

        query_offset = 0
        query_limit = 1000
        result_records = []
        while True:
            records_response = await self._redis_client.ft(index_name).search(
                RedisQuery(query).paging(query_offset, query_limit),
            )
            records = [json.loads(record.json) for record in records_response.docs]

            if not records:
                break
            result_records.extend(self._validate_acl(records, data_acl_groups))
            query_offset += query_limit

        return self._build_result_ids(result_records, target_schema_version, analysis_type)

    def _validate_acl(self, records: list, data_acl_groups: list) -> list:
        """Validates records against acl groups."""

        def verify_acl(record: dict, acls: set) -> bool:
            record_owners = set(record["ACLOwners"].split(","))
            record_viewers = set(record["ACLViewers"].split(","))
            return acls.intersection(record_owners) or acls.intersection(record_viewers)

        return [record for record in records if verify_acl(record, set(data_acl_groups))]

    def _build_sampleanalysis_query(
        self,
        data_partition_id: str,
        analysis_types: List[str],
        wks_parameters: Optional[dict] = None,
    ) -> str:
        """Build a query to be used within search service for
        SamplesAnalysisType."""
        sampleanalysistype_str = "reference-data--SampleAnalysisType"
        osdu_analysis_types = [
            self._prepare_redis_str(f"{data_partition_id}:{sampleanalysistype_str}:{analysis_type}")
            for analysis_type in analysis_types
        ]
        sampleanalysistype_ids_str = "|".join(osdu_analysis_types)
        query = [f"@SampleAnalysisTypeIDs:{{{sampleanalysistype_ids_str}}}"]

        if wks_parameters:
            for prop_name, prop_value in wks_parameters.items():
                if isinstance(prop_value, list):
                    prop_value = "|".join(prop_value)
                prop_value = self._prepare_redis_str(prop_value)
                query.append(f"+@{prop_name}:{{{prop_value}}}")

        logger.debug("Redis query:")
        logger.debug(query)
        return " ".join(query)

    def _build_result_ids(  # noqa: CCR001
        self,
        result_records: list,
        target_schema_version: str,
        analysis_type: str,
    ) -> List[Tuple[str, str]]:
        """Build a list of tuples content_id, samples_analysis_id."""
        result_ids = []
        for record in result_records:
            if ddms_datasets := record.get("DDMSDatasets", ""):  # noqa: WPS332
                ddms_datasets = ddms_datasets.split(",")
                result_ids.extend(
                    get_valid_ids_from_ddms_datasets(
                        ddms_datasets=ddms_datasets,
                        analysis_family="samplesanalysis",
                        analysis_type=analysis_type,
                        target_schema_version=target_schema_version,
                    ),
                )

        return result_ids

    def _prepare_redis_str(self, query_str):
        return query_str.replace(":", r"\:").replace("-", r"\-").replace(".", r"\.")  # noqa: W605
