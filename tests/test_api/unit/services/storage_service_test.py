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
from unittest.mock import MagicMock, patch

import httpx
import pytest
from httpx import HTTPStatusError
from starlette import status

from app.core.config import get_app_settings
from app.exceptions.exceptions import OsduApiException
from app.models.schemas.user import User
from app.resources.common_headers import CORRELATION_ID
from app.services.osdu_clients.storage_client import StorageServiceApiClient
from app.services.storage import (
    StorageService,
    build_storage_service_exception_detail,
)
from tests.test_api.test_routes.osdu.storage_mock_objects import (
    OSDU_GENERIC_RECORD,
)


def build_reason(status_code: int, reason_detail: str, message: str):
    return json.dumps(
        {
            "code": status_code,
            "reason": reason_detail,
            "message": message,
        }
    )


@pytest.fixture
def mock_record_client():
    mock_client = MagicMock(spec=StorageServiceApiClient, instance=True)
    yield mock_client


@pytest.fixture
def mock_user():
    mock_user = MagicMock(spec=User)
    mock_user.access_token = "test_token"
    yield mock_user


@pytest.fixture
def storage_service(mock_user):
    data_partition_id = "test_partition"
    correlation_id = "test_id"
    yield StorageService(
        data_partition_id,
        get_app_settings(),
        mock_user,
        {CORRELATION_ID: correlation_id},
    )


@pytest.fixture
def mock_get_response(mock_record_client, storage_service):
    response_json = OSDU_GENERIC_RECORD.dict(exclude_none=True)
    mock_record_client.client = MagicMock(spec=httpx.AsyncClient)
    mock_record_client.get_latest_record.return_value = response_json
    mock_record_client.get_specific_record.return_value = response_json
    storage_service.storage_client = mock_record_client
    yield


@pytest.fixture
def with_patched_storage_client_error(
    storage_service,
    storage_method,
    response_code,
    response_json=None,
    response_text="",
):
    """Patch storage client to throw an error."""

    class Response(object):
        status_code = response_code
        text = response_text

        def json(_):
            raise json.decoder.JSONDecodeError(msg="", doc="", pos=1)

    error = HTTPStatusError(message="", request=object(), response=Response())
    with patch.object(storage_service.storage_client, storage_method, side_effect=error):
        yield


@pytest.fixture
def with_patched_storage_client_error_json_from_dependecy(
    storage_service,
    storage_method,
    response_code,
    response_json,
    response_text="",
):
    """Patch storage client to throw an error."""

    class Response(object):
        status_code = response_code
        text = response_text

        def json(_):
            return response_json

    error = HTTPStatusError(message="", request=object(), response=Response())
    with patch.object(storage_service.storage_client, storage_method, side_effect=error):
        yield


@pytest.mark.asyncio
async def test_get_latest_record(storage_service, mock_record_client, mock_user, mock_get_response):
    record_id = "test-id"

    record = await storage_service.get_record(record_id)

    assert record == OSDU_GENERIC_RECORD.dict(exclude_none=True)
    mock_record_client.get_latest_record.assert_called_once_with(record_id)


@pytest.mark.asyncio
async def test_get_specific_record(storage_service, mock_record_client, mock_user, mock_get_response):
    record_id = "test-id"
    version = 1

    record = await storage_service.get_record(record_id, version)

    assert record == OSDU_GENERIC_RECORD.dict(exclude_none=True)
    mock_record_client.get_specific_record.assert_called_once_with(
        record_id,
        version,
    )


@pytest.mark.asyncio
async def test_get_record_versions(storage_service, mock_record_client, mock_user):
    record_id = "test_id"
    version = 1
    response_json = {
        "recordId": record_id,
        "versions": [version],
    }
    mock_record_client.get_record_versions.return_value = response_json
    storage_service.storage_client = mock_record_client

    record = await storage_service.get_record_versions(record_id)

    assert record == response_json
    mock_record_client.get_record_versions.assert_called_once_with(record_id)


