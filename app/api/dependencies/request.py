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

from typing import Final, List, Optional

from fastapi import Header, HTTPException, Query, Request, Response
from loguru import logger
from starlette import status

from app.api.dependencies.schema_version import (
    parse_version_from_accept_header,
    set_deprecation_headers,
    validate_version_format,
)
from app.exceptions import exceptions
from app.middleware.correlation_id_middleware import set_correlation_id
from app.resources.common_headers import ACCEPT, CONTENT_TYPE, CORRELATION_ID
from app.resources.mime_types import SupportedMimeTypes

ACCEPT_HEADER: Final = "accept"


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
        supported_content_types = f"Please provide one of the next supported content types: {supported_types}"
        reason = f"The provided content-type is not supported. {supported_content_types}"
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


def get_content_schema_version(
    request: Request,
    response: Response,
    content_schema_version: Optional[str] = Query(
        None,
        description="Content schema version, e.g. `1.0.0`. Takes precedence over the Accept header.",
        example="1.0.0",
    ),
) -> str:
    """Get content schema version from query parameter or Accept header.

    Priority: content_schema_version > Accept header (deprecated).

    :param request: request
    :type request: Request
    :param response: response (used to set deprecation headers)
    :type response: Response
    :param content_schema_version: schema version query parameter
    :type content_schema_version: Optional[str]
    :raises exceptions.NotAcceptableException: if schema version hasn't
        been provided or format is invalid
    :return: schema version
    :rtype: str
    """
    if content_schema_version is not None:
        validate_version_format(content_schema_version, "?content_schema_version")
        logger.debug(f"Schema version (from ?content_schema_version): {content_schema_version}")
        return content_schema_version

    accept_header = request.headers.get(ACCEPT)

    if not accept_header:
        reason = (
            "No schema version provided."
            + " Use the ?content_schema_version= query parameter (e.g. ?content_schema_version=1.0.0)."
            + " The deprecated Accept header versioning is also still accepted."
        )
        raise exceptions.NotAcceptableException(detail=reason)

    parsed = parse_version_from_accept_header(accept_header)
    logger.debug(f"Schema version (from deprecated Accept header): {parsed}")
    set_deprecation_headers(response)
    return parsed


def get_correlation_id(request: Request):
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
