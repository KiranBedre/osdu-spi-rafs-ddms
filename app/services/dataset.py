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

import asyncio
import sys
from typing import List, Optional, Tuple

from fastapi_cache.decorator import cache
from loguru import logger
from starlette import status

from app.core.helpers.cache.key_builder import key_builder_for_service_methods
from app.core.helpers.cache.settings import CACHE_DEFAULT_TTL
from app.core.settings.app import AppSettings
from app.models.schemas.user import User
from app.providers.dependencies.blob_loader import IBlobLoader, get_blob_loader
from app.services.base import IDatasetService
from app.services.error_handlers import handle_core_services_http_status_error
from app.services.osdu_clients.dataset_client import DatasetServiceApiClient
from app.services.utils.dataset import create_default_dataset_record


class DatasetService(IDatasetService):

    def __init__(
        self,
        data_partition_id: str,
        settings: AppSettings,
        user: User,
        extra_headers: dict,
    ) -> None:
        self.schema_authority = settings.schema_authority
        self.dataset_client = DatasetServiceApiClient(
            settings.service_host_dataset,
            data_partition_id=data_partition_id,
            bearer_token=user.access_token,
            extra_headers=extra_headers,
        )
        self.blob_loader: Optional[IBlobLoader] = get_blob_loader(settings)
        self.name = "DatasetService"

    async def download_file(self, dataset_id: str) -> Optional[bytes]:
        """Download file.

        :param dataset_id: dataset id
        :type dataset_id: str
        :return: file content
        :rtype: Optional[bytes]
        """
        retrieval_instruction = await self.dataset_client.get_retrieval_instructions(dataset_id)
        if not retrieval_instruction.get("datasets"):
            logger.debug(
                f"{self.name}: blob hasn't been downloaded due to improper retrieval instructions for: {dataset_id}.",
            )
            return None

        signed_url = retrieval_instruction["datasets"][0]["retrievalProperties"]["signedUrl"]

        blob = await self.blob_loader.download_blob(signed_url)
        logger.debug(f"{self.name}: blob has been downloaded for: {dataset_id}")
        return blob

    async def upload_file(
        self,
        blob_file: bytes,
        dataset_id: str,
        parent_record: dict,
    ) -> str:
        """Upload file.

        :param blob_file: blob file
        :type blob_file: bytes
        :param dataset_id: dataset id
        :type dataset_id: str
        :param parent_record: parent record
        :type parent_record: dict
        :return: stored dataset id and version
        :rtype: str
        """
        storage_instruction = await self.dataset_client.storage_instructions(
            kind_subtype="dataset--File.Generic",
        )
        signed_url = storage_instruction["storageLocation"]["signedUrl"]
        file_source = storage_instruction["storageLocation"]["fileSource"]

        await self.blob_loader.upload_blob(signed_url, blob_file)

        record_list = [
            create_default_dataset_record(
                dataset_id,
                file_source,
                str(sys.getsizeof(blob_file)),
                parent_record,
                self.schema_authority,
            ),
        ]
        registered_dataset = await self.dataset_client.create_or_update_dataset_registry(dataset_registries=record_list)

        stored_dataset = registered_dataset["datasetRegistries"][0]
        return f'{stored_dataset["id"]}:{stored_dataset["version"]}'

    @handle_core_services_http_status_error(
        expected_codes=[
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ],
        detail="Failed to get signed urls using DatasetService.",
    )
    @cache(expire=CACHE_DEFAULT_TTL, key_builder=key_builder_for_service_methods)
    async def get_signed_urls(self, dataset_ids: List[str]) -> List[Tuple[str, str]]:  # noqa: ASYNC910
        """Get a signed url per dataset id for a list of dataset_ids.

        :param dataset_ids: list of dataset ids
        :type dataset_ids: List[str]
        :raises exc: if dataset service raises error
        :return: a list of pairs dataset_id, signed_url
        :rtype: List[Tuple[str, str]]
        """
        max_ids_per_request = 20
        id_chunks = [
            dataset_ids[ix : ix + max_ids_per_request] for ix in range(0, len(dataset_ids), max_ids_per_request)
        ]
        tasks = []
        try:
            async with asyncio.TaskGroup() as group:
                for id_chunk in id_chunks:
                    tasks.append(group.create_task(self._request_signed_urls(id_chunk)))
        except ExceptionGroup as eg:
            for exc in eg.exceptions:  # noqa: WPS328, ASYNC123 pylint: disable=not-an-iterable
                raise exc  # noqa: ASYNC123

        signed_urls = []
        for task in tasks:
            signed_urls.extend(task.result())
        return signed_urls  # noqa: ASYNC910

    async def _request_signed_urls(self, dataset_ids: List[str]) -> List[Tuple[str, str]]:
        """Performs the actual dataset request to fetch signed urls.

        :param dataset_ids: the list of dataset ids
        :type dataset_ids: List[str]
        :return: a list of pairs dataset_id, signed_url
        :rtype: List[Tuple[str, str]]
        """
        retrieval_instructions = await self.dataset_client.retrieval_instructions(dataset_ids)
        signed_urls = []
        for dataset in retrieval_instructions["datasets"]:
            signed_urls.append((dataset["datasetRegistryId"], dataset["retrievalProperties"]["signedUrl"]))
        return signed_urls  # noqa: ASYNC910
