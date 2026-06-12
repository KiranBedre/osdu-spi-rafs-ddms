#  Copyright 2025 ExxonMobil Technology and Engineering Company
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

import io
from typing import Annotated, List, Optional

import pandas as pd
from fastapi import Body, Depends, HTTPException, Request
from pydantic import BaseModel
from starlette import status

from app.api.dependencies.services import get_async_storage_service
from app.api.routes.osdu.storage_records import BaseStorageRecordView
from app.api.routes.v2.data.endpoints import DynamicContentTypeDataViewV2
from app.models.schemas.osdu_storage import StorageUpsertResponse
from app.resources.load_model_example import load_data_example
from app.services import storage

DepthShiftBody = Annotated[
    List[dict],
    Body(
        openapi_examples={
            "example": {
                "value": load_data_example("depth_shift.json"),
            },
        },
    ),
]


class DepthShiftDataViewV2(DynamicContentTypeDataViewV2):
    """DepthShift data view with single-row enforcement on POST."""

    async def _get_validated_payload(
        self,
        request: Request,
        model: BaseModel,
        storage_service: storage.StorageService,
        record_id: Optional[str] = None,
    ) -> bytes:
        parquet_file = await super()._get_validated_payload(request, model, storage_service, record_id)
        df = pd.read_parquet(io.BytesIO(parquet_file))
        if len(df) != 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "CoreToLog content for DepthShift WPC {0} must contain exactly 1 row, "
                    "but {1} rows were found. Each DepthShift WPC must reference a single "
                    "CoreToLog record.".format(record_id or "unknown", len(df))
                ),
            )
        return parquet_file


class DepthShiftRecordView(BaseStorageRecordView):
    """Depth Shift View.

    :param BaseStorageRecordView: inherits from BaseStorageRecordView
    :type BaseStorageRecordView: BaseStorageRecordView
    """

    async def post_records(
        self,
        request: Request,
        request_records: DepthShiftBody,
        storage_service: storage.StorageService = Depends(get_async_storage_service),
    ) -> StorageUpsertResponse:
        return await super().post_records(request, request_records, storage_service)
