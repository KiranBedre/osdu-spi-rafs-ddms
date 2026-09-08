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

from fastapi import Depends
from pydantic_settings import BaseSettings

from app.api.dependencies.auth import require_authorized_user
from app.api.dependencies.request import (
    get_correlation_id,
    require_data_partition_id,
)
from app.core.config import get_app_settings, get_provider_config
from app.core.settings.app import AppSettings
from app.models.schemas.user import User
from app.providers.dependencies.blob_storage import get_blob_storage
from app.resources.common_headers import CORRELATION_ID
from app.services import dataset, entitlements, schema, search, storage


def get_async_dataset_service(
    data_partition_id: str = Depends(require_data_partition_id),
    settings: AppSettings = Depends(get_app_settings),
    user: User = Depends(require_authorized_user),
    correlation_id: str = Depends(get_correlation_id),
):
    return dataset.DatasetService(
        data_partition_id=data_partition_id,
        settings=settings,
        user=user,
        extra_headers={CORRELATION_ID: correlation_id},
    )


def get_async_storage_service(
    data_partition_id: str = Depends(require_data_partition_id),
    settings: AppSettings = Depends(get_app_settings),
    user: User = Depends(require_authorized_user),
    correlation_id: str = Depends(get_correlation_id),
):
    return storage.StorageService(
        data_partition_id=data_partition_id,
        settings=settings,
        user=user,
        extra_headers={CORRELATION_ID: correlation_id},
    )


def get_async_search_service(
    data_partition_id: str = Depends(require_data_partition_id),
    settings: AppSettings = Depends(get_app_settings),
    user: User = Depends(require_authorized_user),
    correlation_id: str = Depends(get_correlation_id),
):
    return search.SearchService(
        data_partition_id=data_partition_id,
        settings=settings,
        user=user,
        extra_headers={CORRELATION_ID: correlation_id},
    )


def get_async_schema_service(
    data_partition_id: str = Depends(require_data_partition_id),
    settings: AppSettings = Depends(get_app_settings),
    user: User = Depends(require_authorized_user),
    correlation_id: str = Depends(get_correlation_id),
):
    return schema.SchemaService(
        data_partition_id=data_partition_id,
        settings=settings,
        user=user,
        extra_headers={CORRELATION_ID: correlation_id},
    )


async def get_blob_storage_service(  # noqa: ASYNC910
    data_partition_id: str = Depends(require_data_partition_id),
    settings: AppSettings = Depends(get_app_settings),
    cloud_provider_config: BaseSettings = Depends(get_provider_config),
):
    if settings.use_blob_storage:
        return await get_blob_storage(
            data_partition_id=data_partition_id,
            settings=settings,
            cloud_provider_config=cloud_provider_config,
        )


def get_async_entitlements_service(
    data_partition_id: str = Depends(require_data_partition_id),
    settings: AppSettings = Depends(get_app_settings),
    user: User = Depends(require_authorized_user),
    correlation_id: str = Depends(get_correlation_id),
):
    return entitlements.EntitlementsService(
        data_partition_id=data_partition_id,
        settings=settings,
        user=user,
        extra_headers={CORRELATION_ID: correlation_id},
    )
