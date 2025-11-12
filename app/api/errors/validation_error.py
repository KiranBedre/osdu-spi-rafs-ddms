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
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT

from app.models.schemas.errors import ValidationErrorResponse


def format_errors(errors: list) -> list:
    formatted_errors = []
    for error in errors:
        error_field = error["loc"][-1]
        if error_field == "record_id":
            pattern = error["ctx"]["pattern"]
            entity = pattern.split(":")[1]
            error_message = f'{entity} ID is not provided in expected OSDU pattern "{pattern}"'
        else:
            error_message = f'{error_field} {error["msg"]}'
        formatted_errors.append(error_message)
    return formatted_errors


async def http422_error_handler(
    _: Request,
    exc: Union[RequestValidationError, ValidationError],
) -> JSONResponse:
    return JSONResponse(
        ValidationErrorResponse.construct(
            reason="Unprocessable entity.",
            errors=format_errors(exc.errors()),
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
                }, {
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
