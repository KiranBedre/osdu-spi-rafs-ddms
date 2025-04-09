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
import json
from typing import Iterable, List, Optional, Tuple, TypeVar

from fastapi import Depends, HTTPException, Query, Request
from loguru import logger
from pydantic import BaseModel
from pydantic.error_wrappers import ValidationError
from starlette import status

from app.api.dependencies.request import get_content_schema_version
from app.api.dependencies.services import (
    get_async_schema_service,
    get_async_storage_service,
)
from app.api.routes.utils.api_version import get_api_version_from_url
from app.api.routes.utils.records import get_id_version
from app.exceptions.exceptions import (
    BadRequestException,
    InvalidDatasetException,
    RecordValidationException,
)
from app.models.data_schemas.base import PATHS_TO_DATA_MODEL
from app.models.data_schemas.pvt_model.base import PATHS_TO_CONTENT_PVT_MODELS
from app.models.domain.osdu import base as osdu_models_base
from app.models.schemas.osdu_storage import OsduStorageRecord
from app.models.schemas.pandas_dataframe import OrientSplit
from app.resources.errors import FilterValidationError
from app.resources.filters import DataFrameFilterValidator
from app.resources.paths import COMMON_RELATIVE_PATHS, PVTModelRelativePaths
from app.services.schema import SchemaService
from app.services.storage import StorageService

SAMPLESANALYSIS_PARENT_RECORDS_FIELD = "ParentSamplesAnalysesReports"
SAMPLESANALYSIS_TYPE_RECORD_FIELD = "SampleAnalysisTypeIDs"

Model = TypeVar("Model", bound=BaseModel)


def get_id(id_data):  # noqa: CCR001
    """Generator to get record ids from different record data field values."""
    if isinstance(id_data, str):
        yield id_data
    elif isinstance(id_data, Iterable):
        if isinstance(id_data, dict):
            for id_value in id_data.values():
                yield from get_id(id_value)
        elif isinstance(id_data, list):
            for element in id_data:
                yield from get_id(element)
        else:
            yield from id_data


async def get_all_ids_from_records(
    records: List[dict],
    fields: List[str],
) -> List[str]:
    """Get the list of all ids in the records fields.

    :param records: list of records
    :type records: List[dict]
    :param fields: list of fields to collect
    :type fields: List[str]
    :return: list of ids
    :rtype: List[str]
    """
    ids_list = []

    for record in records:
        for field in fields:
            field_data = record["data"].get(field, None)
            ids_list.extend(list(get_id(field_data)))
    return ids_list


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
    all_test_ids = await get_all_ids_from_records(records, fields)

    all_test_ids = {get_id_version(test_id)[0] for test_id in all_test_ids}

    if all_test_ids:
        logger.debug(f"The list of ids to check exist on storage: {all_test_ids}")
        storage_response = await storage_service.query_records(list(all_test_ids))
        missing_ids = storage_response["invalidRecords"]
        if missing_ids:
            error_title = "Request can't be processed due to missing referenced records."
            error_details = f"Fields checked: {fields}. Records not found: {missing_ids}"
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


def validate_record_model(record: dict, kind: str):
    """Validates given record against Osdu Model.

    :param record: record
    :type record: dict
    :param kind: kind
    :type kind: str
    :raises RuntimeError: if there is not an Osdu Model that matches
    :raises ValidationError: if matches Osdu Model but it's not
        compliant
    """
    osdu_model = osdu_models_base.IMPLEMENTED_MODELS.get(kind)  # type Model
    if not osdu_model:
        raise RuntimeError("No valid kind or not yet implemented.")
    osdu_model.parse_obj(record)


def validate_record(record: dict, valid_kinds: List[str]):
    """Validates given record.

    :param record: record
    :type record: dict
    :param valid_kinds: list of valid kinds for given endpoin
    :type valid_kinds: List[str]
    :raises RuntimeError: if custom validation fails or there is not
        Osdu Model implemented
    :raises ValidationError: if matches Osdu Model but it's not
        compliant with schema
    """
    kind = record.get("kind")
    validate_kind(kind, valid_kinds)
    validate_record_model(record, kind)


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


