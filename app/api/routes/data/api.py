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

import io
import uuid
from typing import List, Optional

import pandas as pd
import pyarrow
from fastapi import APIRouter, Depends, Path, Request, Response
from fastapi.responses import JSONResponse
from fastapi_cache.decorator import cache
from loguru import logger
from pydantic import BaseModel
from starlette import status

from app.api.dependencies.request import (
    get_content_schema_version,
    validate_bulkdata_content_type,
)
from app.api.dependencies.services import (
    get_async_dataset_service,
    get_async_storage_service,
)
from app.api.dependencies.validation import (
    get_data_model,
    get_validated_bulk_data_json,
    validate_filters,
)
from app.api.routes.osdu.wpc_dataset_source import WPCDatasetSourceView
from app.api.routes.utils.api_description_helper import APIDescriptionHelper
from app.api.routes.utils.api_version import get_api_version_from_url
from app.api.routes.utils.gc_collector import with_gc_collect
from app.api.routes.utils.records import (
    dataset_id_exist,
    find_schema_versions_for_dataset_id,
    generate_dataset_urn,
    get_id_version,
)
from app.bulk_data_validation.data_validation import DataValidator
from app.core.config import get_app_settings
from app.core.helpers.cache.coder import ResponseCoder
from app.core.helpers.cache.key_builder import key_builder_using_token
from app.core.helpers.cache.settings import CACHE_DEFAULT_TTL
from app.dataframe.parquet_filter import apply_filters_from_bytes
from app.exceptions import exceptions
from app.models.data_schemas.data_schema import build_data_schema
from app.resources.filters import DataFrameFilterValidator
from app.resources.mime_types import SupportedMimeTypes
from app.services import dataset, storage


def _normalize_nan_to_none(df: pd.DataFrame) -> None:
    """Replace NaN with None in object columns.

    pd.read_json(orient='records') produces NaN for missing fields,
    while orient='split' produces None. Normalizing to None prevents
    the bulk_mode NaN filter from masking real validation errors.
    """
    obj_cols = df.select_dtypes(include=["object"]).columns
    df[obj_cols] = df[obj_cols].where(df[obj_cols].notna(), None)


