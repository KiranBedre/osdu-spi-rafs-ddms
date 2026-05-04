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

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from loguru import logger
from starlette import status

from app.api.routes.utils.ddms_datasets import check_object_name_schema_version
from app.api.routes.utils.records import (
    find_object_name_from_type,
)
from app.dev.dataframe.multiple_nested_filter_processor import (
    DFMultipleNestedFilterProcessor,
)
from app.dev.resources.multiple_nested_filters import (
    DFMultipleNestedFilterValidator,
)
from app.exceptions import exceptions
from app.providers.dependencies.blob_storage import BlobMetadata, IBlobStorage
from app.resources.mime_types import SupportedMimeTypes
from app.services.storage import StorageService


async def get_parquet_data(
    request: Request,
    record_id: str,
    blob_metadata: BlobMetadata,
    blob_storage_service: IBlobStorage,
    storage_service: StorageService,
    df_filter: DFMultipleNestedFilterValidator,
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
    :type df_filter: DFMultipleNestedFilterValidator
    :return: parquet data in proper format
    :rtype: Response
    """
    record = await storage_service.get_record(record_id)
    mime_type = SupportedMimeTypes.find_by_mime_type(request.headers["content-type"])

    ddms_datasets = record["data"].get("DDMSDatasets", [])

    if object_name := find_object_name_from_type(ddms_datasets, blob_metadata.full_analysis_type):  # noqa: WPS332
        blob_metadata.uuid = object_name.split("/")[-1]
        logger.debug(f"Retrieving dataset: {object_name}")
        check_object_name_schema_version(blob_metadata.version, ddms_datasets, blob_metadata.object_name)
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

        filter_processor = DFMultipleNestedFilterProcessor(df_filter)
        df = filter_processor.apply_filters_from_bytes(parquet_bytes)
        logger.debug(f"Dataset info: {df.size} elements; {df.columns}")

        if mime_type == SupportedMimeTypes.PARQUET:
            df.astype(str)
            response = Response(content=df.to_parquet(), media_type=SupportedMimeTypes.PARQUET.mime_type)
        else:
            response = Response(
                content=df.to_json(orient="split"),
                media_type=SupportedMimeTypes.JSON.mime_type,
            )
        del df
    else:
        response = JSONResponse(
            {"message": f"{object_name} does not exist in current record.", "reason": "Not found."},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return response