async def validate_records_payload(records_list: List[OsduStorageRecord], valid_kinds: List[str]) -> List[dict]:
    """Validates request payload.

    :param records_list: records list
    :type records_list: List[OsduStorageRecord]
    :param valid_kinds: list of valid (supported) kinds for given
        endpoint
    :type valid_kinds: List[str]
    :raises RecordValidationException: raises 422 if exceptions are
        found
    :return: returns the list of validated records
    :rtype: List[dict]
    """
    validated = []
    skipped = []
    for index, record in enumerate(records_list):
        record_dict = record.dict(exclude_none=True)
        try:
            validate_record(record_dict, valid_kinds)
        except RuntimeError as rexc:
            skipped.append(build_skipped_record_error(record_dict, index, rexc))
        except ValidationError as vexc:
            skipped.append(build_skipped_record_error(record_dict, index, vexc))
        except RecordValidationException as rvexc:
            skipped.append(build_skipped_record_error(record_dict, index, rvexc))
        validated.append(record_dict)

    if skipped:
        reason = f"Validation failed. Skipped records {skipped}"
        logger.debug(reason)
        raise RecordValidationException(detail=reason)

    logger.debug("Records successfully validated.")
    return validated


async def validate_coring_records_payload(records_list: List[OsduStorageRecord], **kwargs):
    return await validate_records_payload(records_list, [osdu_models_base.CORING_100_KIND])


async def validate_rocksample_records_payload(records_list: List[OsduStorageRecord], **kwargs):
    return await validate_records_payload(records_list, [osdu_models_base.ROCKSAMPLE_100_KIND])


async def validate_rocksampleanalysis_records_payload(records_list: List[OsduStorageRecord], **kwargs):
    return await validate_records_payload(records_list, [osdu_models_base.ROCKSAMPLEANALYSIS_KIND])


async def validate_pvt_records_payload(
    records_list: List[OsduStorageRecord],
    storage_service: StorageService = Depends(get_async_storage_service),
):
    records = await validate_records_payload(records_list, [osdu_models_base.PVT_KIND])
    await validate_referential_integrity(records, ["PVTTests"], storage_service)
    return records


async def validate_cce_records_payload(records_list: List[OsduStorageRecord], **kwargs):
    return await validate_records_payload(records_list, [osdu_models_base.CCE_KIND])


async def validate_dif_lib_records_payload(records_list: List[OsduStorageRecord], **kwargs):
    return await validate_records_payload(records_list, [osdu_models_base.DIF_LIB_KIND])


async def validate_transport_test_records_payload(records_list: List[OsduStorageRecord], **kwargs):
    return await validate_records_payload(records_list, [osdu_models_base.TRANSPORT_TEST_KIND])


async def validate_com_analysis_records_payload(records_list: List[OsduStorageRecord], **kwargs):
    return await validate_records_payload(records_list, [osdu_models_base.COMPOSITIONAL_ANALYSIS_KIND])


async def validate_mss_records_payload(records_list: List[OsduStorageRecord], **kwargs):
    return await validate_records_payload(records_list, [osdu_models_base.MSS_KIND])


async def validate_swelling_records_payload(records_list: List[OsduStorageRecord], **kwargs):
    return await validate_records_payload(records_list, [osdu_models_base.SWELLING_KIND])


async def validate_cvd_records_payload(records_list: List[OsduStorageRecord], **kwargs):
    return await validate_records_payload(records_list, [osdu_models_base.CVD_KIND])


async def validate_wateranalysis_records_payload(records_list: List[OsduStorageRecord], **kwargs):
    return await validate_records_payload(records_list, [osdu_models_base.WATER_ANALYSYS_KIND])


