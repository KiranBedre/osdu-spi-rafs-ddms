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
from types import MappingProxyType
from typing import Final, List, Optional

from fastapi import Header, HTTPException, Query, Request, Response
from loguru import logger
from starlette import status

from app.api.dependencies.schema_version import (
    parse_version_from_accept_header,
    set_deprecation_headers,
    validate_version_format,
)
from app.api.routes.utils.records import get_id
from app.exceptions import exceptions
from app.middleware.correlation_id_middleware import set_correlation_id
from app.models.schemas.depth_shift_query import DepthShiftPolicy, DepthShiftQueryParams
from app.resources.common_headers import ACCEPT, CONTENT_TYPE, CORRELATION_ID, X_COLLABORATION
from app.resources.mime_types import SupportedMimeTypes

ACCEPT_HEADER: Final = "accept"
DEPTH_SHIFT_ID_PATTERN: Final = r"^[\w\-\.]+:work-product-component--DepthShift:[\w\-\.\:\%]+$"
SCOPE_PARAM_PATTERNS: Final = MappingProxyType(
    {
        "basin_id": r"^[\w\-\.]+:master-data--Basin:[\w\-\.\:\%]+$",
        "field_id": r"^[\w\-\.]+:master-data--Field:[\w\-\.\:\%]+$",
        "well_id": r"^[\w\-\.]+:master-data--Well:[\w\-\.\:\%]+$",
        "wellbore_id": r"^[\w\-\.]+:master-data--Wellbore:[\w\-\.\:\%]+$",
    },
)


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
        raise exceptions.UnsupportedMediaTypeException(detail=reason)


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
        validate_version_format(content_schema_version, "content_schema_version")
        logger.debug(f"Schema version (from content_schema_version): {content_schema_version}")
        return content_schema_version

    accept_header = request.headers.get(ACCEPT)

    if not accept_header:
        reason = (
            "No schema version provided."
            + " Use the content_schema_version query parameter (e.g. ?content_schema_version=1.0.0)."
            + " The deprecated Accept header versioning is also still accepted (e.g. Accept: */*;version=1.0.0)."
        )
        raise exceptions.NotAcceptableException(detail=reason)

    parsed = parse_version_from_accept_header(accept_header)
    logger.debug(f"Schema version (from deprecated Accept header): {parsed}")
    set_deprecation_headers(response)
    return parsed


def get_response_mime_type(request: Request) -> SupportedMimeTypes:
    """Determine response MIME type from the Accept header.

    Iterates comma-separated media ranges in the Accept header, strips
    quality and extension parameters, and returns the first supported
    MIME type.  Defaults to JSON when the header is absent or ``*/*``.
    Raises 406 if an explicit unsupported MIME type is requested.

    :param request: request
    :type request: Request
    :return: resolved MIME type (JSON or PARQUET)
    :rtype: SupportedMimeTypes
    :raises exceptions.NotAcceptableException: if Accept specifies only
        unsupported MIME types
    """
    accept_header = request.headers.get(ACCEPT, "")
    if not accept_header or accept_header.strip() == "*/*":
        logger.debug("Response MIME type defaulting to application/json")
        return SupportedMimeTypes.JSON

    for media_range in accept_header.split(","):
        mime_part = media_range.split(";")[0].strip().lower()
        if mime_part in {"*/*", ""}:
            logger.debug("Response MIME type defaulting to application/json")
            return SupportedMimeTypes.JSON
        mime_type = SupportedMimeTypes.find_by_mime_type(mime_part)
        if mime_type is not None:
            logger.debug(f"Response MIME type from Accept header: {mime_type.mime_type}")
            return mime_type

    first_mime = accept_header.split(",")[0].split(";")[0].strip()
    supported = "('application/json', 'application/x-parquet', '*/*')"
    reason = (
        "Not Acceptable."
        + f" The requested media type '{first_mime}' is not supported."
        + f" Supported types are: {supported}."
    )
    logger.debug(reason)
    raise exceptions.NotAcceptableException(detail=reason)


