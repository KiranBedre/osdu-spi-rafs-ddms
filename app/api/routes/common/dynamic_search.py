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

from typing import Callable, List, Optional

from fastapi import Depends, HTTPException, Request
from fastapi_cache.decorator import cache
from starlette import status

from app.api.dependencies.request import get_content_schema_version, get_depth_shift_params
from app.api.dependencies.services import (
    get_async_dataset_service,
    get_async_search_service,
    get_blob_storage_service,
)
from app.api.dependencies.validation import (
    get_orient,
    get_search_data_pagination_parameters,
    get_search_scope,
)
from app.api.routes.common.base_search import (
    GenericSearchDataView,
    PaginationParametersType,
)
from app.api.routes.utils.api_version import get_domain_from_url
from app.core.helpers.cache.coder import ResponseCoder
from app.core.helpers.cache.key_builder import key_builder_using_token
from app.core.helpers.cache.settings import CACHE_DEFAULT_TTL
from app.models.schemas.depth_shift_query import DepthShiftQueryParams
from app.models.schemas.search_scope import SearchScope
from app.providers.dependencies.blob_storage import IBlobStorage
from app.resources.filters import DataFrameFilterValidator
from app.services import dataset, search

query_params_str = [
    "The  `columns_filter`, `rows_filter`, and  `columns_aggregation` ",
    "query parameters can be used to manage data in response. <br><br> ",
    "Use `offset`, `page_limit` query parameters to control response data size. ",
    "The `page_limit` and `total_size` (found in response) <br> refers to the number of parquet ",
    "files read.<br><br>",
    "Use `indexed_start_date` and `indexed_end_date` query parameters to filter the data based on indexing ",
    "date. <br><br>  - `indexed_start_date`: Filter for data indexed on or after this date. <br><br>  ",
    "- `indexed_end_date`: Filter for data indexed on or before this date. <br><br>",
]


def append_query_params(text_parts: list[str]) -> str:
    return " ".join(text_parts + query_params_str)


def get_search_description_template(entity_name: str) -> str:
    """Returns the standard description for search endpoints."""
    return append_query_params(
        [
            f"Get `{entity_name}` records containing associated bulk data (`data.DDMSDatasets`).<br><br>",
            "Use the `content_schema_version` query parameter to specify content schema version",
            "(e.g. `?content_schema_version=1.0.0`). The `Accept` header versioning is deprecated.",
        ],
    )


def get_search_data_description_template(entity_name: str) -> str:
    """Returns the standard description for search data endpoints."""
    return append_query_params(
        [
            f"Get `{entity_name}` records bulk data content.<br><br>",
            "Use the `content_schema_version` query parameter to specify content schema version",
            "(e.g. `?content_schema_version=1.0.0`). The `Accept` header versioning is deprecated.<br><br>",
            "Use the `orient` query parameter to select the JSON output format (`split` or `records`).",
        ],
    )


class DynamicGenericSearchView(GenericSearchDataView):

    def __init__(self, router, ddms_dataset_ids_fetcher_class, endpoints_config: List[dict]):
        super().__init__(router, ddms_dataset_ids_fetcher_class, register_default_routes=False)
        self._router = router
        self._endpoints_config = endpoints_config
        self._register_dynamic_endpoints()

    def _build_extractor(self, param_name):
        if param_name is None:
            return lambda req: get_domain_from_url(req.url.path)
        return lambda req: req.path_params.get(param_name)

    def _inject_param(self, request: Request, extractor: Callable) -> str:
        return extractor(request)

    def _build_dynamic_endpoint(self, method_name: str, extractor: Callable, filter_dep):

        parent_method = getattr(self, method_name)
        uses_orient = method_name == "get_search_data"

        if uses_orient:

            async def search_endpoint(  # noqa: WPS430
                request: Request,
                df_filter: DataFrameFilterValidator = Depends(filter_dep),
                content_schema_version: str = Depends(get_content_schema_version),
                pagination_parameters: PaginationParametersType = Depends(get_search_data_pagination_parameters),
                search_scope: SearchScope = Depends(get_search_scope),
                dataset_service: dataset.DatasetService = Depends(get_async_dataset_service),
                blob_storage_service: IBlobStorage = Depends(get_blob_storage_service),
                search_service: search.SearchService = Depends(get_async_search_service),
                orient: str = Depends(get_orient),
                depth_shift_params: Optional[DepthShiftQueryParams] = Depends(get_depth_shift_params),
            ):
                if depth_shift_params is not None:
                    raise HTTPException(
                        status_code=status.HTTP_501_NOT_IMPLEMENTED,
                        detail="Depth-shift augmentation is not yet supported on the search/data endpoint.",
                    )
                dynamic_param = self._inject_param(request, extractor)
                return await parent_method(
                    request=request,
                    analysis_type=dynamic_param,
                    dataset_service=dataset_service,
                    blob_storage_service=blob_storage_service,
                    search_service=search_service,
                    df_filter=df_filter,
                    content_schema_version=content_schema_version,
                    pagination_parameters=pagination_parameters,
                    search_scope=search_scope,
                    orient=orient,
                )

        else:

            async def search_endpoint(  # noqa: WPS430, WPS440
                request: Request,
                df_filter: DataFrameFilterValidator = Depends(filter_dep),
                content_schema_version: str = Depends(get_content_schema_version),
                pagination_parameters: PaginationParametersType = Depends(get_search_data_pagination_parameters),
                search_scope: SearchScope = Depends(get_search_scope),
                dataset_service: dataset.DatasetService = Depends(get_async_dataset_service),
                blob_storage_service: IBlobStorage = Depends(get_blob_storage_service),
                search_service: search.SearchService = Depends(get_async_search_service),
            ):
                dynamic_param = self._inject_param(request, extractor)
                return await parent_method(
                    request=request,
                    analysis_type=dynamic_param,
                    dataset_service=dataset_service,
                    blob_storage_service=blob_storage_service,
                    search_service=search_service,
                    df_filter=df_filter,
                    content_schema_version=content_schema_version,
                    pagination_parameters=pagination_parameters,
                    search_scope=search_scope,
                )

        return cache(
            expire=CACHE_DEFAULT_TTL,
            coder=ResponseCoder,
            key_builder=key_builder_using_token,
        )(search_endpoint)

    def _register_dynamic_endpoints(self):
        for config in self._endpoints_config:
            extractor = self._build_extractor(config["param_name"])
            closure = self._build_dynamic_endpoint(
                method_name=config["handler"],
                extractor=extractor,
                filter_dep=config["filter_dep"],
            )

            self._router.add_api_route(
                path=config["path"],
                endpoint=closure,
                methods=["GET"],
                status_code=status.HTTP_200_OK,
                description=config.get("description", ""),
                include_in_schema=config.get("include_in_schema", True),
            )
