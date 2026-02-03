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
from typing import Final, List

from fastapi import Header, HTTPException, Request
from loguru import logger
from starlette import status

from app.exceptions import exceptions
from app.middleware.correlation_id_middleware import set_correlation_id
from app.resources.common_headers import ACCEPT, CONTENT_TYPE, CORRELATION_ID
from app.resources.mime_types import SupportedMimeTypes

ACCEPT_HEADER: Final = "accept"
SUPPORTED_MIME_TYPES: Final[tuple] = ("application/json", "*/*")


def require_data_partition_id(
    data_partition_id: str = Header(
        title="data-partition-id",
        openapi_examples={
            "example": {
                "value": "opendes",
            },
        },
        description="Specifies the proper data partition id",
    ),
):
    """Validate data-partition-id header with Swagger visibility.

    Note: Missing header validation returns 400 (not 422) via the custom
    exception handler in validation_error.py, since headers are request
    metadata, not entity body per RFC 4918.
    """
    return data_partition_id


def validate_content_type(request: Request, supported_types: List[str]) -> None:
    """Validate content-type.

    :param request: request
    :type request: Request
    :param supported_types: list of suppported mime types
    :type supported_types: List[str]
    :raises exceptions.InvalidHeaderException: if content type was not
        provided
    :raises exceptions.InvalidHeaderException: if content type is not
        supported
    """
    try:
        content_type = request.headers[CONTENT_TYPE]
    except KeyError:
        reason = "Content-Type header is required, but was not provided"
        logger.debug(reason)
        raise exceptions.InvalidHeaderException(detail=reason)

    if content_type not in supported_types:
        supported_content_types = (
            f"Please provide one of the next supported content types: {supported_types}"
        )
        reason = (
            f"The provided content-type is not supported. {supported_content_types}"
        )
        logger.debug(reason)
        raise exceptions.InvalidHeaderException(detail=reason)


def validate_bulkdata_content_type(request: Request) -> None:
    """Validate bulk data content-type.

    :param request: request
    :type request: Request
    :raises exceptions.InvalidHeaderException: if content type was not
        provided
    :raises exceptions.InvalidHeaderException: if content type is not
        supported
    """
    supported_types = [
        SupportedMimeTypes.JSON.mime_type,
        SupportedMimeTypes.PARQUET.mime_type,
    ]
    validate_content_type(request=request, supported_types=supported_types)


def validate_json_content_type(request: Request) -> None:
    """Validate generic application/json content-type.

    :param request: request
    :type request: Request
    :raises exceptions.InvalidHeaderException: if content type was not
        provided
    :raises exceptions.InvalidHeaderException: if content type is not
        supported
    """
    supported_types = [SupportedMimeTypes.JSON.mime_type]
    validate_content_type(request=request, supported_types=supported_types)


async def get_content_schema_version(request: Request) -> str:
    """Get content schema version from header.

    :param request: request
    :type request: Request
    :raises exceptions.InvalidHeaderException: if schema version hasn't
        been provided or schema format is invalid
    :return: schema version
    :rtype: str
    """
    accept_header = request.headers.get(ACCEPT)

    if not accept_header:
        error_title = "Missing 'Accept' header."
        example_detail = "Example: --header 'Accept: application/json;version=1.0.0'"
        error_details = f"The 'Accept' header is required to specify the schema version. {example_detail}"
        reason = f"{error_title} {error_details}"
        raise exceptions.NotAcceptableException(detail=reason)

    parts = [part.strip() for part in accept_header.lower().split(";")]
    mime_type = parts[0]

    if mime_type not in SUPPORTED_MIME_TYPES:
        error_title = "Not Acceptable."
        error_details = " ".join([
            f"The requested media type '{mime_type}' is not supported.",
            f"Supported types are: {SUPPORTED_MIME_TYPES}.",
        ])
        reason = f"{error_title} {error_details}"
        raise exceptions.NotAcceptableException(detail=reason)

    accept_header = accept_header.lower().strip()
    version_regex = r"version=(\d+\.\d+(?:\.\d+)?)"
    version_match = re.search(version_regex, accept_header)

    if not version_match:
        error_title = "No schema version specified or invalid schema format."
        example_detail = "Example: --header 'Accept: */*;version=1.0.0'"
        error_details = f"Check if the schema version is specified in the 'Accept' header. {example_detail}"
        reason = f"{error_title} {error_details}"
        raise exceptions.NotAcceptableException(detail=reason)

    content_schema_version = version_match.group(1)
    logger.debug(f"Schema version: {content_schema_version}")
    return content_schema_version


async def get_correlation_id(request: Request):
    correlation_id = request.headers.get(CORRELATION_ID)
    if not correlation_id:
        reason = f"No {CORRELATION_ID} in headers"
        logger.debug(reason)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reason,
        )
    set_correlation_id(correlation_id)
    return correlation_id
