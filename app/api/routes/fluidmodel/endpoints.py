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

from typing import Annotated, List

from fastapi import Body, Depends, Request
from starlette import status

from app.api.dependencies.request import validate_json_content_type
from app.api.dependencies.services import (
    get_async_storage_service,
    get_async_schema_service,
)
from app.api.routes.utils.api_description_helper import APIDescriptionHelper
from app.api.dependencies.validation import validate_record_multi_content_type_reference
from app.api.routes.osdu.storage_records import (
    BaseStorageRecordView,
    OsduStorageRecord,
    StorageUpsertResponse,
    StorageUpsertResponseWithWarning,
)
from app.resources.load_model_example import load_data_example
from app.services import schema, storage

FluidModelBody = Annotated[
    List[dict],
    Body(
        openapi_examples={
            "example": {
                "value": load_data_example("fluid_model.json"),
            },
        },
    ),
]


class FluidModelRecordView(BaseStorageRecordView):
    """Fluid Model View.

    :param BaseStorageRecordView: inherits from BaseStorageRecordView
    :type BaseStorageRecordView: BaseStorageRecordView
    """

    async def post_records(
        self,
        request: Request,
        request_records: FluidModelBody,
        storage_service: storage.StorageService = Depends(get_async_storage_service),
    ) -> StorageUpsertResponseWithWarning | StorageUpsertResponse:

        warning_indices = validate_record_multi_content_type_reference(
            records_list=request_records,
            content_type_reference="FluidModelTypeID"
        )

        storage_response = await storage_service.upsert_records(request_records)
        record_count = storage_response.get("recordCount")
        record_id_versions = storage_response.get("recordIdVersions")
        skipped_record_count = len(storage_response.get("skippedRecordIds", []))

        if warning_indices:
            warning = "Records missing FluidModelTypeID will not be included in outputs produced by search endpoints"
            warning_record_ids = [
                record_id_versions[index].rsplit(":", 1)[0]
                for index in warning_indices
                if index < len(record_id_versions)
            ]

            return StorageUpsertResponseWithWarning(
                record_count=record_count,
                record_id_versions=set(record_id_versions),
                skipped_record_count=skipped_record_count,
                warning=warning,
                warning_record_ids=warning_record_ids
            )
        else:
            return StorageUpsertResponse(
                record_count=record_count,
                record_id_versions=set(record_id_versions),
                skipped_record_count=skipped_record_count
            )

    def _prepare_post_records_route(self) -> None:
        """Add api route for post_records."""

        async def validate_request_records(  # noqa: WPS430
            request_records: List[OsduStorageRecord],
            storage_service: storage.StorageService = Depends(get_async_storage_service),
            schema_service: schema.SchemaService = Depends(get_async_schema_service),
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
            return await self._validate_records_payload(
                request_records,
                storage_service=storage_service,
                schema_service=schema_service,
            )

        self._router.add_api_route(
            path="",
            endpoint=self.post_records,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            response_model=StorageUpsertResponseWithWarning | StorageUpsertResponse,
            response_model_by_alias=False,
            description=APIDescriptionHelper.append_manage_roles(
                f"Create or update `{self._record_type}` record(s)."
                + " The `Content-Type: application/json` request header is required.",
            ),
            dependencies=[
                Depends(validate_request_records),
                Depends(validate_json_content_type),
            ],
        )
