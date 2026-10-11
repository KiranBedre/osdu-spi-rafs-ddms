from unittest.mock import Mock

import pytest
from fastapi import APIRouter, FastAPI
from httpx import AsyncClient
from starlette.status import HTTP_200_OK

from app.core.settings.base import AppEnvTypes
from app.providers.helpers.metric import init_metric


@pytest.mark.asyncio
async def test_metrics_support_included_router():
    app = FastAPI()
    router = APIRouter()

    @router.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    app.include_router(router)
    settings = Mock(app_env=AppEnvTypes.prod, cloud_provider="azure")
    init_metric(app, settings)

    async with AsyncClient(base_url="http://testserver", app=app) as client:
        response = await client.get("/healthz")

    assert response.status_code == HTTP_200_OK