def get_depth_shift_params(  # noqa: WPS238
    depth_shift_id: Optional[str] = Query(
        default=None,
        description="DepthShift WPC record ID to apply to the response data.",
    ),
    depth_shift_policy: Optional[str] = Query(
        default=None,
        description=(
            "Depth shift resolution strategy: 'definitive' uses the sample's definitive depth shift, "
            + "'id_provided' uses the explicit depth_shift_id."
        ),
    ),
) -> Optional[DepthShiftQueryParams]:
    """Parse and validate depth-shift query parameters.

    Depth-shift application is always intentional. No default policy.
    Absence of ``depth_shift_policy`` means original depths only.

    Validation matrix:

    - No params → return None (no shift, original depths only)
    - ``depth_shift_policy=definitive`` → resolve WPC from Sample definitive reference
    - ``depth_shift_policy=id_provided`` + ``depth_shift_id`` → apply explicit WPC ID
    - ``depth_shift_id`` without ``depth_shift_policy`` → 400 (must be explicit)
    - ``depth_shift_policy=id_provided`` without ``depth_shift_id`` → 400
    - ``depth_shift_policy=definitive`` + ``depth_shift_id`` → 400
    - invalid ``depth_shift_policy`` value → 400

    :param depth_shift_id: DepthShift WPC record ID
    :type depth_shift_id: Optional[str]
    :param depth_shift_policy: depth shift resolution strategy
    :type depth_shift_policy: Optional[str]
    :return: validated params, or None
    :rtype: Optional[DepthShiftQueryParams]
    :raises HTTPException: 400 on any invalid combination
    """
    _validate_depth_shift_params(depth_shift_id, depth_shift_policy)

    if not depth_shift_policy:
        return None

    normalized_depth_shift_id = get_id(depth_shift_id) if depth_shift_id else None

    return DepthShiftQueryParams(
        depth_shift_id=normalized_depth_shift_id,
        depth_shift_policy=depth_shift_policy,
    )


def _raise_bad_depth_shift_request(detail: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail,
    )


def _validate_depth_shift_params(depth_shift_id: Optional[str], depth_shift_policy: Optional[str]) -> None:
    _validate_depth_shift_policy_value(depth_shift_policy)

    if not depth_shift_policy:
        if depth_shift_id:
            _raise_bad_depth_shift_request("'depth_shift_id' requires 'depth_shift_policy=id_provided' to be explicit.")
        return

    _validate_depth_shift_param_combination(depth_shift_id, depth_shift_policy)
    _validate_depth_shift_id_format(depth_shift_id)


def _validate_depth_shift_policy_value(depth_shift_policy: Optional[str]) -> None:
    if not depth_shift_policy:
        return

    valid_policies = tuple(policy.value for policy in DepthShiftPolicy)
    if depth_shift_policy not in valid_policies:
        _raise_bad_depth_shift_request(
            "Invalid 'depth_shift_policy' value '{0}'. Must be one of: {1}.".format(
                depth_shift_policy,
                list(valid_policies),
            ),
        )


def _validate_depth_shift_param_combination(depth_shift_id: Optional[str], depth_shift_policy: str) -> None:
    if depth_shift_policy == "definitive" and depth_shift_id:
        _raise_bad_depth_shift_request("'depth_shift_id' must not be supplied when 'depth_shift_policy=definitive'.")

    if depth_shift_policy == "id_provided" and not depth_shift_id:
        _raise_bad_depth_shift_request("'depth_shift_policy=id_provided' requires 'depth_shift_id'.")


def _validate_depth_shift_id_format(depth_shift_id: Optional[str]) -> None:
    if depth_shift_id and not re.match(DEPTH_SHIFT_ID_PATTERN, depth_shift_id):
        _raise_bad_depth_shift_request(f"Invalid 'depth_shift_id' format. Expected pattern: {DEPTH_SHIFT_ID_PATTERN}.")


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


def get_x_collaboration_header(
    x_collaboration: Optional[str] = Header(None, alias=X_COLLABORATION),
) -> Optional[str]:
    return x_collaboration


def validate_scope_parameter(param_name: str, param_value: Optional[str]) -> None:
    """Validate a scope parameter (basin_id, field_id, well_id, wellbore_id).

    Scope parameters must be valid OSDU record IDs of the expected kind.

    :param param_name: parameter name (e.g., 'basin_id')
    :type param_name: str
    :param param_value: parameter value
    :type param_value: Optional[str]
    :raises HTTPException: 400 if value is invalid
    """
    if not param_value:
        return

    expected_pattern = SCOPE_PARAM_PATTERNS.get(param_name)
    if expected_pattern is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported scope parameter '{param_name}'.",
        )

    if not re.match(expected_pattern, param_value):
        detail = "Invalid '{0}' format. Expected OSDU record ID matching {1}. Got: {2}".format(
            param_name,
            expected_pattern,
            param_value,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )
