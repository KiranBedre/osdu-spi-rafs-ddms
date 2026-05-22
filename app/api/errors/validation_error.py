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

from typing import Union

from fastapi.exceptions import RequestValidationError
from fastapi.openapi.constants import REF_PREFIX
from fastapi.openapi.utils import (
    validation_error_definition,
    validation_error_response_definition,
)
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_422_UNPROCESSABLE_CONTENT,
)

from app.models.schemas.errors import ValidationErrorResponse


def _format_single_error(error: dict) -> str:
    """Format a single validation error into a human-readable message."""
    error_loc = error.get("loc", [])
    error_field = error_loc[-1] if error_loc else "unknown"
    error_type = error_loc[0] if error_loc else None

    if error_field == "record_id":
        pattern = error["ctx"]["pattern"]
        entity = pattern.split(":")[1]
        return f'{entity} ID is not provided in expected OSDU pattern "{pattern}"'
    if error_type == "header" and error["msg"] == "field required":
        return f"No {error_field} in headers"
    return f'{error_field} {error["msg"]}'


def format_errors(errors: list) -> list:
    formatted_errors = []
    for error in errors:
        error_message = _format_single_error(error)
        if error_message not in formatted_errors:
            formatted_errors.append(error_message)
    return formatted_errors


def _is_header_error(errors: list) -> bool:
    """Check if all errors are for missing headers.

    Headers are request metadata, not entity body, so missing headers
    should return 400 Bad Request instead of 422 per RFC 4918.
    """
    return all(error.get("loc") and error["loc"][0] == "header" for error in errors)


async def http422_error_handler(  # noqa: ASYNC910, ASYNC124
    _: Request,
    exc: Union[RequestValidationError, ValidationError],
) -> JSONResponse:
    errors = exc.errors()

    # Return 400 for missing headers (RFC 4918: headers are request metadata)
    if _is_header_error(errors):
        return JSONResponse(  # noqa: ASYNC910
            ValidationErrorResponse.construct(
                code=HTTP_400_BAD_REQUEST,
                reason="Bad request.",
                errors=format_errors(errors),
            ).dict(),
            status_code=HTTP_400_BAD_REQUEST,
        )

    return JSONResponse(  # noqa: ASYNC910
        ValidationErrorResponse.construct(
            reason="Unprocessable entity.",
            errors=format_errors(errors),
        ).dict(),
        status_code=HTTP_422_UNPROCESSABLE_CONTENT,
    )


# TODO remove this once this fastapi issue is closed https://github.com/tiangolo/fastapi/issues/3790
# or when FastAPI version >= 0.75.2
validation_error_definition["properties"] = {
    "loc": {
        "app_name": "Location",
        "type": "array",
        "items": {
            "anyOf": [
                {
                    "type": "string",
                },
                {
                    "type": "integer",
                },
            ],
        },
    },
    "msg": {
        "app_name": "Message",
        "type": "string",
    },
    "type": {
        "app_name": "Error Type",
        "type": "string",
    },
}

validation_error_response_definition["properties"] = {
    "errors": {
        "app_name": "Errors",
        "type": "array",
        "items": {
            "$ref": "{0}ValidationError".format(REF_PREFIX),
        },
    },
}
