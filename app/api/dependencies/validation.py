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
import copy
import json
from datetime import date
from typing import Iterable, List, Optional, Set, Tuple, TypeVar

from fastapi import Depends, HTTPException, Query, Request
from loguru import logger
from pydantic import BaseModel
from starlette import status

from app.api.dependencies.request import get_content_schema_version
from app.api.dependencies.services import (
    get_async_schema_service,
    get_async_storage_service,
)
from app.api.routes.utils.api_version import get_api_version_from_url
from app.api.routes.utils.query import divide_chunks, find_osdu_ids_from_string
from app.core.config import get_app_settings
from app.exceptions.exceptions import (
    BadRequestException,
    InvalidDatasetException,
    RecordValidationException,
)
from app.models.data_schemas.base import PATHS_TO_DATA_MODEL
from app.models.domain.osdu import base as osdu_models_base
from app.models.schemas.osdu_storage import OsduStorageRecord
from app.models.schemas.pandas_dataframe import OrientSplit
from app.resources.errors import FilterValidationError
from app.resources.filters import DataFrameFilterValidator
from app.resources.paths import COMMON_RELATIVE_PATHS
from app.services.schema import SchemaService
from app.services.storage import StorageService

SAMPLESANALYSIS_TYPE_RECORD_FIELD = "SampleAnalysisTypeIDs"

Model = TypeVar("Model", bound=BaseModel)
settings = get_app_settings()


def get_id(id_data):  # noqa: CCR001
    """Generator to get record ids from different record data field values."""
    if isinstance(id_data, str):
        yield id_data
    elif isinstance(id_data, Iterable):
        if isinstance(id_data, dict):
            for id_key, id_value in id_data.items():
                if "ID" in id_key:
                    yield from get_id(id_value)
        elif isinstance(id_data, list):
            for element in id_data:
                yield from get_id(element)
        else:
            yield from id_data


def get_all_ids_from_records(records: List[dict]) -> Set[str]:
    """Get all referenced ids from the records.

    :param records: records list
    :type records: List[dict]
    :return: A set of referenced ids
    :rtype: Set[str]
    """
    all_ids = set()
    for record in records:
        record_copy = copy.deepcopy(record)
        if "id" in record_copy:
            del record_copy["id"]  # noqa: WPS529
        all_ids.update(find_osdu_ids_from_string(json.dumps(record_copy)))
    return all_ids


def validate_ids_from_records(
    records: List[dict],
    fields: List[str],
):
    """Get the list of all ids in the records fields.

    :param records: list of records
    :type records: List[dict]
    :param fields: list of fields to collect
    :type fields: List[str]
    """
    errors = []
    for index, record in enumerate(records):
        for field in fields:
            field_data = record["data"].get(field, None)
            mandatory_ids = list(get_id(field_data))
            if not mandatory_ids:
                errors.append(f"Missing {field} in index {index}")
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=errors,
        )


async def validate_referential_integrity(
    records: List[dict],
    fields: List[str],
    storage_service: StorageService,
):
    """Performs referential integrity validation.

    :param records: list of records to validate
    :type records: List[dict]
    :param fields: list of fields to validate
    :type fields: List[str]
    :param storage_service: the storage service instance
    :type storage_service: StorageService
    :raises HTTPException: Status 422 if any of the references is not
        found
    """
    validate_ids_from_records(records, fields)

    all_test_ids = get_all_ids_from_records(records)
    missing_ids = []

    logger.debug(f"The list of ids to check exist on storage: {all_test_ids}")
    for ids_to_check in divide_chunks(list(all_test_ids), settings.storage_query_limit):
        storage_response = await storage_service.query_records(ids_to_check)
        missing_ids.extend(storage_response["invalidRecords"])

    logger.debug(missing_ids)

    if missing_ids:
        error_title = "Request can't be processed due to missing referenced records."
        error_details = f"Records not found: {missing_ids}"
        reason = f"{error_title} {error_details}"
        logger.debug(reason)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=reason,
        )


def validate_kind(kind: str, valid_kinds: List[str]):
    """Validates kind against supported kinds in given endpoint.

    :param kind: the kind to be validated
    :type kind: str
    :param valid_kinds: supported kinds
    :type valid_kinds: List[str]
    :raises RuntimeError: If there is no kind that matches supported
        kinds
    """
    if kind not in valid_kinds:
        raise RecordValidationException(
            detail=f"Kind `{kind}` not supported in RAFS-DDMS. Supported kinds for this endpoint: {valid_kinds}",
        )


def build_skipped_record_error(record: dict, index: int, error: Exception):
    return {
        "id": record.get("id", f"record_at_index_{index}"),
        "kind": record.get("kind"),
        "reason": error,
    }


