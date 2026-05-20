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

import httpx
import pytest
from httpx import HTTPStatusError
from starlette import status

from app.exceptions.exceptions import OsduApiException
from app.services.error_handlers import (
    handle_core_services_http_status_error,
    translate_upstream_status_code,
)


def _make_status_error(status_code: int) -> HTTPStatusError:
    request = httpx.Request("GET", "http://osdu-service/api")
    response = httpx.Response(status_code, request=request)
    return HTTPStatusError(message=str(status_code), request=request, response=response)


class TestTranslateUpstreamStatusCode:
    @pytest.mark.parametrize("code", [400, 401, 403, 404, 409, 422])
    def test_passthrough_codes(self, code):
        assert translate_upstream_status_code(code) == code

    @pytest.mark.parametrize("code", [500, 502])
    def test_server_and_bad_gateway_map_to_502(self, code):
        assert translate_upstream_status_code(code) == status.HTTP_502_BAD_GATEWAY

    def test_503_maps_to_503(self):
        assert translate_upstream_status_code(503) == status.HTTP_503_SERVICE_UNAVAILABLE

    def test_504_maps_to_504(self):
        assert translate_upstream_status_code(504) == status.HTTP_504_GATEWAY_TIMEOUT

    def test_unknown_maps_to_502(self):
        assert translate_upstream_status_code(418) == status.HTTP_502_BAD_GATEWAY

    def test_424_not_returned_as_default(self):
        assert translate_upstream_status_code(500) != status.HTTP_424_FAILED_DEPENDENCY


class TestHandleCoreServicesHttpStatusError:
    @pytest.mark.asyncio
    async def test_expected_code_raises_for_status(self):
        @handle_core_services_http_status_error(expected_codes=[404])
        async def func():
            raise _make_status_error(404)

        with pytest.raises(HTTPStatusError):
            await func()

    @pytest.mark.asyncio
    async def test_upstream_500_raises_502(self):
        @handle_core_services_http_status_error(expected_codes=[404])
        async def func():
            raise _make_status_error(500)

        with pytest.raises(OsduApiException) as exc_info:
            await func()
        assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY

    @pytest.mark.asyncio
    async def test_upstream_502_raises_502(self):
        @handle_core_services_http_status_error(expected_codes=[])
        async def func():
            raise _make_status_error(502)

        with pytest.raises(OsduApiException) as exc_info:
            await func()
        assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY

    @pytest.mark.asyncio
    async def test_upstream_503_raises_503(self):
        @handle_core_services_http_status_error(expected_codes=[])
        async def func():
            raise _make_status_error(503)

        with pytest.raises(OsduApiException) as exc_info:
            await func()
        assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_upstream_504_raises_504(self):
        @handle_core_services_http_status_error(expected_codes=[])
        async def func():
            raise _make_status_error(504)

        with pytest.raises(OsduApiException) as exc_info:
            await func()
        assert exc_info.value.status_code == status.HTTP_504_GATEWAY_TIMEOUT

    @pytest.mark.asyncio
    @pytest.mark.parametrize("code", [400, 401, 403, 404, 409, 422])
    async def test_passthrough_codes_raised_unchanged(self, code):
        @handle_core_services_http_status_error(expected_codes=[])
        async def func():
            raise _make_status_error(code)

        with pytest.raises(OsduApiException) as exc_info:
            await func()
        assert exc_info.value.status_code == code

    @pytest.mark.asyncio
    async def test_unknown_code_raises_502(self):
        @handle_core_services_http_status_error(expected_codes=[])
        async def func():
            raise _make_status_error(418)

        with pytest.raises(OsduApiException) as exc_info:
            await func()
        assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY

    @pytest.mark.asyncio
    async def test_424_never_raised_for_upstream_500(self):
        @handle_core_services_http_status_error(expected_codes=[])
        async def func():
            raise _make_status_error(500)

        with pytest.raises(OsduApiException) as exc_info:
            await func()
        assert exc_info.value.status_code != status.HTTP_424_FAILED_DEPENDENCY

    @pytest.mark.asyncio
    async def test_no_exception_passes_through(self):
        @handle_core_services_http_status_error(expected_codes=[])
        async def func():
            return "ok"

        result = await func()
        assert result == "ok"
