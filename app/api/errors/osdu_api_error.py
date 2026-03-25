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

import json

from httpx import HTTPStatusError
from loguru import logger
from requests.exceptions import HTTPError
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api.errors.human_readable_maps import transform_to_human_readable
from app.exceptions.exceptions import OsduApiException
from app.models.schemas.errors import OsduApiErrorResponse

# Error response field constants
ERROR_FIELD_CODE = "code"
ERROR_FIELD_REASON = "reason"
ERROR_FIELD_MESSAGE = "message"


def format_request_exc(exc: HTTPError) -> dict:
    try:
        exc_message = json.loads(exc.response.text)
        if not isinstance(exc_message, dict):
            raise TypeError("Response is not a JSON object")
        formatted_exc = OsduApiErrorResponse.construct(
            code=exc_message.get(ERROR_FIELD_CODE) or exc.response.status_code,
            reason=exc_message.get(ERROR_FIELD_REASON) or exc.response.reason,
            message=exc_message.get(ERROR_FIELD_MESSAGE) or exc.response.text,
        ).dict()
    except (TypeError, json.JSONDecodeError):
        formatted_exc = OsduApiErrorResponse.construct(
            code=exc.response.status_code,
            reason=exc.response.reason,
            message=exc.response.text,
        ).dict()
    return transform_to_human_readable(formatted_exc)


async def osdu_api_http_error_handler(_: Request, exc: HTTPError) -> JSONResponse:
    formatted_error = format_request_exc(exc)
    error_code = formatted_error[ERROR_FIELD_CODE]
    error_reason = formatted_error[ERROR_FIELD_REASON]
    error_message = formatted_error[ERROR_FIELD_MESSAGE]
    log_message = (
        f"OSDU API HTTP error: {error_code} - {error_reason} | Message: {error_message}"
    )
    logger.error(log_message)
    return JSONResponse(
        formatted_error,
        status_code=exc.response.status_code,
    )


def format_exc(exc: HTTPStatusError) -> dict:
    try:
        exc_message = json.loads(exc.response.text)
        if not isinstance(exc_message, dict):
            raise TypeError("Response is not a JSON object")
        formatted_exc = OsduApiErrorResponse.construct(
            code=exc_message.get(ERROR_FIELD_CODE) or exc.response.status_code,
            reason=exc_message.get(ERROR_FIELD_REASON) or exc.response.reason_phrase,
            message=exc_message.get(ERROR_FIELD_MESSAGE) or exc.response.text,
        ).dict()
    except (TypeError, json.JSONDecodeError):
        formatted_exc = OsduApiErrorResponse.construct(
            code=exc.response.status_code,
            reason=exc.response.reason_phrase,
            message=exc.response.text,
        ).dict()
    return transform_to_human_readable(formatted_exc)


async def osdu_api_httpx_error_handler(_: Request, exc: HTTPStatusError) -> JSONResponse:
    formatted_error = format_exc(exc)
    error_code = formatted_error[ERROR_FIELD_CODE]
    error_reason = formatted_error[ERROR_FIELD_REASON]
    error_message = formatted_error[ERROR_FIELD_MESSAGE]
    log_message = (
        f"OSDU API HTTPX error: {error_code} - {error_reason} | Message: {error_message}"
    )
    logger.error(log_message)
    return JSONResponse(
        formatted_error,
        status_code=exc.response.status_code,
    )


async def osdu_api_custom_exc_handler(_: Request, exc: OsduApiException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        error_kwargs = {
            ERROR_FIELD_CODE: exc.status_code,
            ERROR_FIELD_REASON: exc.detail.get(ERROR_FIELD_REASON),
            ERROR_FIELD_MESSAGE: exc.detail.get(ERROR_FIELD_MESSAGE),
        }
        error_reason = exc.detail.get(ERROR_FIELD_REASON)
        error_message = exc.detail.get(ERROR_FIELD_MESSAGE)
        log_message = (
            f"OSDU API custom exception: {exc.status_code} - {error_reason} | Message: {error_message}"
        )
        logger.error(log_message)
    else:
        error_kwargs = {
            ERROR_FIELD_CODE: exc.status_code,
            ERROR_FIELD_REASON: exc.detail,
        }
        logger.error(
            f"OSDU API custom exception: {exc.status_code} - {exc.detail}",
        )
    return JSONResponse(
        OsduApiErrorResponse.construct(**error_kwargs).dict(),
        status_code=exc.status_code,
    )
