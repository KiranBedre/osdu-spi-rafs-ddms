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

from typing import Any, Dict, List

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from loguru import logger
from starlette import status

from app.api.dependencies.request import get_response_mime_type
from app.api.routes.utils.records import (
    find_object_name_from_type,
    find_object_name_index,
    find_schema_versions_for_object_name,
    generate_blob_urn,
    get_id_version,
)
from app.core.config import get_app_settings
from app.dataframe.parquet_filter import apply_filters_from_bytes
from app.exceptions import exceptions
from app.providers.dependencies.blob_storage import (
    Blob,
    BlobMetadata,
    IBlobStorage,
)
from app.resources.filters import DataFrameFilterValidator
from app.resources.mime_types import SupportedMimeTypes
from app.services.storage import StorageService


def check_object_name_schema_version(
    content_schema_version: str,
    ddms_datasets: List[str],
    blob_id: str,
) -> None:
    """Check if proper schema version requested.

    :param content_schema_version: client schema version
    :type content_schema_version: str
    :param ddms_datasets: DDMS Datasets
    :type ddms_datasets: List[str]
    :param dataset_id: dataset id
    :type dataset_id: str
    :raises exceptions.InvalidHeaderException: if client schema version
        is improper
    """
    schema_versions = list(find_schema_versions_for_object_name(ddms_datasets, blob_id))
    if content_schema_version not in schema_versions:
        error_title = f"Schema version mismatch for dataset {blob_id}:"
        error_details = f"requested {content_schema_version}, stored {schema_versions}"
        reason = f"{error_title} {error_details}"
        logger.debug(reason)
        raise exceptions.InvalidHeaderException(detail=reason)


async def upsert_parquet_data(
    blob: Blob,
    record_id: str,
    blob_storage_service: IBlobStorage,
    storage_service: StorageService,
) -> Dict[str, Any]:
    """Upsert parquet via blob storage service and update WPC via storage
    service.

    :param blob: The blob to be created or updated
    :type blob: Blob
    :param record_id: The record ID
    :type record_id: str
    :param blob_storage_service: Instance of blob storage service
    :type blob_storage_service: IBlobStorage
    :param storage_service: Instance of storage service
    :type storage_service: storage.StorageService
    :return: Dictionary containing the DDMS URN of the stored Parquet
        file
    :rtype: dict
    """
    record = await storage_service.get_record(record_id)
    settings = get_app_settings()

    record_data = record["data"]
    ddms_datasets = record_data.get("DDMSDatasets", [])
    existent_object_name = find_object_name_from_type(ddms_datasets, blob.blob_metadata.full_analysis_type)

    object_name = blob.blob_metadata.object_name
    ddms_urn = generate_blob_urn(
        ddms_id=settings.ddms_id,
        wpc_id=record_id,
        object_name=object_name,
    )
    ddms_datasets_index = find_object_name_index(ddms_datasets=ddms_datasets, object_name=existent_object_name)
    if ddms_datasets_index is not None:
        ddms_datasets[ddms_datasets_index] = ddms_urn
    else:
        ddms_datasets.append(ddms_urn)

    metadata = await blob_storage_service.create_blob(blob)
    logger.info(f"File uploaded for new blob: {object_name}")
    logger.debug(metadata)

    record_data["DDMSDatasets"] = ddms_datasets
    storage_response = await storage_service.upsert_records([record])
    logger.info(f"Updated record: {storage_response}")

    return JSONResponse(
        {
            "ddms_urn": ddms_urn,
            "updated_wpc_id": storage_response["recordIdVersions"],
        },
    )


async def get_parquet_data(
    request: Request,
    record_id: str,
    blob_metadata: BlobMetadata,
    blob_storage_service: IBlobStorage,
    storage_service: StorageService,
    df_filter: DataFrameFilterValidator,
    orient: str = "split",
) -> Response:
    """Get parquet data.

    :param request: request
    :type request: Request
    :param record_id: record id,
    :type record_id: str
    :param blob_metadata: the blob metadata,
    :type blob_metadata: BlobMetadata
    :param blob_storage_service: blob storage service
    :type blob_storage_service: IBlobStorage
    :param storage_service: storage service
    :type storage_service: StorageService
    :param df_filter: df filter validator
    :type df_filter: DataFrameFilterValidator
    :param orient: JSON output format ('split' or 'records')
    :type orient: str
    :return: parquet data in proper format
    :rtype: Response
    """
    record_id, version = get_id_version(record_id)
    record = await storage_service.get_record(record_id, version)
    mime_type = get_response_mime_type(request)
    # Aggregation results only make sense in split format (index holds the function name)
    orient = "split" if df_filter.valid_columns_aggregation else orient

    object_name = blob_metadata.object_name
    ddms_datasets = record["data"].get("DDMSDatasets", [])

    if find_object_name_index(ddms_datasets, object_name) is not None:
        logger.debug(f"Retrieving parquet: {object_name}")
        check_object_name_schema_version(blob_metadata.version, ddms_datasets, object_name)
        blob = await blob_storage_service.get_blob(blob_metadata)
        parquet_bytes = blob.blob_data
        blob_info = blob.blob_metadata.metadata
        logger.info(f"Downloaded {blob_info}")

        if not parquet_bytes:
            reason = f"{object_name} exist in record but without content."
            logger.debug(reason)
            raise exceptions.UnprocessableContentException(
                detail=reason,
            )

        df = apply_filters_from_bytes(parquet_bytes, df_filter)
        logger.debug(f"Dataframe info: {df.size} elements; {df.columns}")

        if mime_type == SupportedMimeTypes.PARQUET:
            response = Response(content=df.to_parquet(), media_type=SupportedMimeTypes.PARQUET.mime_type)
        else:
            response = Response(
                content=df.to_json(orient=orient),
                media_type=SupportedMimeTypes.JSON.mime_type,
            )
        del df
    else:
        response = JSONResponse(
            {"message": f"{object_name} does not exist in current record.", "reason": "Not found."},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return response
