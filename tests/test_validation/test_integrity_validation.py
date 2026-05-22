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

import pytest
from fastapi import HTTPException
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT

from app.api.dependencies.validation import (
    validate_ids_from_records,
    validate_referential_integrity,
)
from tests.test_api.test_routes.data.data_mock_objects import StorageService
from tests.test_validation.test_data import (
    EXPECTED_IDS_LIST,
    TEST_ID_MISSING_FIELD,
    TEST_IDS_FIELDS,
    TEST_RECORD,
)


@pytest.mark.asyncio
async def test_validate_ids_from_records():
    assert None is validate_ids_from_records([TEST_RECORD], TEST_IDS_FIELDS)


@pytest.mark.asyncio
async def test_validate_ids_from_records_raises(mocker):
    with pytest.raises(HTTPException) as exc_info:
        validate_ids_from_records(
            [TEST_RECORD],
            TEST_ID_MISSING_FIELD,
        )

    assert exc_info.value.status_code == HTTP_422_UNPROCESSABLE_CONTENT

    expected_response_detail = ["Missing MissingField in index 0"]
    assert exc_info.value.detail == expected_response_detail


@pytest.mark.asyncio
async def test_validate_referential_integrity(mocker):
    mock_get_storage_service = StorageService(None, query_records_response={"invalidRecords": [EXPECTED_IDS_LIST]})
    with pytest.raises(HTTPException) as exc_info:
        await validate_referential_integrity(
            [TEST_RECORD],
            TEST_IDS_FIELDS,
            mock_get_storage_service,
        )

    assert exc_info.value.status_code == HTTP_422_UNPROCESSABLE_CONTENT

    error_title = "Request can't be processed due to missing referenced records."
    error_details = f"Records not found: [{EXPECTED_IDS_LIST}]"
    expected_response_detail = f"{error_title} {error_details}"
    assert exc_info.value.detail == expected_response_detail

    mock_get_storage_service = StorageService(None, query_records_response={"invalidRecords": []})
    get_all_ids_from_records = mocker.patch("app.api.dependencies.validation.get_all_ids_from_records")
    await validate_referential_integrity(
        [TEST_RECORD],
        TEST_IDS_FIELDS,
        mock_get_storage_service,
    )

    get_all_ids_from_records.assert_called_once_with([TEST_RECORD])
