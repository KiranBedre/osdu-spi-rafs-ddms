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

import uuid
from contextvars import ContextVar

from fastapi import Request, Response
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)

from app.resources.common_headers import CORRELATION_ID

_correlation_id_ctx_var: ContextVar[str] = ContextVar(CORRELATION_ID, default=None)


def get_correlation_id() -> str:
    return _correlation_id_ctx_var.get()


def set_correlation_id(cid) -> None:
    _correlation_id_ctx_var.set(cid)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware to add a correlation ID to the incoming request
    object.

    The middleware intercepts incoming requests and checks if a
    correlation ID header is present. If not, it generates a new
    correlation ID in the format "rafs-ddms/{uuid}" and adds it to the
    request headers.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        correlation_id = request.headers.get(CORRELATION_ID)
        if not correlation_id:
            correlation_id = f"rafs-ddms-{uuid.uuid4()}"
            headers = dict(request.scope["headers"])
            headers[bytes(CORRELATION_ID, "utf-8")] = bytes(correlation_id, "utf-8")
            request.scope["headers"] = [(h_name, h_value) for h_name, h_value in headers.items()]

        response = await call_next(request)
        if CORRELATION_ID not in response.headers:
            response.headers[CORRELATION_ID] = correlation_id
        _correlation_id_ctx_var.set(correlation_id)
        return response
