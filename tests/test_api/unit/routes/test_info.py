#  Copyright 2026 ExxonMobil Technology and Engineering Company
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

"""Unit tests for the /info endpoint."""

import pytest
from httpx import AsyncClient
from starlette import status

from app.core.config import get_app_settings
from app.main import app


@pytest.mark.asyncio
async def test_get_info_returns_app_settings():
    settings = get_app_settings()

    async with AsyncClient(base_url="http://testserver", app=app) as client:
        response = await client.get(f"{settings.openapi_prefix}/info")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["name"] == settings.app_name
    assert body["app_version"] == settings.app_version
    assert body["build_time"] == settings.build_date
    assert body["branch"] == settings.commit_branch
    assert body["commit_id"] == settings.commit_id
    assert body["commit_message"] == settings.commit_message
    assert body["release_version"] == settings.release_version
