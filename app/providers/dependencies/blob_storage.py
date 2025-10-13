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

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiofiles
from pydantic import BaseSettings

from app.core.settings.app import AppSettings
from app.exceptions.exceptions import (
    NotFoundException,
    UnprocessableContentException,
)
from app.resources.mime_types import MimeType


@dataclass
class BlobMetadata(object):
    analysis_family: str
    analysis_type: str
    version: str
    uuid: str
    content_type: MimeType
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not all([self.analysis_family, self.analysis_type, self.version, self.uuid, self.content_type]):
            raise ValueError(
                "analysis_famuly, analysis_type, version, uuid, and content_type must be non-empty strings.",
            )

    @property
    def object_name(self) -> str:
        return f"{self.analysis_family}/{self.analysis_type}/{self.version}/{self.uuid}"

    @property
    def full_analysis_type(self) -> str:
        return f"{self.analysis_family}/{self.analysis_type}/{self.version}"


@dataclass
class Blob(object):
    blob_data: bytes
    blob_metadata: BlobMetadata


@dataclass
class StoragePartitionInfo(object):
    data_partition_id: str
    storage_account_info: Dict[str, Any]


class IBlobStorage(ABC):
    """Abstract class for cloud storage backends."""

    @abstractmethod
    async def create_blob(
        self,
        blob: Blob,
    ) -> BlobMetadata:
        """Create the blob in the storage backend.

        :param blob: the blob to upload
        :type blob: Blob
        :raises UnprocessableContentException: when unable to create the
            blob
        :return: the uploaded blob metadata
        :rtype: BlobMetadata
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_blob(
        self,
        blob_metadata: BlobMetadata,
    ) -> bool:
        """Deletes the blob with given metadata.

        :param blob_metadata: the blob metadata
        :type blob_metadata: BlobMetadata
        :raises NotFoundException: when blob is not found
        :return: True if success
        :rtype: bool
        """
        raise NotImplementedError

    @abstractmethod
    async def update_blob(
        self,
        blob: Blob,
    ) -> BlobMetadata:
        """Updates blob with new content.

        :param blob: the blob to upload
        :type blob: Blob
        :raises UnprocessableContentException: when unable to update the
            blob
        :return: the uploaded blob metadata
        :rtype: BlobMetadata
        """
        raise NotImplementedError

    @abstractmethod
    async def get_blob(
        self,
        blob_metadata: BlobMetadata,
    ) -> Blob:
        """Gets the blob with given metadata.

        :param blob_metadata: the blob metadata
        :type blob_metadata: BlobMetadata
        :raises NotFoundException: when blob is not found
        :return: the blob with content
        :rtype: Blob
        """
        raise NotImplementedError

    @abstractmethod
    async def list_blobs(
        self,
        subpath: str,
    ) -> List[str]:
        """List the blobs given a subpath.

        :param subpath: subpatht of the , e.g.,
            samplesanalysis/nmr/1.0.0/
        :type analysis_type: str
        :return: list of blobs
        :rtype: List[str]
        """
        raise NotImplementedError


class LocalFilesystemBlobStorage(IBlobStorage):
    def __init__(self, base_path: str):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    async def create_blob(self, blob: Blob) -> BlobMetadata:
        blob_path = os.path.join(self.base_path, blob.blob_metadata.object_name)
        os.makedirs(os.path.dirname(blob_path), exist_ok=True)

        async with aiofiles.open(blob_path, "wb") as fp:
            await fp.write(blob.blob_data)

        return blob.blob_metadata

    async def delete_blob(self, blob_metadata: BlobMetadata) -> bool:
        blob_path = os.path.join(self.base_path, blob_metadata.object_name)
        if os.path.exists(blob_path):
            os.remove(blob_path)
            return True
        raise NotFoundException(detail=f"Blob not found: {blob_metadata.object_name}")

    async def update_blob(self, blob: Blob) -> BlobMetadata:
        try:
            await self.delete_blob(blob.blob_metadata)
        except NotFoundException as exc:
            error_msg = exc.detail
            raise UnprocessableContentException(detail=f"Unable to process: {error_msg}")
        return await self.create_blob(blob)

    async def get_blob(self, blob_metadata: BlobMetadata) -> Blob:
        blob_path = os.path.join(self.base_path, blob_metadata.object_name)
        if not os.path.exists(blob_path):
            raise NotFoundException(detail=f"Blob not found: {blob_metadata.object_name}")

        async with aiofiles.open(blob_path, "rb") as fp:
            blob_data = await fp.read()

        return Blob(blob_data=blob_data, blob_metadata=blob_metadata)

    async def list_blobs(self, subpath: str) -> List[str]:
        full_path = os.path.join(self.base_path, subpath)
        if not os.path.exists(full_path):
            return []

        return [
            os.path.relpath(os.path.join(root, blob_file), self.base_path)
            for root, _, blob_files in os.walk(full_path)
            for blob_file in blob_files
        ]


async def get_blob_storage(
    data_partition_id: str,
    settings: AppSettings,
    cloud_provider_config: Optional[BaseSettings],
    **kwargs,
) -> IBlobStorage:

    if settings.local_dev_mode:
        return LocalFilesystemBlobStorage("./blobdata")

    match settings.cloud_provider:
        case "azure":
            from app.providers.dependencies.az.blob_storage import (
                AzureBlobStorage,
            )
            from app.providers.dependencies.az.storage_account_info import (
                AzureStorageAccountInfo,
            )
            async with AzureStorageAccountInfo(
                data_partition_id, settings, cloud_provider_config,
            ) as azure_storage_account_info:
                account_info = await azure_storage_account_info.get_info()
                return AzureBlobStorage(StoragePartitionInfo(data_partition_id, account_info))
        case _:
            raise NotImplementedError()
