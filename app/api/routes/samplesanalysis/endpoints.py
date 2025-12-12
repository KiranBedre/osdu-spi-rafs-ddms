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

from typing import Annotated, List

from fastapi import APIRouter, Body, Depends, Request
from starlette import status

from app.api.dependencies.request import validate_json_content_type
from app.api.dependencies.services import get_async_storage_service
from app.api.routes.osdu.storage_records import BaseStorageRecordView
from app.api.routes.utils.api_description_helper import APIDescriptionHelper
from app.models.schemas.osdu_storage import (
    OsduStorageRecord,
    StorageUpsertResponse,
)
from app.resources.load_model_example import load_data_example
from app.services import storage

SAMPLESANALYSIS_ID_REGEX_STR = r"^[\w\-\.]+:work-product-component--SamplesAnalysis:[\w\-\.\:\%]+$"


class SamplesAnalysisRecordView(BaseStorageRecordView):
    def __init__(
        self,
        router: APIRouter,
        validate_records_payload: callable,
        record_type: str,
    ) -> None:
        super().__init__(
            router=router,
            id_regex_str=SAMPLESANALYSIS_ID_REGEX_STR,
            validate_records_payload=validate_records_payload,
            record_type=record_type,
        )

    async def post_records(
        self,
        request: Request,
        request_records: Annotated[
            List[dict], Body(
                openapi_examples={
                    "example": {
                        "value": load_data_example("samples_analysis.json"),
                    },
                },
            ),
        ],
        storage_service: storage.StorageService = Depends(get_async_storage_service),
    ) -> StorageUpsertResponse:
        return await super().post_records(request, request_records, storage_service)

    def _prepare_post_records_route(self) -> None:
        """Add api route for post_records without dependencies."""
        async def validate_request_records(
            request_records: List[OsduStorageRecord],
            storage_service: storage.StorageService = Depends(get_async_storage_service),
        ) -> List[dict]:
            """Validate request records.

            :param request_records: request records
            :type request_records: List[OsduStorageRecord]
            :param storage_service: storage service instance, defaults
                  to Depends(get_async_storage_service)
            :type storage_service: storage.StorageService, optional
            :return: validated records
            :rtype: List[dict]
            """
            return await self._validate_records_payload(request_records, storage_service)

        self._router.add_api_route(
            path="",
            endpoint=self.post_records,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            response_model=StorageUpsertResponse,
            response_model_by_alias=False,
            description=APIDescriptionHelper.append_manage_roles(
                f"Create or update `{self._record_type}` record(s).",
            ),
            dependencies=[
                Depends(validate_request_records),
                Depends(validate_json_content_type),
            ],
        )