@pytest.mark.asyncio
async def test_upsert_records(storage_service, mock_record_client, mock_user):
    records = [OSDU_GENERIC_RECORD.dict(exclude_none=True)]
    response_json = {
        "recordCount": 1,
        "recordIds": [
            "test-id",
        ],
        "skippedRecordIds": [],
        "recordIdVersions": [
            "test-id:1",
        ],
    }
    mock_record_client.create_update_records.return_value = response_json
    storage_service.storage_client = mock_record_client

    record = await storage_service.upsert_records(records)

    assert record == response_json
    mock_record_client.create_update_records.assert_called_with(records)


@pytest.mark.asyncio
async def test_soft_delete_record(storage_service, mock_record_client, mock_user):
    record_id = "test_id"
    mock_record_client.soft_delete_record.return_value = None
    mock_record_client.storage_url = "https://test-url"
    storage_service.storage_client = mock_record_client

    assert await storage_service.soft_delete_record(record_id) is None

    mock_record_client.soft_delete_record.assert_called_once_with(record_id)


@pytest.mark.parametrize(
    "storage_method,response_code,expected_status_code",
    [
        ("get_latest_record", status.HTTP_400_BAD_REQUEST, status.HTTP_400_BAD_REQUEST),
        ("get_latest_record", status.HTTP_429_TOO_MANY_REQUESTS, status.HTTP_502_BAD_GATEWAY),
        ("get_latest_record", status.HTTP_500_INTERNAL_SERVER_ERROR, status.HTTP_502_BAD_GATEWAY),
    ],
)
@pytest.mark.asyncio
async def test_error_handler_get_record(
    storage_method,
    response_code,
    expected_status_code,
    storage_service,
    mock_record_client,
    mock_user,
    with_patched_storage_client_error,
):
    record_id = "test-id"

    with pytest.raises(OsduApiException) as exc:
        await storage_service.get_record(record_id)

    assert exc.value.status_code == expected_status_code
    reason = build_reason(
        status_code=response_code,
        reason_detail=build_storage_service_exception_detail("retrieve"),
        message="",
    )
    assert exc.value.detail == reason


@pytest.mark.parametrize(
    "storage_method,response_code,expected_status_code",
    [
        ("get_specific_record", status.HTTP_400_BAD_REQUEST, status.HTTP_400_BAD_REQUEST),
        ("get_specific_record", status.HTTP_429_TOO_MANY_REQUESTS, status.HTTP_502_BAD_GATEWAY),
        ("get_specific_record", status.HTTP_500_INTERNAL_SERVER_ERROR, status.HTTP_502_BAD_GATEWAY),
    ],
)
@pytest.mark.asyncio
async def test_error_handler_get_record_version(
    storage_method,
    response_code,
    expected_status_code,
    storage_service,
    mock_record_client,
    mock_user,
    with_patched_storage_client_error,
):
    record_id = "test-id"
    version = 1

    with pytest.raises(OsduApiException) as exc:
        await storage_service.get_record(record_id, version)

    assert exc.value.status_code == expected_status_code
    reason = build_reason(
        status_code=response_code,
        reason_detail=build_storage_service_exception_detail("retrieve"),
        message="",
    )
    assert exc.value.detail == reason


@pytest.mark.parametrize(
    "storage_method,response_code,expected_status_code",
    [
        ("soft_delete_record", status.HTTP_400_BAD_REQUEST, status.HTTP_400_BAD_REQUEST),
        ("soft_delete_record", status.HTTP_429_TOO_MANY_REQUESTS, status.HTTP_502_BAD_GATEWAY),
        ("soft_delete_record", status.HTTP_500_INTERNAL_SERVER_ERROR, status.HTTP_502_BAD_GATEWAY),
    ],
)
@pytest.mark.asyncio
async def test_error_handler_soft_delete_record(
    storage_method,
    response_code,
    expected_status_code,
    storage_service,
    mock_record_client,
    mock_user,
    with_patched_storage_client_error,
):
    record_id = "test-id"

    with pytest.raises(OsduApiException) as exc:
        await storage_service.soft_delete_record(record_id)

    assert exc.value.status_code == expected_status_code
    reason = build_reason(
        status_code=response_code,
        reason_detail=build_storage_service_exception_detail("delete"),
        message="",
    )
    assert exc.value.detail == reason


