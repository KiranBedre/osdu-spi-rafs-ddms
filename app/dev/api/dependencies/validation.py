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

import json
from typing import Optional

from fastapi import Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel
from starlette import status

from app.api.dependencies.request import require_data_partition_id
from app.api.dependencies.validation import get_data_model
from app.core.config import AppSettings, get_app_settings
from app.dev.api.dependencies.services import get_async_partition_service
from app.dev.core.helpers.redis_index import build_samplesanalysis_schema
from app.dev.resources.multiple_nested_filters import (
    DFMultipleNestedFilterValidator,
    FilterExamples,
)
from app.dev.services import partition
from app.resources.errors import FilterValidationError


async def validate_multiple_nested_filters(
    model: BaseModel = Depends(get_data_model),
    columns_filter: Optional[str] = Query(
        default=None,
        description="A valid json array of property names",
        example=json.dumps(FilterExamples.PROJECTION),
    ),
    rows_filter: Optional[str] = Query(
        default=None,
        description="A valid json object with property name, operator and value",
        example=json.dumps(FilterExamples.PREDICATE),
    ),
    columns_aggregation: Optional[str] = Query(
        default=None,
        description="A valid json array with property name and aggregator function",
        example=json.dumps(FilterExamples.AGGREGATION),
    ),
    rows_multiple_filter: Optional[str] = Query(
        default=None,
        description="A valid json object with combined rows filters with optional $or and $and keys",
        example=json.dumps(FilterExamples.LOGICAL_PREDICATE),
    ),
) -> DFMultipleNestedFilterValidator:
    """Validates query parameters used for dataframe filtering.

    :param model: _description_, defaults to Depends(get_data_model)
    :type model: BaseModel, optional
    :param columns_filter: _description_, defaults to
        Query(default=None, description="A valid json array of property names",
        example=json.dumps(FilterExamples.PROJECTION))
    :type columns_filter: Optional[str], optional
    :param rows_filter: _description_, defaults to
        Query(default=None, description="A valid json object with property name, operator and value",
        example=json.dumps(FilterExamples.PREDICATE))
    :type rows_filter: Optional[str], optional
    :param columns_aggregation: _description_, defaults to
        Query(default=None, description="A valid json array with property name and aggregator function",
        example=json.dumps(FilterExamples.AGGREGATION))
    :type columns_aggregation: Optional[str], optional
    :param rows_multiple_filter: _description_, defaults to
        Query(default=None, description="A valid json object with combined rows filters with optional  and  keys",
        example=json.dumps(FilterExamples.LOGICAL_PREDICATE))
    :type rows_multiple_filter: Optional[str], optional
    :raises HTTPException: _description_
    :return: _description_
    :rtype: DFMultipleNestedFilterValidator
    """
    df_filter = DFMultipleNestedFilterValidator(
        schema=model.schema(),
        raw_columns_filter=columns_filter,
        raw_rows_filter=rows_filter,
        raw_columns_aggregation=columns_aggregation,
        raw_rows_multiple_filter=rows_multiple_filter,
    )
    try:
        any([
            df_filter.valid_columns_aggregation,
            df_filter.valid_columns_filter,
            df_filter.valid_rows_filter,
            df_filter.valid_rows_multiple_filter,
        ])
    except FilterValidationError as exc:
        logger.error(f"Query parameters are invalid: {exc}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    logger.debug("Query parameters are valid.")
    return df_filter


async def get_search_wks_parameters(
    metadata: Optional[str] = Query(
        default=None,
        description="A valid json object with property name and value.",
    ),
    settings: AppSettings = Depends(get_app_settings),
) -> dict:
    if metadata and settings.redis_index_enable:
        try:
            wks_metadata = json.loads(metadata)
        except json.decoder.JSONDecodeError as exc:
            err_msg = str(exc)
            logger.error(err_msg)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

        names = {prop.as_name for prop in build_samplesanalysis_schema()}
        names.symmetric_difference_update({"SamplesAnalysisID", "SampleAnalysisTypeIDs"})
        metadata_keys = set(wks_metadata.keys())
        if not metadata_keys.intersection(names):
            err_msg = f"Properties {metadata_keys} not found in samplesanalysis redis schema: {names}"
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

        return wks_metadata


async def get_validated_partition(
    partition: str = Depends(require_data_partition_id),
    partition_service: partition.PartitionService = Depends(get_async_partition_service),
) -> str:
    if not await partition_service.partition_exist(partition):
        err_msg = f"Partition '{partition}' does not exist"
        logger.error(err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    return partition
