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
from requests.exceptions import HTTPError
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api.errors.human_readable_maps import transform_to_human_readable
from app.exceptions.exceptions import OsduApiException
from app.models.schemas.errors import OsduApiErrorResponse


def format_request_exc(exc: HTTPError) -> dict:
    try:
        exc_message = json.loads(exc.response.text)
        formatted_exc = OsduApiErrorResponse.construct(
            code=exc_message.get("code") or exc.response.status_code,
            reason=exc_message.get("reason") or exc.response.reason,
            message=exc_message.get("message") or exc.response.text,
        ).dict()
    except (TypeError, json.JSONDecodeError):
        formatted_exc = OsduApiErrorResponse.construct(
            code=exc.response.status_code,
            reason=exc.response.reason,
            message=exc.response.text,
        ).dict()
    return transform_to_human_readable(formatted_exc)


async def osdu_api_http_error_handler(_: Request, exc: HTTPError) -> JSONResponse:
    return JSONResponse(
        format_request_exc(exc),
        status_code=exc.response.status_code,
    )


def format_exc(exc: HTTPStatusError) -> dict:
    try:
        exc_message = json.loads(exc.response.text)
        formatted_exc = OsduApiErrorResponse.construct(
            code=exc_message.get("code") or exc.response.status_code,
            reason=exc_message.get("reason"),
            message=exc_message.get("message") or exc.response.text,
        ).dict()
    except (TypeError, json.JSONDecodeError):
        formatted_exc = OsduApiErrorResponse.construct(
            code=exc.response.status_code,
            reason=str(exc.response.content),
            message=exc.response.text,
        ).dict()
    return transform_to_human_readable(formatted_exc)


async def osdu_api_httpx_error_handler(_: Request, exc: HTTPStatusError) -> JSONResponse:
    return JSONResponse(
        format_exc(exc),
        status_code=exc.response.status_code,
    )


async def osdu_api_custom_exc_handler(_: Request, exc: OsduApiException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        error_kwargs = {
            "code": exc.status_code,
            "reason": exc.detail.get("reason"),
            "message": exc.detail.get("message"),
        }
    else:
        error_kwargs = {
            "code": exc.status_code,
            "reason": exc.detail,
        }
    return JSONResponse(
        OsduApiErrorResponse.construct(**error_kwargs).dict(),
        status_code=exc.status_code,
    )