@pytest.mark.parametrize(
    "storage_method,response_code,expected_status_code",
    [
        ("create_update_records", status.HTTP_429_TOO_MANY_REQUESTS, status.HTTP_502_BAD_GATEWAY),
        ("create_update_records", status.HTTP_500_INTERNAL_SERVER_ERROR, status.HTTP_502_BAD_GATEWAY),
    ],
)
@pytest.mark.asyncio
async def test_error_handler_upsert_records(
    storage_method,
    response_code,
    expected_status_code,
    storage_service,
    mock_record_client,
    mock_user,
    with_patched_storage_client_error,
):
    with pytest.raises(OsduApiException) as exc:
        await storage_service.upsert_records([])

    assert exc.value.status_code == expected_status_code
    reason = build_reason(
        status_code=response_code,
        reason_detail=build_storage_service_exception_detail("upsert"),
        message="",
    )
    assert exc.value.detail == reason


@pytest.mark.parametrize(
    "storage_method,response_code,expected_status_code",
    [
        ("query_records", status.HTTP_400_BAD_REQUEST, status.HTTP_400_BAD_REQUEST),
        ("query_records", status.HTTP_404_NOT_FOUND, status.HTTP_404_NOT_FOUND),
        ("query_records", status.HTTP_429_TOO_MANY_REQUESTS, status.HTTP_502_BAD_GATEWAY),
        ("query_records", status.HTTP_500_INTERNAL_SERVER_ERROR, status.HTTP_502_BAD_GATEWAY),
    ],
)
@pytest.mark.asyncio
async def test_error_handler_query_records(
    storage_method,
    response_code,
    expected_status_code,
    storage_service,
    mock_record_client,
    mock_user,
    with_patched_storage_client_error,
):
    with pytest.raises(OsduApiException) as exc:
        await storage_service.query_records([])

    assert exc.value.status_code == expected_status_code
    reason = build_reason(
        status_code=response_code,
        reason_detail=build_storage_service_exception_detail("query"),
        message="",
    )
    assert exc.value.detail == reason


@pytest.mark.parametrize(
    "storage_method,response_code,response_json",
    [
        ("get_latest_record", status.HTTP_500_INTERNAL_SERVER_ERROR, {"code": status.HTTP_500_INTERNAL_SERVER_ERROR}),
        ("get_latest_record", status.HTTP_500_INTERNAL_SERVER_ERROR, {"code": status.HTTP_500_INTERNAL_SERVER_ERROR}),
        (
            "create_update_records",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            {"code": status.HTTP_500_INTERNAL_SERVER_ERROR},
        ),
        ("soft_delete_record", status.HTTP_500_INTERNAL_SERVER_ERROR, {"code": status.HTTP_500_INTERNAL_SERVER_ERROR}),
        ("query_records", status.HTTP_500_INTERNAL_SERVER_ERROR, {"code": status.HTTP_500_INTERNAL_SERVER_ERROR}),
    ],
)
@pytest.mark.asyncio
async def test_error_handler_message_from_service(
    storage_method,
    response_code,
    response_json,
    storage_service,
    mock_record_client,
    mock_user,
    with_patched_storage_client_error_json_from_dependecy,
):
    record_id = "test-id"

    with pytest.raises(OsduApiException) as exc:
        if storage_method == "get_latest_record":
            await storage_service.get_record(record_id)
        if storage_method == "get_specific_record":
            await storage_service.get_record(record_id, version=1)
        if storage_method == "create_update_records":
            await storage_service.upsert_records([])
        if storage_method == "soft_delete_record":
            await storage_service.soft_delete_record(record_id)
        if storage_method == "query_records":
            await storage_service.query_records([])

    assert exc.value.status_code == status.HTTP_502_BAD_GATEWAY
    assert exc.value.detail == json.dumps(response_json)