async def validate_osdu_wks_records(
    records_list: List[OsduStorageRecord],
    schema_service: SchemaService,
    valid_kinds: List[str],
) -> List[dict]:
    """Validate OSDU records using Well Known Schema.

    :param records_list: list of records
    :type records_list: List[OsduStorageRecord]
    :param schema_service: schema service instance
    :type schema_service: SchemaService
    :param valid_kinds: list of valid kinds
    :type valid_kinds: List[str]
    :raises exc: when schema fetch fails
    :raises RecordValidationException: when jsonschema validation fails
    :return: list of validated records
    :rtype: List[dict]
    """
    tasks = []
    records = []
    skipped = []
    try:
        async with asyncio.TaskGroup() as group:
            for index, record in enumerate(records_list):
                record_dict = record.dict(exclude_none=True)
                validate_kind(record_dict.get("kind", ""), valid_kinds=valid_kinds)
                records.append(record_dict)
                tasks.append(
                    group.create_task(
                        schema_service.validate(
                            record=record_dict, schema_id=record_dict["kind"], optional_id=f"record_at_index_{index}",
                        ),
                    ),
                )
    except ExceptionGroup as eg:
        for exc in eg.exceptions:  # noqa: WPS328 pylint: disable=not-an-iterable
            raise exc

    skipped = [task.result() for task in tasks if task.result()]
    if skipped:
        logger.error(f"Validation failed. Skipped records {skipped}")
        raise RecordValidationException(detail=skipped)

    logger.info("Records successfully validated.")
    return records


async def validate_samples_analyses_report_v2_payload(
    records_list: List[OsduStorageRecord],
    storage_service: StorageService = Depends(get_async_storage_service),
    schema_service: SchemaService = Depends(get_async_schema_service),
):
    records = await validate_osdu_wks_records(
        records_list,
        schema_service,
        [osdu_models_base.SAMPLES_ANALYSES_REPORT_KIND],
    )
    await validate_referential_integrity(
        records,
        [],
        storage_service,
    )
    return records


async def validate_samplesanalysis_records_v2_payload(
    records_list: List[OsduStorageRecord],
    storage_service: StorageService = Depends(get_async_storage_service),
    schema_service: SchemaService = Depends(get_async_schema_service),
):
    records = await validate_osdu_wks_records(
        records_list,
        schema_service,
        [osdu_models_base.SAMPLESANALYSIS_KIND],
    )
    await validate_referential_integrity(
        records,
        [SAMPLESANALYSIS_TYPE_RECORD_FIELD],
        storage_service,
    )
    return records


async def validate_master_data_records_payload(
    records_list: List[OsduStorageRecord],
    schema_service: SchemaService,
    storage_service: StorageService,
) -> List[dict]:
    records = await validate_osdu_wks_records(records_list, schema_service, osdu_models_base.MASTER_DATA_KINDS_V2)
    await validate_referential_integrity(records, [], storage_service)
    return records


def get_content_model_paths(request_path: str, api_version: str) -> tuple:
    """Get the paths to search for the appropriate content model.

    :param request_path: the request path
    :type request_path: str
    :param api_version: the api version
    :type api_version: str
    :return: appropiate paths to retrieve content models
    :rtype: tuple
    """
    relative_paths = COMMON_RELATIVE_PATHS[api_version]()
    paths_to_content_models = PATHS_TO_DATA_MODEL[api_version]

    if api_version in {"v2", "dev"} and "search" in request_path:
        start_index = 5  # skip '/data'
        relative_paths = [f"{path[start_index:]}/search" for path in relative_paths]  # noqa: WPS237
        search_path_to_content_models = {}
        for path, model in paths_to_content_models.items():
            search_path_to_content_models[f"{path[start_index:]}/search"] = model  # noqa: WPS237

        paths_to_content_models = search_path_to_content_models

    return (relative_paths, paths_to_content_models)


async def get_data_model(request: Request, content_schema_version: str = Depends(get_content_schema_version)) -> Model:
    """Get the model based on the request path.

    :param request: request object
    :type request: Request
    :param content_schema_version: version obtained from header,
        defaults to Depends(retrieve_schema_version)
    :type content_schema_version: str, optional
    :raises BadRequestException: if model is not implemented for given
        version
    :raises HTTPException: if model is not implemented neither for path
        nor version
    :return: The corresponding data model according to path and version
    :rtype: Model
    """
    model = None

    version_models = None
    request_path = request.url.path
    api_version = get_api_version_from_url(request_path)
    relative_paths, paths_to_content_models = get_content_model_paths(request_path, api_version)
    for path in relative_paths:
        if path in str(request_path):
            version_models = paths_to_content_models.get(path)
            break

    if not version_models:
        reason = f"Unimplemented model for route {request_path}."
        logger.debug(reason)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=reason)

    model = version_models.get(content_schema_version)
    if not model:
        available_versions = set(version_models.keys())
        error_title = "There is no model for given version."
        error_details = f"Schema version {content_schema_version} is not one of proper versions: {available_versions}"
        reason = f"{error_title} {error_details}"
        logger.debug(reason)
        raise BadRequestException(detail=reason)

    return model


