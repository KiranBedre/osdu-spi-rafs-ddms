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
from typing import List, Optional

from fastapi import Depends

from app.api.dependencies.services import (
    get_async_dataset_service,
    get_async_storage_service,
)
from app.api.routes.utils.mimetypes import get_mime_type
from app.api.routes.utils.records import get_id_version
from app.resources.source_renderer import DatasetSourceFile
from app.services import dataset, storage


async def get_data_file_source(
    dataset_full_id: str,
    storage_service: storage.StorageService = Depends(get_async_storage_service),
    dataset_service: dataset.DatasetService = Depends(get_async_dataset_service),
):
    """Resolve a single dataset file source from storage.

    Args:
        dataset_full_id: Full dataset ID including optional version suffix.
        storage_service: Async storage service for retrieving dataset records.
        dataset_service: Async dataset service for downloading file content.

    Returns:
        DatasetSourceFile containing the dataset ID, MIME type, and file content.
    """
    dataset_id, version = get_id_version(dataset_full_id)
    dataset_record = await storage_service.get_record(dataset_id, version)
    mime_type = get_mime_type(dataset_record)

    return DatasetSourceFile(
        dataset_id=dataset_id,
        mime_type=mime_type,
        content=await dataset_service.download_file(dataset_id),
    )


async def get_data_file_sources(
    record_id: str,
    storage_service: storage.StorageService = Depends(get_async_storage_service),
    dataset_service: dataset.DatasetService = Depends(get_async_dataset_service),
    version: Optional[str] = None,
) -> List[DatasetSourceFile]:
    """Resolve all dataset file sources for a given record.

    Args:
        record_id: The ID of the parent record containing dataset references.
        storage_service: Async storage service for retrieving records.
        dataset_service: Async dataset service for downloading file content.
        version: Optional version of the record to retrieve.

    Returns:
        List of DatasetSourceFile for all datasets referenced in the record.
    """
    record = await storage_service.get_record(record_id, version)
    datasets = record["data"].get("Datasets", [])

    tasks = [get_data_file_source(dataset_id, storage_service, dataset_service) for dataset_id in datasets]

    return await asyncio.gather(*tasks)
