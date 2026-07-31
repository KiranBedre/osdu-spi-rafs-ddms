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

from collections.abc import Mapping
from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.dependencies.request import get_content_schema_version, get_response_mime_type
from app.api.dependencies.services import get_async_entitlements_service
from app.api.dependencies.validation import raise_model_not_found
from app.api.routes.utils.api_description_helper import APIDescriptionHelper
from app.api.routes.utils.api_version import get_domain_from_url
from app.models.data_schemas.base import (
    CONTENT_PATTERNS,
)
from app.services import entitlements


class GenericTypesView:
    def __init__(
        self,
        router: APIRouter,
        endpoint_path: str,
        paths_to_data_model: Mapping[str, Mapping[str, Any]],
    ) -> None:
        if not endpoint_path:
            raise ValueError("endpoint_path must not be empty")
        if not endpoint_path.startswith("/"):
            raise ValueError("endpoint_path must start with '/'")
        self._router = router
        self._endpoint_path = endpoint_path
        self._paths_to_data_model = paths_to_data_model
        self._prepare_types_route()

    async def get_types(
        self,
        entitlements_service: entitlements.EntitlementsService = Depends(get_async_entitlements_service),
    ) -> JSONResponse:
        await entitlements_service.get_groups()

        types_versions_map = {}
        for path, versions in self._paths_to_data_model.items():
            type_name = path.strip("/").split("/")[-1]
            types_versions_map[type_name] = list(versions.keys())
        return JSONResponse(content=types_versions_map)

    def _prepare_types_route(self) -> None:
        """Add API route for getting available data types and versions."""
        self._router.add_api_route(
            path=self._endpoint_path,
            endpoint=self.get_types,
            methods=["GET"],
            status_code=status.HTTP_200_OK,
            response_model=Dict[str, list],
            description=APIDescriptionHelper.append_joined_roles("Get available types."),
        )


class GenericSchemasView(object):
    def __init__(self, router: APIRouter, endpoint_config: dict):
        self._router = router
        self.endpoint_config = endpoint_config
        self._register_routes()

    async def generic_handler(
        self,
        request: Request,
        response: Response,
        mapping: Dict[str, Any],
        content_type_extractor: Callable[[Request], Dict[str, str]],
        content_schema_version: str = Depends(get_content_schema_version),
        entitlements_service: entitlements.EntitlementsService = Depends(get_async_entitlements_service),
    ) -> JSONResponse:
        """Fetches json schema for specific model and version.

        :param request: Schema handler
        :type request: Request
        :param mapping: mapping of versions to schema models
        :type mapping: Dict[str, Any]
        :param content_type_extractor: extractor for content type
        :type content_type_extractor: Callable[[Request], Dict[str, str]]
        :param content_schema_version: content schema version, defaults to Depends(get_content_schema_version)
        :type content_schema_version: str, optional
        :param entitlements_service: entitlements service instance, defaults to Depends(get_async_entitlements_service)
        :type entitlements_service: entitlements.EntitlementsService, optional
        :raises NotFoundException: if model is not implemented for given model type
        :return: The schema of the model found
        :rtype: JSONResponse
        """
        # validate user is authenticated in OSDU
        await entitlements_service.get_groups()
        get_response_mime_type(request)

        content_type = content_type_extractor(request)
        model_versions = None
        for pattern in CONTENT_PATTERNS:
            model_versions = mapping.get(pattern.format(analysistype=content_type))
            if model_versions:
                break
        if model_versions and (model := model_versions.get(content_schema_version)):  # noqa: WPS332
            return JSONResponse(
                content=model.schema(),
                headers=dict(response.headers),
            )

        available_versions = set(model_versions.keys()) if model_versions else set()
        raise_model_not_found(content_type, content_schema_version, available_versions)

    def _register_routes(self):
        self._router.add_api_route(
            path=self.endpoint_config["path"],
            endpoint=self._build_endpoint(self.endpoint_config),
            methods=self.endpoint_config.get("methods", ["GET"]),
            status_code=status.HTTP_200_OK,
            response_model=Dict[str, list],
            description=APIDescriptionHelper.append_joined_roles(
                self.endpoint_config.get("description", ""),
            ),
        )

    def _build_endpoint(self, config):
        # Closure to bind mapping and param_extractor for each endpoint
        async def get_content_schema(  # noqa: WPS430
            request: Request,
            response: Response,
            content_schema_version: Optional[str] = Depends(get_content_schema_version),
            entitlements_service: entitlements.EntitlementsService = Depends(get_async_entitlements_service),
        ):
            return await self.generic_handler(
                request,
                response,
                config["mapping"],
                config["param_extractor"],
                content_schema_version,
                entitlements_service,
            )

        return get_content_schema


def infer_content_type_from_url(request: Request) -> str:
    return get_domain_from_url(request.url.path)


def build_extractor_for_param_name(param_name: str) -> Callable:
    def extract_param(request: Request) -> str:  # noqa: WPS430
        return request.path_params.get(param_name)

    return extract_param
