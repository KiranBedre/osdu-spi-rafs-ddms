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

from typing import List
from pydantic import Field

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response
from fastapi_cache.decorator import cache
from starlette import status

from app.api.dependencies.request import validate_json_content_type
from app.api.dependencies.services import (
    get_async_schema_service,
    get_async_storage_service,
)
from app.api.routes.utils.api_description_helper import APIDescriptionHelper
from app.core.helpers.cache.key_builder import key_builder_using_token
from app.core.helpers.cache.settings import CACHE_DEFAULT_TTL
from app.models.schemas.osdu_storage import (
    OsduStorageRecord,
    StorageUpsertResponse,
)
from app.services import schema, storage

_VERSION_MAX = 9223372036854775807  # int64 max


class BaseStorageRecordView(object):
    def __init__(
        self,
        router: APIRouter,
        id_regex_str: str,
        validate_records_payload: callable,
        record_type: str,
    ) -> None:
        self._router = router
        self._validate_records_payload = validate_records_payload
        self._record_type = record_type
        self._id_regex_str = id_regex_str
        self._prepare_api_routes()

    @cache(expire=CACHE_DEFAULT_TTL, key_builder=key_builder_using_token)
    async def get_record(
        self,
        record_id: str,
        storage_service: storage.StorageService = Depends(get_async_storage_service),
    ) -> dict:
        """Get last upserted record.

        :param record_id: record id
        :type record_id: str
        :param storage_service: storage service
        :type storage_service: StorageService
        :return: record
        :rtype: dict
        """
        return await storage_service.get_record(record_id)

    @cache(expire=CACHE_DEFAULT_TTL, key_builder=key_builder_using_token)
    async def get_record_versions(
        self,
        record_id: str,
        storage_service: storage.StorageService = Depends(get_async_storage_service),
    ) -> dict:
        """Get record versions.

        :param record_id: record id
        :type record_id: str
        :param storage_service: storage service
        :type storage_service: storage.StorageService
        :return: record versions
        :rtype: dict
        """
        return await storage_service.get_record_versions(record_id)

    @cache(expire=CACHE_DEFAULT_TTL, key_builder=key_builder_using_token)
    async def get_record_specific_version(
        self,
        version: int,
        record_id: str,
        storage_service: storage.StorageService = Depends(get_async_storage_service),
    ) -> dict:
        """Get specific record.

        :param version: version
        :type version: int
        :param record_id: record id
        :type record_id: str
        :param storage_service: storage service
        :type storage_service: storage.StorageService
        :return: specific record
        :rtype: dict
        """
        record = await storage_service.get_record(record_id, version)

        if record:
            # Handle both dictionary (production) and Pydantic mock objects (testing)
            record_version = record.get("version") if isinstance(record, dict) else getattr(record, "version", None)

            if record_version is not None and int(record_version) != version:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Record version {version} not found")

        return record

    async def post_records(
        self,
        request: Request,
        request_records: List[dict],
        storage_service: storage.StorageService = Depends(get_async_storage_service),
    ) -> StorageUpsertResponse:
        """Post records.

        :param request: request
        :type request: Request
        :param request_records: request records
        :type request_records: List[dict]
        :param storage_service: storage service
        :type storage_service: storage.StorageService
        :return: upserted records ids
        :rtype: StorageUpsertResponse
        """
        storage_response = await storage_service.upsert_records(request_records)
        record_count = storage_response.get("recordCount")
        record_id_versions = storage_response.get("recordIdVersions")
        skipped_record_count = len(storage_response.get("skippedRecordIds", []))

        return StorageUpsertResponse(
            record_count=record_count,
            record_id_versions=set(record_id_versions),
            skipped_record_count=skipped_record_count,
        )

    async def soft_delete_record(
        self,
        record_id: str,
        storage_service: storage.StorageService = Depends(get_async_storage_service),
    ) -> Response:
        """Make record unavailable without admin rights.

        :param record_id: record id
        :type record_id: str
        :param storage_service: storage service
        :type storage_service: storage.StorageService
        :return: response with no content
        :rtype: Response
        """
        await storage_service.soft_delete_record(record_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    def _prepare_api_routes(self) -> None:
        """Prepare and add api routes."""
        self._prepare_get_record_route()
        self._prepare_get_record_versions_route()
        self._prepare_get_record_specific_version_route()
        self._prepare_post_records_route()
        self._prepare_soft_delete_record_route()

    def _prepare_get_record_route(self) -> None:
        """Add api route for get_record."""

        def validate_record_id(record_id: str = Path(default=..., pattern=self._id_regex_str)) -> str:
            """Validate if record id matches regex.

            :param record_id: record id
            :type record_id: str
            :return: record id
            :rtype: str
            """
            return record_id

        self._router.add_api_route(
            path="/{record_id}",
            endpoint=self.get_record,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
            description=APIDescriptionHelper.append_joined_roles(
                f"Get the latest version of `{self._record_type}` object by record id.",
            ),
            dependencies=[Depends(validate_record_id)],
        )

    def _prepare_get_record_versions_route(self) -> None:
        """Add api route for get_record_versions."""

        def validate_record_id(record_id: str = Path(default=..., pattern=self._id_regex_str)) -> str:
            """Validate if record id matches regex.

            :param record_id: record id
            :type record_id: str
            :return: record id
            :rtype: str
            """
            return record_id

        self._router.add_api_route(
            path="/{record_id}/versions",
            endpoint=self.get_record_versions,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
            description=APIDescriptionHelper.append_joined_roles(
                f"Get a list of `{self._record_type}` object versions by record id.",
            ),
            dependencies=[Depends(validate_record_id)],
        )

    def _prepare_get_record_specific_version_route(self) -> None:
        """Add api route for get_record_specific_version."""

        def validate_record_id(record_id: str = Path(default=..., pattern=self._id_regex_str)) -> str:
            """Validate if record id matches regex.

            :param record_id: record id
            :type record_id: str
            :return: record id
            :rtype: str
            """
            return record_id

        def validate_version(version: int = Path(default=..., ge=1, le=_VERSION_MAX)) -> int:
            """Validate version is a positive integer within int64 range.

            :param version: record version
            :type version: int
            :return: version
            :rtype: int
            """
            return version

        self._router.add_api_route(
            path="/{record_id}/versions/{version}",
            endpoint=self.get_record_specific_version,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
            description=APIDescriptionHelper.append_joined_roles(
                f"Get the given version of `{self._record_type}` object.",
            ),
            dependencies=[Depends(validate_record_id), Depends(validate_version)],
        )

    def _prepare_post_records_route(self) -> None:
        """Add api route for post_records."""

        async def validate_request_records(
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
            response_model=StorageUpsertResponse,
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

    def _prepare_soft_delete_record_route(self) -> None:
        """Add api route for soft_delete_record."""

        def validate_record_id(record_id: str = Path(default=..., pattern=self._id_regex_str)) -> str:
            """Validate if record id matches regex.

            :param record_id: record id
            :type record_id: str
            :return: record id
            :rtype: str
            """
            return record_id

        self._router.add_api_route(
            path="/{record_id}",
            endpoint=self.soft_delete_record,
            methods=["DELETE"],
            status_code=status.HTTP_204_NO_CONTENT,
            description=APIDescriptionHelper.append_manage_roles(
                f"Delete the `{self._record_type}` object by record id.",
            ),
            dependencies=[Depends(validate_record_id)],
        )


class StorageUpsertResponseWithWarning(StorageUpsertResponse):
    warning: str
    warningRecordIds: List[str] = Field(
        alias="warning_record_ids",
    )
