from unittest.mock import MagicMock, patch

import pytest

from app.api.dependencies import services
from app.resources.common_headers import CORRELATION_ID, X_COLLABORATION


@pytest.mark.parametrize(
    "factory,constructor_patch",
    [
        (services.get_async_dataset_service, "app.api.dependencies.services.dataset.DatasetService"),
        (services.get_async_storage_service, "app.api.dependencies.services.storage.StorageService"),
        (services.get_async_search_service, "app.api.dependencies.services.search.SearchService"),
        (services.get_async_schema_service, "app.api.dependencies.services.schema.SchemaService"),
        (services.get_async_entitlements_service, "app.api.dependencies.services.entitlements.EntitlementsService"),
    ],
)
def test_service_dependencies_propagate_x_collaboration_header(factory, constructor_patch):
    header = "id=123e4567-e89b-12d3-a456-426614174051,application=rafsddms"
    with patch(constructor_patch) as constructor:
        factory(
            data_partition_id="opendes",
            settings=MagicMock(),
            user=MagicMock(),
            correlation_id="corr-id",
            x_collaboration=header,
        )

    assert constructor.call_args.kwargs["extra_headers"] == {
        CORRELATION_ID: "corr-id",
        X_COLLABORATION: header,
    }


@pytest.mark.parametrize(
    "factory,constructor_patch",
    [
        (services.get_async_dataset_service, "app.api.dependencies.services.dataset.DatasetService"),
        (services.get_async_storage_service, "app.api.dependencies.services.storage.StorageService"),
        (services.get_async_search_service, "app.api.dependencies.services.search.SearchService"),
        (services.get_async_schema_service, "app.api.dependencies.services.schema.SchemaService"),
        (services.get_async_entitlements_service, "app.api.dependencies.services.entitlements.EntitlementsService"),
    ],
)
def test_service_dependencies_skip_x_collaboration_header_when_missing(factory, constructor_patch):
    with patch(constructor_patch) as constructor:
        factory(
            data_partition_id="opendes",
            settings=MagicMock(),
            user=MagicMock(),
            correlation_id="corr-id",
            x_collaboration=None,
        )

    assert constructor.call_args.kwargs["extra_headers"] == {
        CORRELATION_ID: "corr-id",
    }