async def validate_sto_records_payload(records_list: List[OsduStorageRecord], **kwargs):
    return await validate_records_payload(records_list, [osdu_models_base.STO_KIND])


async def validate_interfacialtension_records_payload(records_list: List[OsduStorageRecord], **kwargs):
    return await validate_records_payload(records_list, [osdu_models_base.INTERFACIAL_TENSION_KIND])


async def validate_vle_records_payload(records_list: List[OsduStorageRecord], **kwargs):
    return await validate_records_payload(records_list, [osdu_models_base.VLE_KIND])


async def validate_mcm_records_payload(records_list: List[OsduStorageRecord], **kwargs):
    return await validate_records_payload(records_list, [osdu_models_base.MCM_KIND])


async def validate_slimtubetest_records_payload(records_list: List[OsduStorageRecord], **kwargs):
    return await validate_records_payload(records_list, [osdu_models_base.SLIMTUBETEST_KIND])


async def validate_samples_analyses_report_v1_payload(records_list: List[OsduStorageRecord], **kwargs):
    return await validate_records_payload(records_list, [osdu_models_base.SAMPLES_ANALYSES_REPORT_V1_KIND])


async def validate_samples_analyses_report_v2_payload(
    records_list: List[OsduStorageRecord],
    storage_service: StorageService = Depends(get_async_storage_service),
    schema_service: SchemaService = Depends(get_async_schema_service),
):
    records = await validate_osdu_wks_records(
        records_list, schema_service, [osdu_models_base.SAMPLES_ANALYSES_REPORT_KIND],
    )
    await validate_referential_integrity(records, [SAMPLESANALYSIS_TYPE_RECORD_FIELD], storage_service)
    return records


async def validate_samplesanalysis_records_v1_payload(
    records_list: List[OsduStorageRecord],
    storage_service: StorageService = Depends(get_async_storage_service),
    **kwargs,
):
    records = await validate_records_payload(records_list, [osdu_models_base.SAMPLESANALYSIS_V1_KIND])
    await validate_referential_integrity(records, [SAMPLESANALYSIS_PARENT_RECORDS_FIELD], storage_service)
    return records


async def validate_samplesanalysis_records_v2_payload(
    records_list: List[OsduStorageRecord],
    storage_service: StorageService = Depends(get_async_storage_service),
    schema_service: SchemaService = Depends(get_async_schema_service),
):
    records = await validate_osdu_wks_records(records_list, schema_service, [osdu_models_base.SAMPLESANALYSIS_KIND])
    await validate_referential_integrity(
        records, [SAMPLESANALYSIS_PARENT_RECORDS_FIELD, SAMPLESANALYSIS_TYPE_RECORD_FIELD], storage_service,
    )
    return records


async def validate_master_data_records_payload(
    records_list: List[OsduStorageRecord],
    schema_service: SchemaService,
    **kwargs,
) -> List[dict]:
    return await validate_osdu_wks_records(records_list, schema_service, osdu_models_base.MASTER_DATA_KINDS_V2)


async def validate_pvt_model_records_payload(
    records_list: List[OsduStorageRecord],
    schema_service: SchemaService,
    **kwargs,
) -> List[dict]:
    return await validate_osdu_wks_records(records_list, schema_service, osdu_models_base.PVT_MODEL_KINDS)


def get_content_model_paths(request_path: str, api_version: str) -> tuple:
    """Get the paths to search for the appropriate content model.

    :param request_path: the request path
    :type request_path: str
    :param api_version: the api version
    :type api_version: str
    :return: appropiate paths to retrieve content models
    :rtype: tuple
    """
    if "pvtmodel" in request_path:
        relative_paths = PVTModelRelativePaths()
        paths_to_content_models = PATHS_TO_CONTENT_PVT_MODELS
    else:
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
) -> Tuple[int, int]:
    return offset, page_limit


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
) -> Tuple[int, int]:
    return offset, page_limit
