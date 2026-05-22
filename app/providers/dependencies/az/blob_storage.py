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

from typing import List

from azure.core.exceptions import (  # pylint: disable=no-name-in-module
    HttpResponseError,
    ResourceExistsError,
    ResourceModifiedError,
    ResourceNotFoundError,
    ServiceRequestError,
    ServiceResponseError,
)
from azure.identity.aio import DefaultAzureCredential  # pylint: disable=no-name-in-module
from azure.storage.blob import BlobType, ContentSettings  # pylint: disable=no-name-in-module
from azure.storage.blob.aio import BlobServiceClient  # pylint: disable=no-name-in-module
from loguru import logger

from app.exceptions.exceptions import (
    NotFoundException,
    ServiceUnavailableException,
)
from app.providers.dependencies.az.storage_account_info import (
    STORAGE_ACCOUNT_BLOB_ENDPOINT,
)
from app.providers.dependencies.blob_storage import (
    Blob,
    BlobMetadata,
    IBlobStorage,
    StoragePartitionInfo,
)

ALL_AZURE_CORE_ERRORS = (
    HttpResponseError,
    ResourceModifiedError,
    ResourceExistsError,
    ResourceNotFoundError,
    ServiceRequestError,
    ServiceResponseError,
)


class AzureBlobStorage(IBlobStorage):

    def __init__(self, storage_partition_info: StoragePartitionInfo):
        self._account_url = storage_partition_info.storage_account_info[STORAGE_ACCOUNT_BLOB_ENDPOINT]
        self._container_name = storage_partition_info.storage_account_info["container_name"]
        self._credential = DefaultAzureCredential()

    async def create_blob(self, blob) -> BlobMetadata:
        return await self._upload_blob(blob)

    async def update_blob(self, blob: Blob):
        return await self._upload_blob(blob, overwrite=True)

    async def get_blob(self, blob_metadata: BlobMetadata) -> Blob:
        object_name = blob_metadata.object_name
        async with BlobServiceClient(
            account_url=self._account_url,
            credential=self._credential,
        ) as blob_service_client:
            container_client = blob_service_client.get_container_client(container=self._container_name)
            blob_client = container_client.get_blob_client(object_name)

            try:
                blob_metadata.metadata = await blob_client.get_blob_properties()
                blob_stream = await blob_client.download_blob()
                blob_data = await blob_stream.readall()
                return Blob(blob_data=blob_data, blob_metadata=blob_metadata)
            except (HttpResponseError, ResourceNotFoundError) as exc:
                exc_msg = str(exc)
                object_name = blob_metadata.object_name
                error_msg = f"Unable to get the blob {object_name}: {exc_msg}"
                logger.error(error_msg)
                raise NotFoundException(detail=error_msg)

    async def list_blobs(self, subpath: str) -> List[str]:
        async with BlobServiceClient(
            account_url=self._account_url,
            credential=self._credential,
        ) as blob_service_client:
            container_client = blob_service_client.get_container_client(container=self._container_name)

            blob_names = []
            async for blob in container_client.list_blobs(subpath):
                blob_names.append(blob["name"])

        return blob_names

    async def delete_blob(self, blob_metadata: BlobMetadata) -> bool:
        object_name = blob_metadata.object_name
        async with BlobServiceClient(
            account_url=self._account_url,
            credential=self._credential,
        ) as blob_service_client:
            container_client = blob_service_client.get_container_client(container=self._container_name)
            blob_client = container_client.get_blob_client(object_name)

            resource_deleted = False
            try:
                await blob_client.delete_blob()
                resource_deleted = True
            except ResourceNotFoundError:
                error_msg = f"Blob not found: {object_name}"
                logger.error(error_msg)
                raise NotFoundException(detail=error_msg)

        return resource_deleted

    async def _upload_blob(
        self,
        blob: Blob,
        overwrite: bool = False,
        blob_type: BlobType = BlobType.BLOCKBLOB,
    ) -> BlobMetadata:
        async with BlobServiceClient(
            account_url=self._account_url,
            credential=self._credential,
        ) as blob_service_client:
            container_client = blob_service_client.get_container_client(container=self._container_name)
            blob_client = container_client.get_blob_client(blob.blob_metadata.object_name)

            content_settings = ContentSettings(content_type=blob.blob_metadata.content_type.mime_type)
            try:
                blob.blob_metadata.metadata = await blob_client.upload_blob(
                    data=blob.blob_data,
                    metadata=blob.blob_metadata.metadata,
                    blob_type=blob_type,
                    overwrite=overwrite,
                    content_settings=content_settings,
                )
                return blob.blob_metadata
            except ALL_AZURE_CORE_ERRORS as exc:
                exc_msg = str(exc)
                error_msg = f"Azure Blob Storage upload failed: {exc_msg}"
                logger.error(error_msg)
                raise ServiceUnavailableException(detail=error_msg) from exc
