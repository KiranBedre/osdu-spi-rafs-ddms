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
from typing import List

from fastapi import APIRouter, Depends
from loguru import logger
from redis.commands.json.path import Path
from starlette import status

from app.api.dependencies.services import (
    get_async_search_service,
    get_async_storage_service,
)
from app.api.routes.utils.records import get_id
from app.dev.api.dependencies.index import init_index
from app.dev.api.dependencies.validation import get_validated_partition
from app.dev.core.helpers.redis_index import (
    SAMPLESANALYSIS_IX_PREFIX,
    get_redis_client,
)
from app.models.domain.osdu.base import SAMPLESANALYSIS_KIND
from app.services import search, storage


class RedisIndexView:

    def __init__(
        self,
        router: APIRouter,
    ) -> None:
        self._router = router
        self._prepare_api_routes()

    async def index_records(
        self,
        index_initialized: bool = Depends(init_index),
        partition: str = Depends(get_validated_partition),
        search_service: search.SearchService = Depends(get_async_search_service),
        storage_service: storage.StorageService = Depends(get_async_storage_service),
    ) -> str:
        """_summary_

        :param index_initialized: _description_, defaults to
            Depends(init_index)
        :type index_initialized: bool, optional
        :param partition: _description_, defaults to
            Depends(get_validated_partition)
        :type partition: str, optional
        :param search_service: _description_, defaults to
            Depends(get_async_search_service)
        :type search_service: search.SearchService, optional
        :param storage_service: _description_, defaults to
            Depends(get_async_storage_service)
        :type storage_service: storage.StorageService, optional
        :return: _description_
        :rtype: str
        """
        records_processed = 0
        tasks = []

        if not index_initialized:
            return "Feature not available"

        async for samplesanalyses_batch in self._get_samplesanalysis_records(search_service):
            for samplesanalysis_record in samplesanalyses_batch:
                sa_record_id = samplesanalysis_record.get("id")
                records_processed += 1

                record_to_index = {
                    "SamplesAnalysisID": sa_record_id,
                    "ACLViewers": ",".join(samplesanalysis_record.get("acl", {}).get("viewers", [""])),
                    "ACLOwners": ",".join(samplesanalysis_record.get("acl", {}).get("owners", [""])),
                    "DDMSDatasets": ",".join(samplesanalysis_record.get("data", {}).get("DDMSDatasets", [])),
                    "ParentSamplesAnalysesReports": ",".join([
                        get_id(sar.get("ParentSamplesAnalysesReportID", ""))
                        for sar in samplesanalysis_record.get("data", {}).get("ParentSamplesAnalysesReports", [])
                    ]),
                    "SampleAnalysisTypeIDs": ",".join([
                        get_id(sat_id)
                        for sat_id in samplesanalysis_record.get("data", {}).get("SampleAnalysisTypeIDs", [])
                    ]),
                    "SampleIDs": ",".join([
                        get_id(sample_id)
                        for sample_id in samplesanalysis_record.get("data", {}).get("SampleIDs", [])
                    ]),
                }

                sample_ids = record_to_index["SampleIDs"].split(",")
                tasks.append(
                    self._process_sample_ids(
                        sample_ids, storage_service, sa_record_id, record_to_index, partition,
                    ),
                )

        await asyncio.gather(*tasks)
        return f"{records_processed} samples analysis records processed."

    async def _process_sample_ids(  # noqa: CCR001
        self,
        sample_ids: List[str],
        storage_service: storage.StorageService,
        record_id: str,
        record_to_index: dict,
        partition: str,
    ) -> None:
        samples_response = await storage_service.query_records(sample_ids)

        sample_type_ids, basin_ids, field_ids, wellbore_ids = [], [], [], []

        for sample_record in samples_response["records"]:
            sample_record_data = sample_record.get("data", {})

            if sample_record_data.get("SampleTypeID"):
                sample_type_ids.append(get_id(sample_record_data.get("SampleTypeID")))

            for geo_ctx in sample_record_data.get("GeoContexts", []):
                if geo_ctx.get("BasinID"):
                    basin_ids.append(get_id(geo_ctx.get("BasinID")))
                if geo_ctx.get("FieldID"):
                    field_ids.append(get_id(geo_ctx.get("FieldID")))

            wellbore_id = sample_record_data.get("SampleAcquisition", {}).get(
                "SampleAcquisitionDetail", {},
            ).get("WellboreID", "")
            if wellbore_id:
                wellbore_ids.append(get_id(wellbore_id))

        record_to_index["SampleTypeIds"] = ",".join(sample_type_ids)
        record_to_index["WellboreIDs"] = ",".join(wellbore_ids)
        record_to_index["BasinIDs"] = ",".join(basin_ids)
        record_to_index["FieldIDs"] = ",".join(field_ids)

        tasks = [
            self._get_alias_names(wellbore_ids, storage_service, "WellboreNames", record_to_index),
            self._get_alias_names(basin_ids, storage_service, "BasinNames", record_to_index),
            self._get_alias_names(field_ids, storage_service, "FieldNames", record_to_index),
        ]
        await asyncio.gather(*tasks)

        logger.debug(record_to_index)
        prefix = SAMPLESANALYSIS_IX_PREFIX.format(partition=partition)
        key = f"{prefix}{record_id}"
        redis_client = await get_redis_client()
        await redis_client.json().set(key, Path.root_path(), record_to_index)

    async def _get_alias_names(
        self,
        query_ids: List[str],
        storage_service: storage.StorageService,
        field_name: str,
        record_to_index: dict,
    ) -> None:
        if query_ids:
            records_response = await storage_service.query_records(query_ids)
            alias_names = [
                alias_name.get("AliasName") for record in records_response.get("records", [])
                for alias_name in record.get("data", {}).get("NameAliases", [])  # noqa: WPS361
                if alias_name.get("AliasName")
            ]
            record_to_index[field_name] = ",".join(alias_names)

    async def _get_samplesanalysis_records(
        self,
        search_service: search.SearchService,
    ):
        query_offset = 0
        while True:
            search_response = await search_service.find_records(
                kind=SAMPLESANALYSIS_KIND,
                offset=query_offset,
                limit=search.QUERY_LIMIT,
            )
            records = search_response.get("results", [])
            if not records:
                break
            yield records
            query_offset += search.QUERY_LIMIT

    def _prepare_api_routes(self) -> None:
        """Prepare and add api routes."""
        self._prepare_records_index_route()

    def _prepare_records_index_route(self) -> None:
        self._router.add_api_route(
            path="/sa_records_index",
            endpoint=self.index_records,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
        )