async def validate_filters(
    model: BaseModel = Depends(get_data_model),
    columns_filter: Optional[str] = Query(
        default=None,
        example="PropertyX,PropertyY,PropertyZ",
    ),
    rows_filter: Optional[str] = Query(
        default=None,
        example="PropertyX[.PropertyXFieldA],gt,4000",
    ),
    columns_aggregation: Optional[str] = Query(
        default=None,
        example="PropertyX[.PropertyXFieldA],avg",
    ),
) -> DataFrameFilterValidator:
    """Validates query parameters used for dataframe filtering.

    :param model: pydantic model, defaults to Depends(get_data_model)
    :type model: BaseModel, optional
    :param columns_filter: comma separated string of columns, defaults
        to Query( default=None, example="PropertyX,PropertyY,PropertyZ",
        )
    :type columns_filter: Optional[str], optional
    :param rows_filter: comma separated predicate, defaults to Query(
        default=None, example="PropertyX[.PropertyXFieldA],gt,4000", )
    :type rows_filter: Optional[str], optional
    :param columns_aggregation: comma separated aggregation, defaults to
        Query( default=None, example="PropertyX[.PropertyXFieldA],avg",
        )
    :type columns_aggregation: Optional[str], optional
    :raises HTTPException: when validation  fails
    :return: filter object with validations
    :rtype: DataFrameFilterValidator
    """
    sql_filter = DataFrameFilterValidator(
        model=model,
        raw_columns_filter=columns_filter,
        raw_rows_filter=rows_filter,
        raw_columns_aggregation=columns_aggregation,
    )
    try:
        any([
            sql_filter.valid_columns_aggregation,
            sql_filter.valid_columns_filter,
            sql_filter.valid_rows_filter,
        ])
    except FilterValidationError as exc:
        logger.debug(f"Query parameters are invalid: {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    logger.debug("Query parameters are valid.")
    return sql_filter


async def get_validated_bulk_data_json(request: Request) -> str:
    """Validates incoming json bulk data in orient=split format.

    :param request: the incoming request object
    :type request: Request
    :raises InvalidDatasetException: if data and index are inconsistent
    :raises ValidationError: if orientsplit frame can't be build from
        request body
    :return: validated json data
    :rtype: str
    """
    body = await request.body()
    bulk_data = OrientSplit.parse_obj(json.loads(body.decode("utf-8")))

    index_length = len(bulk_data.index)
    data_length = len(bulk_data.data)
    if index_length != data_length:
        detail = f"Data error: 'index' lenght: {index_length} != 'data' lenght: {data_length}"
        raise InvalidDatasetException(detail=detail)
    return bulk_data.json()


async def get_search_data_pagination_parameters(
    page_limit: Optional[int] = Query(
        default=100,
        example=100,
        gt=0,
        le=100,
    ),
    offset: Optional[int] = Query(
        default=0,
        example=100,
        ge=0,
    ),
    indexed_start_date: Optional[date] = Query(
        default=None,
        example="2023-01-01",
    ),
    indexed_end_date: Optional[date] = Query(
        default=None,
        example="2023-12-31",
    ),
) -> Tuple[int, int, Optional[date], Optional[date]]:
    if indexed_start_date and indexed_end_date:
        if indexed_start_date > indexed_end_date:
            raise HTTPException(
                status_code=422,
                detail="indexed_start_date must be before or equal to indexed_end_date",
            )
    return offset, page_limit, indexed_start_date, indexed_end_date


async def get_search_pagination_parameters(
    page_limit: Optional[int] = Query(
        default=1000,
        example=1000,
        gt=0,
        le=1000,
    ),
    offset: Optional[int] = Query(
        default=0,
        example=100,
        ge=0,
    ),
    indexed_start_date: Optional[date] = Query(
        default=None,
        example="2023-01-01",
    ),
    indexed_end_date: Optional[date] = Query(
        default=None,
        example="2023-12-31",
    ),
) -> Tuple[int, int, Optional[date], Optional[date]]:
    if indexed_start_date and indexed_end_date:
        if indexed_start_date > indexed_end_date:
            raise HTTPException(
                status_code=422,
                detail="indexed_start_date must be before or equal to indexed_end_date",
            )
    return offset, page_limit, indexed_start_date, indexed_end_date
