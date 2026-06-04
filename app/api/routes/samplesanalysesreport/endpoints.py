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

from app.api.dependencies.services import get_async_storage_service
from app.api.routes.osdu.storage_records import BaseStorageRecordView
from app.api.routes.osdu.wpc_dataset_source import WPCDatasetSourceView
from app.models.schemas.osdu_storage import StorageUpsertResponse
from app.resources.load_model_example import load_data_example
from app.services import storage


class SamplesAnalysesReportView(BaseStorageRecordView):
    """Samples Analyses Report View.

    :param BaseStorageRecordView: inherits from BaseStorageRecordView
    :type BaseStorageRecordView: BaseStorageRecordView
    """

    def __init__(
        self,
        router: APIRouter,
        id_regex_str: str,
        validate_records_payload: callable,
        record_type: str,
    ) -> None:
        super().__init__(router, id_regex_str, validate_records_payload, record_type)
        self._wpc_dataset_source_view = WPCDatasetSourceView(router, id_regex_str)

    async def post_records(
        self,
        request: Request,
        request_records: Annotated[
            List[dict],
            Body(
                openapi_examples={
                    "example": {
                        "value": load_data_example("samples_analyses_report.json"),
                    },
                },
            ),
        ],
        storage_service: storage.StorageService = Depends(get_async_storage_service),
    ) -> StorageUpsertResponse:
        return await super().post_records(request, request_records, storage_service)
