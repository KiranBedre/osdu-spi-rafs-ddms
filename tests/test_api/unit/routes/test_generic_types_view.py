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

from unittest.mock import AsyncMock

import pytest
from fastapi import APIRouter

from app.api.routes.common.endpoints import GenericTypesView

SAMPLE_PATHS_TO_DATA_MODEL = {
    "/data/blackoil": {
        "1.0.0": object(),
        "1.1.0": object(),
    },
    "/data/compositional": {
        "1.0.0": object(),
    },
}


def get_registered_paths(router: APIRouter) -> list[str]:
    return [route.path for route in router.routes]


def test_registers_configured_endpoint_path() -> None:
    router = APIRouter()

    GenericTypesView(
        router=router,
        endpoint_path="/analysistypes",
        paths_to_data_model={},
    )

    assert "/analysistypes" in get_registered_paths(router)


def test_supports_a_different_endpoint_path() -> None:
    router = APIRouter()

    GenericTypesView(
        router=router,
        endpoint_path="/customtypes",
        paths_to_data_model={},
    )

    assert "/customtypes" in get_registered_paths(router)


def test_rejects_empty_endpoint_path() -> None:
    with pytest.raises(
        ValueError,
        match="endpoint_path must not be empty",
    ):
        GenericTypesView(
            router=APIRouter(),
            endpoint_path="",
            paths_to_data_model={},
        )


def test_rejects_endpoint_path_without_leading_slash() -> None:
    with pytest.raises(
        ValueError,
        match="endpoint_path must start with '/'",
    ):
        GenericTypesView(
            router=APIRouter(),
            endpoint_path="analysistypes",
            paths_to_data_model={},
        )


@pytest.mark.asyncio
async def test_get_types_uses_injected_map() -> None:
    view = GenericTypesView(
        router=APIRouter(),
        endpoint_path="/analysistypes",
        paths_to_data_model=SAMPLE_PATHS_TO_DATA_MODEL,
    )
    entitlements_service = AsyncMock()

    response = await view.get_types(entitlements_service=entitlements_service)

    assert response.body is not None
    import json

    payload = json.loads(response.body)
    assert payload == {
        "blackoil": ["1.0.0", "1.1.0"],
        "compositional": ["1.0.0"],
    }