class BaseDataView(object):
    def __init__(
        self,
        router: APIRouter,
        id_regex_str: str,
        bulk_dataset_prefix: str,
        record_type: str,
        specific_route_type: str = "",
        include_dataset_source_view=True,
    ) -> None:
        self._router = router
        self._id_regex_str = id_regex_str
        self._bulk_dataset_prefix = bulk_dataset_prefix
        self._record_type = record_type
        self._specific_route_type = specific_route_type
        self.description_template_roles = APIDescriptionHelper.append_manage_roles(
            "Upload the bulk data for a given `{record_type}` object by record id.<br>\
            Each update creates a new immutable dataset and a new WPC record version. \
                Dataset IDs are never reused; historical data is preserved through WPC versioning. <br> <br>\
            Use the `Content-Type` request header to specify payload and response formats \
                (`application/json` and `application/parquet` are supported).<br>\
            Use the `Accept` request header to specify content schema version \
                (example header `Accept: */*;version=1.0.0` is supported).",
        )
        self.description_template_get_data = APIDescriptionHelper.append_joined_roles(
            "Get the bulk data for a given `{record_type}` object by record id. <br><br>\
            To retrieve a specific version, append the version number to the record id \
                (e.g., `record_id:1` for version 1). Without a version suffix, returns the latest version.<br><br>\
            Use the `Accept` request header to specify content schema version \
                (example header `Accept: */*;version=1.0.0` is supported).<br><br>\
            The  `columns_filter`, `rows_filter`, and  `columns_aggregation` \
                query parameters can be used to manage data in response.<br><br>\
            Use the `orient` query parameter to select the JSON output format (`split` or `records`).",
        )
        self.description_template_get_source = APIDescriptionHelper.append_joined_roles(
            "Get the source report file for a given `{record_type}` object by record id.<br><br>\
            Datasets identifiers from the `Datasets` record's property are used as source file references.\
            If the record relates to multiple reports, the reports' source files will be zipped.",
        )
        self.bulk_dataset_regex = r"[\w\-\.]+:dataset--File.Generic:{bulk_dataset_prefix}[\w\-\d\.]+:?[\w\-\.\:\%]*"
        self.prepare_api_routes()
        if include_dataset_source_view:
            self._wpc_dataset_source_view = WPCDatasetSourceView(router, id_regex_str, specific_route_type)

    def prepare_api_routes(self) -> None:
        """Prepare and add api routes."""
        self._prepare_get_data_route()
        self._prepare_post_data_route()

    @cache(expire=CACHE_DEFAULT_TTL, coder=ResponseCoder, key_builder=key_builder_using_token)
    async def get_data(
        self,
        request: Request,
        record_id: str,
        dataset_id: str,
        dataset_service: dataset.DatasetService = Depends(get_async_dataset_service),
        storage_service: storage.StorageService = Depends(get_async_storage_service),
        df_filter: DataFrameFilterValidator = Depends(validate_filters),
        content_schema_version: str = Depends(get_content_schema_version),
    ) -> Response:
        """Get record data.

        :param request: request
        :type request: Request
        :param record_id: record id (may include version suffix like record_id:1)
        :type record_id: str
        :param dataset_id: dataset id,
        :type dataset_id: str
        :param dataset_service: dataset service
        :type dataset_service: dataset.DatasetService
        :param storage_service: storage service
        :type storage_service: storage.StorageService
        :param df_filter: dataframe filter validator
        :type df_filter: DataFrameFilterValidator
        :return: dataset data
        :rtype: Response
        """
        # Issue #707: Support versioned record IDs (e.g., record_id:1)
        # Uses OSDU's built-in WPC versioning instead of query parameter
        base_record_id, version = get_id_version(record_id)

        return await self._get_data(
            request,
            base_record_id,
            dataset_id,
            dataset_service,
            storage_service,
            df_filter,
            content_schema_version,
            version,
        )

    async def post_data(
        self,
        request: Request,
        record_id: str,
        storage_service: storage.StorageService = Depends(get_async_storage_service),
        dataset_service: dataset.DatasetService = Depends(get_async_dataset_service),
        model: BaseModel = Depends(get_data_model),
        content_schema_version: str = Depends(get_content_schema_version),
    ) -> dict:
        """Post record data.

        :param request: request
        :type request: Request
        :param record_id: record id
        :type record_id: str
        :param storage_service: storage service
        :type storage_service: storage.StorageService
        :param dataset_service: dataset service
        :type dataset_service: dataset.DatasetService
        :param model: pydantic model for validation
        :type model: BaseModel
        :raises exceptions.InvalidDatasetException: if data impossible
            to read
        :raises exceptions.DataValidationException: if data does not
            match pydantic model
        :raises exceptions.InvalidDatasetException: if data impossible
            to convert to parquet
        :return: upserted records ids
        :rtype: dict
        """
        api_version = get_api_version_from_url(request.url.path)
        logger.info(f"Post data for api version: {api_version}")

        parquet_file = await self._get_validated_payload(request, model, storage_service)

        return await self._upsert_dataset(
            request,
            record_id,
            parquet_file,
            self._bulk_dataset_prefix,
            content_schema_version,
            api_version,
            dataset_service,
            storage_service,
        )

    async def _get_data(
        self,
        request: Request,
        record_id: str,
        dataset_id: str,
        dataset_service: dataset.DatasetService = Depends(get_async_dataset_service),
        storage_service: storage.StorageService = Depends(get_async_storage_service),
        df_filter: DataFrameFilterValidator = Depends(validate_filters),
        content_schema_version: str = Depends(get_content_schema_version),
        orient: str = "split",
        version: Optional[int] = None,
    ) -> Response:
        """Get record data.

        :param request: request
        :type request: Request
        :param record_id: record id,
        :type record_id: str
        :param dataset_id: dataset id,
        :type dataset_id: str
        :param dataset_service: dataset service
        :type dataset_service: dataset.DatasetService
        :param storage_service: storage service
        :type storage_service: storage.StorageService
        :param df_filter: df filter validator
        :type df_filter: DataFrameFilterValidator
        :param orient: JSON output format ('split' or 'records')
        :type orient: str
        :param version: WPC record version (optional)
        :type version: Optional[int]
        :return: dataset data
        :rtype: Response
        """
        # Issue #707: Support retrieving historical bulk data by WPC version
        record = await storage_service.get_record(record_id, version)
        mime_type = SupportedMimeTypes.find_by_mime_type(request.headers["content-type"])
        # Aggregation results only make sense in split format (index holds the function name)
        orient = "split" if df_filter.valid_columns_aggregation else orient

        dataset_id, _ = get_id_version(dataset_id)
        ddms_datasets = record["data"].get("DDMSDatasets", [])

        if dataset_id_exist(ddms_datasets, dataset_id):
            logger.debug(f"Retrieving dataset: {dataset_id}")
            self._check_content_schema_version(content_schema_version, ddms_datasets, dataset_id)
            parquet_bytes = await dataset_service.download_file(dataset_id)

            if not parquet_bytes:
                reason = f"{dataset_id} exist in record but without content."
                logger.debug(reason)
                raise exceptions.UnprocessableContentException(
                    detail=reason,
                )

            df = apply_filters_from_bytes(parquet_bytes, df_filter)
            logger.debug(f"Dataset info: {df.size} elements; {df.columns}")

            if mime_type == SupportedMimeTypes.PARQUET:
                df.astype(str)
                response = Response(content=df.to_parquet(), media_type=SupportedMimeTypes.PARQUET.mime_type)
            else:
                response = Response(
                    content=df.to_json(orient=orient),
                    media_type=SupportedMimeTypes.JSON.mime_type,
                )
            del df
        else:
            response = JSONResponse(
                {"message": f"{dataset_id} does not exist in current record.", "reason": "Not found."},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return response

    def _handle_validation_exception(self, v_exc: Exception) -> None:
        """Parses validation exception and raises a user-friendly error."""
        error_msg = str(v_exc)

        if "JSONDecodeError" in error_msg or "Expecting value" in error_msg:
            reason = "Invalid JSON format. Please check syntax."
            logger.debug(f"Raw validation error: {error_msg}")
            raise exceptions.UnprocessableContentException(detail=reason)

        if "validation error" in error_msg and "OrientSplit" in error_msg:
            required_keys = ["columns", "index", "data"]
            missing_fields = [f"'{key}'" for key in required_keys if f"{key}\n  field required" in error_msg]

            if missing_fields:
                fields_str = ", ".join(missing_fields)
                reason = "Data error: missing required fields: {0}. For records format, wrap the data in an array [{{...}}, ...].".format(  # noqa: E501, WPS326
                    fields_str,
                )
            else:
                reason = "Data error: invalid 'split' format. Expected 'columns' (list of strings), 'index' (list of integers), and 'data' (list of arrays). For records format, use an array of objects [{{...}}, ...]."  # noqa: E501, WPS326

            logger.debug(f"Raw validation error: {error_msg}")
            raise exceptions.UnprocessableContentException(detail=reason)

        reason = f"Data error: {v_exc}"
        logger.debug(f"Raw validation error: {error_msg}")
        raise exceptions.UnprocessableContentException(detail=reason)

    @with_gc_collect
    async def _get_validated_payload(
        self,
        request: Request,
        model: BaseModel,
        storage_service: storage.StorageService,
    ) -> bytes:
        """Validates payload and returns the parquet file.

        :param request: request object
        :type request: Request
        :param model: the model
        :type model: BaseModel
        :param storage_service: storage service instance
        :type storage_service: storage.StorageService
        :raises exceptions.InvalidDatasetException: when is not possible
            to convert to parquet
        :raises exceptions.DataValidationException: when validation
            fails
        :return: validated parquet file
        :rtype: bytes
        """
        mime_type = SupportedMimeTypes.find_by_mime_type(request.headers["content-type"])
        api_version = get_api_version_from_url(request.url.path)

        data_schema = build_data_schema(model)
        data_validator = DataValidator(data_schema, storage_service, api_version)

        parquet_file = None

        try:
            if mime_type == SupportedMimeTypes.PARQUET:
                parquet_file = await request.body()
                logger.debug(pd.get_option("io.parquet.engine"))
                df = pd.read_parquet(io.BytesIO(parquet_file))

                # workaround to pass pandera validation
                # TODO remove when migration to pyarrow validation is done
                df = pd.read_json(io.StringIO(df.to_json(orient="split")), orient="split")
            else:
                validated_json, orient = await get_validated_bulk_data_json(request)
                df = pd.read_json(io.StringIO(validated_json), orient=orient)
                _normalize_nan_to_none(df)

        except (ValueError, pyarrow.lib.ArrowException) as v_exc:
            self._handle_validation_exception(v_exc)

        logger.info(f"Data has been read from {mime_type} format")

        # Use bulk_mode for relaxed validation: allows NaN in optional object fields
        # This handles DataFrame column alignment constraint in bulk ingestion
        errors = await data_validator.validate(df, bulk_mode=True)
        if errors:
            self._handle_errors(errors)

        if not parquet_file:
            try:
                df.astype(str)
                logger.debug(f"Dataset info: {df.size} elements; {df.columns}")
                parquet_file = df.to_parquet(index=False)
            except Exception as exc:  # noqa: B902
                reason = f"Parquet conversion error: {exc}"
                logger.debug(reason)
                raise exceptions.InvalidDatasetException(detail=reason)
        del df
        return parquet_file

    async def _upsert_dataset(
        self,
        request: Request,
        record_id: str,
        parquet_file: bytes,
        bulk_dataset_prefix: str,
        content_schema_version: str,
        api_version: str,
        dataset_service: dataset.DatasetService,
        storage_service: storage.StorageService,
    ) -> dict:
        """Upsert dataset via dataset service and updates wpc via storage
        service.

        :param request: the request object
        :type request: Request
        :param record_id: the record id
        :type record_id: str
        :param parquet_file: the parquet file to store
        :type parquet_file: bytes
        :param bulk_dataset_prefix: the prefix of the bulk data (aka
            content data)
        :type bulk_dataset_prefix: str
        :param content_schema_version: the content schema version
        :type content_schema_version: str
        :param api_version: the api version
        :type api_version: str
        :param dataset_service: dataset service instance
        :type dataset_service: dataset.DatasetService
        :param storage_service: storage service instance
        :type storage_service: storage.StorageService
        :return: the ddms urn of the stored parquet file
        :rtype: dict
        """
        record = await storage_service.get_record(record_id)
        data_partition_id = request.headers["data-partition-id"]
        settings = get_app_settings()

        # Removing hyphens "-" as they are not supported in register service
        entity_type = bulk_dataset_prefix.replace("-", "")
        record_data = record["data"]
        ddms_datasets = record_data.get("DDMSDatasets", [])

        # Issue #707: Always create a new dataset ID to ensure immutable versioning.
        # Each bulk data update creates a new dataset and a new WPC version.
        # Historical data is preserved through OSDU's built-in WPC versioning.
        new_dataset_id = f"{data_partition_id}:dataset--File.Generic:{bulk_dataset_prefix}-{uuid.uuid4()}"
        dataset_record_id = await dataset_service.upload_file(parquet_file, new_dataset_id, record)

        ddms_urn = generate_dataset_urn(
            ddms_id=settings.ddms_id,
            api_version=api_version,
            entity_type=f"{entity_type}data",
            wpc_id=record_id,
            dataset_id=dataset_record_id,
            content_schema_version=content_schema_version,
        )
        # Replace the existing entry for this dataset prefix instead of appending.
        # Historical versions are preserved via WPC versioning, not via array growth.
        ddms_datasets = [
            urn for urn in ddms_datasets
            if f"/{entity_type}data/" not in urn
        ]
        ddms_datasets.append(ddms_urn)
        record_data["DDMSDatasets"] = ddms_datasets
        logger.info(f"File uploaded for new immutable dataset: {new_dataset_id}")

        logger.debug(f"Dataset Id: {dataset_record_id}")
        storage_response = await storage_service.upsert_records([record])
        logger.info(f"Updated record: {storage_response}")

        return {"ddms_urn": ddms_urn}

    def _check_content_schema_version(
        self,
        content_schema_version: str,
        ddms_datasets: List[str],
        dataset_id: str,
    ) -> None:
        """Check if proper schema version requested.

        :param content_schema_version: client schema version
        :type content_schema_version: str
        :param ddms_datasets: DDMS Datasets
        :type ddms_datasets: List[str]
        :param dataset_id: dataset id
        :type dataset_id: str
        :raises exceptions.InvalidHeaderException: if client schema
            version is improper
        """
        schema_versions = list(find_schema_versions_for_dataset_id(ddms_datasets, dataset_id))
        if content_schema_version not in schema_versions:
            error_title = f"Schema version mismatch for dataset {dataset_id}:"
            error_details = f"requested {content_schema_version}, stored {schema_versions}"
            reason = f"{error_title} {error_details}"
            logger.debug(reason)
            raise exceptions.InvalidHeaderException(detail=reason)

    def _handle_errors(self, errors: dict):
        """Handle validation errors.

        :param errors: errors as dict
        :type errors: dict
        :raises exceptions.DataValidationException: when there are
            validation errors
        """
        error_case_to_message = {
            "column_in_schema": "Invalid parameters",
            "column_in_dataframe": "Mandatory parameters missing",
            "invalid_type": "Invalid type",
            "invalid_value": "Invalid value",
            "missing_records": "Missing records in storage",
        }

        errors_desc = {}
        unknown_errors = []

        for case, columns in errors.items():
            if error_case_to_message.get(case):
                errors_desc.update({error_case_to_message.get(case): columns})
            else:
                unknown_errors = [*unknown_errors, *columns]

        if unknown_errors:
            errors_desc.update({"Unknown errors": unknown_errors})

        reason = "Data validation failed."
        logger.debug(f"{reason} {errors_desc}")
        raise exceptions.DataValidationException(errors=errors_desc, detail=reason)

    def _prepare_get_data_route(self) -> None:
        """Add api route for get_data."""
        bulk_dataset_regex = self.bulk_dataset_regex.format(bulk_dataset_prefix=self._bulk_dataset_prefix)

        def validate_record_id(record_id: str = Path(default=..., pattern=self._id_regex_str)) -> str:
            """Validate if record id matches regex.

            :param record_id: record id
            :type record_id: str
            :return: record id
            :rtype: str
            """
            return record_id

        def validate_dataset_id(dataset_id: str = Path(default=..., pattern=bulk_dataset_regex)) -> str:
            """Validate if dataset id matches regex.

            :param dataset_id: dataset id
            :type dataset_id: str
            :return: dataset id
            :rtype: str
            """
            return dataset_id

        self._router.add_api_route(
            path=f"/{{record_id}}/{self._specific_route_type}data/{{dataset_id}}",
            endpoint=self.get_data,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
            description=self.description_template_get_data.format(record_type=self._record_type),
            dependencies=[
                Depends(validate_record_id),
                Depends(validate_dataset_id),
                Depends(validate_bulkdata_content_type),
            ],
        )

    def _prepare_post_data_route(self) -> None:
        """Add api route for post_data."""

        def validate_record_id(record_id: str = Path(default=..., pattern=self._id_regex_str)) -> str:
            """Validate if record id matches regex.

            :param record_id: record id
            :type record_id: str
            :return: record id
            :rtype: str
            """
            return record_id

        self._router.add_api_route(
            path=f"/{{record_id}}/{self._specific_route_type}data",
            endpoint=self.post_data,
            methods=["POST"],
            status_code=status.HTTP_200_OK,
            description=self.description_template_roles.format(record_type=self._record_type),
            dependencies=[
                Depends(validate_record_id),
                Depends(validate_bulkdata_content_type),
            ],
        )
