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

import re
from collections import defaultdict
from typing import List, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger
from pydantic.error_wrappers import ValidationError
from pydantic.main import BaseModel
from starlette import status

from app.api.dependencies.services import get_async_storage_service
from app.api.routes.osdu.storage_records import BaseStorageRecordView
from app.exceptions.exceptions import RecordValidationException
from app.models.schemas.osdu_storage import StorageUpsertResponse
from app.services.storage import StorageService


async def get_parent_records(
    storage_service: StorageService,
    records: list,
    parent_id_field: str,
    parent_model: BaseModel,
) -> Tuple[dict, list]:
    """Get parent records.

    :param storage_service: storage service
    :type storage_service: StorageService
    :param records: records
    :type records: list
    :param parent_id_field: parent id field name
    :type parent_id_field: str
    :raises RecordValidationException: if parent record not found
    :raises RecordValidationException: if child field has wrong type
    :param parent_model: parent entity model
    :type parent_model: BaseModel
    :return: parent records ids with list of connected child ids
    :rtype: Tuple[dict, list]
    """
    parent_id_child_record_map = defaultdict(list)
    for record in records:
        parent_id = record["data"].get(parent_id_field)
        if parent_id:
            parent_id = parent_id[:-1]
            parent_id_child_record_map[parent_id].append(record)

    query_parent_records = await storage_service.query_records(list(parent_id_child_record_map.keys()))
    if query_parent_records["invalidRecords"]:
        reason = f"Parent records {query_parent_records['invalidRecords']} not found."
        logger.debug(reason)
        raise RecordValidationException(detail=reason)

    parent_records = query_parent_records["records"]
    parent_records_size = len(parent_records)
    logger.info(f"Parent records have been found: {parent_records_size}")

    for parent_record in parent_records:
        try:
            parent_model.validate(parent_record)
            parent_record_size = len(parent_record)
            logger.info(f"{parent_record_size} Parent records are valid.")
        except ValidationError as val_error:
            details = []
            for error in val_error.errors():
                error_field = ".".join(map(str, error["loc"]))
                error_msg = error["msg"]
                error_detail = f"{error_field}: {error_msg}"
                details.append(error_detail)
            reason = f"Parent record is invalid. {details}"
            logger.debug(reason)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=reason,
            )

    logger.debug(f"Map parent_id-child_record: {parent_id_child_record_map}")
    return parent_id_child_record_map, parent_records


async def link_to_parent(
    storage_service: StorageService,
    child_id_field: str,
    parent_id_child_id_map: dict,
    parent_records: list,
) -> dict:
    """Link child id to parent.

    :param storage_service: storage service
    :type storage_service: StorageService
    :param child_id_field: child id field name
    :type child_id_field: str
    :param parent_id_child_id_map: parent records ids with list of connected child ids
    :type parent_id_child_id_map: dict
    :param parent_records: parent records
    :type parent_records: list
    :return: upserted records ids
    :rtype: dict
    """
    for parent_record in parent_records:
        regex = "--(.*?):"
        for record_id in parent_id_child_id_map[parent_record["id"]]:
            record_id_without_version = "{0}:".format(record_id.rsplit(":", 1)[0])
            entity = re.search(regex, record_id).group(1)
            entity_ids = parent_record["data"].setdefault(child_id_field, {}).setdefault(f"{entity}ID", [])
            if record_id_without_version not in entity_ids:
                entity_ids.append(record_id_without_version)

    storage_response = {}
    if parent_records:
        storage_response = await storage_service.upsert_records(parent_records)

    return storage_response


class StorageRecordViewWithLinking(BaseStorageRecordView):
    def __init__(
        self,
        router: APIRouter,
        id_regex_str: str,
        validate_records_payload: callable,
        record_type: str,
        child_id_field: str,
        parent_id_field: str,
        parent_model: BaseModel,
    ) -> None:
        super().__init__(
            router,
            id_regex_str,
            validate_records_payload,
            record_type,
        )
        self._child_id_field = child_id_field
        self._parent_id_field = parent_id_field
        self._parent_model = parent_model

    async def post_records(
        self,
        request: Request,
        request_records: List[dict],
        storage_service: StorageService = Depends(get_async_storage_service),
    ) -> StorageUpsertResponse:
        """Post records with linking to parent.

        :param request_records: request records
        :type request_records: List[dict]
        :param storage_service: storage service
        :type storage_service: storage.StorageService
        :return: upserted records ids
        :rtype: StorageUpsertResponse
        """
        record_count = 0
        record_id_versions = []
        skipped_record_count = 0
        has_parent_entity = bool(self._child_id_field and self._parent_id_field and self._parent_model)

        if has_parent_entity:
            parent_id_child_record_map, parent_records = await get_parent_records(
                storage_service,
                request_records,
                self._parent_id_field,
                self._parent_model,
            )

            parent_id_child_id_map = {}

            for parent_id, child_records in parent_id_child_record_map.items():
                storage_response = await super().post_records(request, child_records, storage_service)

                record_count += storage_response.recordCount
                skipped_record_count += storage_response.skippedRecordCount
                current_record_id_versions = storage_response.recordIdVersions
                parent_id_child_id_map.update({parent_id: current_record_id_versions})
                record_id_versions.extend(current_record_id_versions)

            try:
                parent_records_storage_response = await link_to_parent(
                    storage_service,
                    self._child_id_field,
                    parent_id_child_id_map,
                    parent_records,
                )
                record_count += parent_records_storage_response.get("recordCount")
                record_id_versions += parent_records_storage_response.get("recordIdVersions")
                skipped_record_count += len(parent_records_storage_response.get("skipperRecordIds", []))

            except (KeyError, AttributeError) as exc:
                logger.warning(f"Failed to update PVT records: {exc}")
        else:
            storage_response = await super().post_records(request_records, storage_service)
            record_count += storage_response.recordCount
            record_id_versions = storage_response.recordIdVersions
            skipped_record_count += storage_response.skippedRecordCount

        return StorageUpsertResponse(
            record_count=record_count,
            record_id_versions=set(record_id_versions),
            skipped_record_count=skipped_record_count,
        )
