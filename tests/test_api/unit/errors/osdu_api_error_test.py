#  Copyright 2025 ExxonMobil Technology and Engineering Company
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

import httpx
import pytest
from httpx import HTTPStatusError

from app.api.errors.osdu_api_error import _unwrap_osdu_error, format_exc


def _make_httpx_error(status_code: int, body: dict) -> HTTPStatusError:
    request = httpx.Request("POST", "http://schema-service/schema")
    response = httpx.Response(status_code, json=body, request=request)
    return HTTPStatusError(message=str(status_code), request=request, response=response)


class TestUnwrapOsduError:
    def test_flat_format_returned_unchanged(self):
        flat = {"code": 404, "reason": "notFound", "message": "Schema is not present"}
        assert _unwrap_osdu_error(flat) == flat

    def test_nested_error_envelope_is_unwrapped(self):
        nested = {
            "error": {
                "code": 404,
                "message": "Schema is not present",
                "errors": [{"domain": "global", "reason": "notFound", "message": "Schema is not present"}],
            }
        }
        result = _unwrap_osdu_error(nested)
        assert result["code"] == 404
        assert result["message"] == "Schema is not present"
        assert result["reason"] == "notFound"

    def test_nested_error_without_errors_list(self):
        nested = {"error": {"code": 500, "message": "Internal Server Error"}}
        result = _unwrap_osdu_error(nested)
        assert result["code"] == 500
        assert result["message"] == "Internal Server Error"
        assert result["reason"] is None

    def test_non_dict_error_value_returns_original(self):
        msg = {"error": "something went wrong"}
        assert _unwrap_osdu_error(msg) == msg

    def test_no_error_key_returns_original(self):
        msg = {"status": 404}
        assert _unwrap_osdu_error(msg) == msg


class TestFormatExc:
    def test_nested_osdu_error_produces_clean_message(self):
        body = {
            "error": {
                "code": 404,
                "message": "Schema is not present",
                "errors": [{"domain": "global", "reason": "notFound", "message": "Schema is not present"}],
            }
        }
        exc = _make_httpx_error(404, body)
        result = format_exc(exc)

        assert result["code"] == 404
        assert result["message"] == "Schema is not present"
        assert isinstance(result["message"], str)
        # message must not be a raw JSON string
        with pytest.raises((json.JSONDecodeError, TypeError)):
            json.loads(result["message"])

    def test_flat_error_body_still_works(self):
        body = {"code": 404, "reason": "notFound", "message": "Schema is not present"}
        exc = _make_httpx_error(404, body)
        result = format_exc(exc)

        assert result["code"] == 404
        assert result["message"] == "Schema is not present"
