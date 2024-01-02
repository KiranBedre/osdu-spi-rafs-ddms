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

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from httpx import HTTPStatusError
from requests.exceptions import HTTPError
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware

from app.api.errors.data_validation_error import (
    data_validation_http_error_handler,
)
from app.api.errors.http_error import http_error_handler
from app.api.errors.invalid_body_error import invalid_body_error_handler
from app.api.errors.invalid_header_error import invalid_header_error_handler
from app.api.errors.osdu_api_error import (
    osdu_api_custom_exc_handler,
    osdu_api_http_error_handler,
    osdu_api_httpx_error_handler,
)
from app.api.errors.validation_error import http422_error_handler
from app.api.routes.api import router as api_router
from app.api.routes.v1.api import router as api_router_v1
from app.api.routes.v2.api import router as api_router_v2
from app.core.config import get_app_settings
from app.core.events import create_start_app_handler, create_stop_app_handler
from app.custom_openapi import get_custom_openapi_schema
from app.exceptions.exceptions import (
    DataValidationException,
    InvalidBodyException,
    InvalidHeaderException,
    OsduApiException,
)
from app.middleware.correlation_id_middleware import CorrelationIDMiddleware
from app.providers.helpers.metric import init_metric

EXCEPTIONS_AND_HANDLERS = (
    (HTTPException, http_error_handler),
    (RequestValidationError, http422_error_handler),
    (HTTPError, osdu_api_http_error_handler),
    (HTTPStatusError, osdu_api_httpx_error_handler),
    (InvalidBodyException, invalid_body_error_handler),
    (InvalidHeaderException, invalid_header_error_handler),
    (DataValidationException, data_validation_http_error_handler),
    (OsduApiException, osdu_api_custom_exc_handler),
)


def get_application() -> FastAPI:
    """Prepare FastAPI application.

    :return: application
    :rtype: FastAPI
    """
    settings = get_app_settings()

    settings.configure_logging()

    application = FastAPI(**settings.fastapi_kwargs)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_hosts,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(CorrelationIDMiddleware)
    init_metric(application, settings)

    application.add_event_handler(
        "startup",
        create_start_app_handler(application, settings),
    )
    application.add_event_handler(
        "shutdown",
        create_stop_app_handler(application, settings),
    )

    application.include_router(api_router, prefix=f"{settings.openapi_prefix}")
    if settings.enable_api_v1:
        application.include_router(api_router_v1, prefix=f"{settings.openapi_prefix}/v1")
    application.include_router(api_router_v2, prefix=f"{settings.openapi_prefix}/v2")

    for exception, error_handler in EXCEPTIONS_AND_HANDLERS:
        application.add_exception_handler(exception, error_handler)

    application.openapi_schema = get_custom_openapi_schema(application, settings)
    return application


app = get_application()
