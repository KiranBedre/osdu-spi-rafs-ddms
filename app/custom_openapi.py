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

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.core.settings.app import AppSettings
from app.models.schemas.osdu_storage import OsduStorageRecord
from app.models.schemas.pandas_dataframe import OrientSplit
from app.resources.load_model_example import load_data_example


def _copy_definitions_to_root(schema: dict, openapi_schema: dict) -> None:
    """Copy nested definitions to OpenAPI root for Swagger UI $ref resolution.

    Swagger UI looks for $ref: #/definitions/X at document root.
    Keeps original definitions in schema for jsonschema validation.
    """
    nested_definitions = schema.get("definitions", {})
    if nested_definitions:
        openapi_schema.setdefault("definitions", {})
        openapi_schema["definitions"].update(nested_definitions)


def _set_request_body(path_item: dict, schema: dict, example_file: str) -> None:
    """Set request body for a POST endpoint."""
    path_item["post"]["requestBody"] = {
        "content": {
            "application/json": {
                "schema": schema,
                "example": load_data_example(example_file),
            },
        },
    }


def _get_parameter_sort_key(openapi_param: dict) -> tuple:
    """Get sort key for parameter ordering: required first, then by location."""
    location_order = {"path": 0, "header": 1, "query": 2, "cookie": 3}
    is_optional = 0 if openapi_param.get("required") else 1
    location_rank = location_order.get(openapi_param.get("in", ""), 9)
    return (is_optional, location_rank, openapi_param.get("name", ""))


def _sort_parameters(openapi_schema: dict) -> None:
    """Sort parameters: required first, then by location (path, header, query)."""
    for path_item in openapi_schema.get("paths", {}).values():
        for operation in path_item.values():
            if isinstance(operation, dict) and "parameters" in operation:
                operation["parameters"].sort(key=_get_parameter_sort_key)


def get_custom_openapi_schema(app: FastAPI, settings: AppSettings) -> dict:
    """Override openapi with custom values.

    :param FastAPI app: FastAPI app
    :param AppSettings settings: App Settings
    :return dict: The openapi schema modified
    """
    custom_openapi_schema = get_openapi(
        title=settings.app_name,
        openapi_version="3.0.3",
        version=settings.app_version,
        routes=app.routes,
        description="OSDU Rock and Fluid Sample DDMS",
        license_info={
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
        },
    )
    _apply_request_body_overrides(custom_openapi_schema, settings)
    _sort_parameters(custom_openapi_schema)
    return custom_openapi_schema


def _apply_request_body_overrides(openapi_schema: dict, settings: AppSettings) -> None:
    """Apply custom request body overrides to OpenAPI schema."""
    paths = openapi_schema["paths"]
    prefix = settings.openapi_prefix

    # SamplesAnalysis data POST
    path_item = paths[f"{prefix}/v2/samplesanalysis/{{record_id}}/data/{{analysis_type}}"]
    _set_request_body(path_item, OrientSplit.schema(), "multiple_salinity.json")

    # SaturationFunctionSet data POST
    path_item = paths[f"{prefix}/v2/saturationfunctionset/{{record_id}}/data"]
    _set_request_body(path_item, OrientSplit.schema(), "saturation_function_set_post_content_example.json")

    # SamplesAnalysis record POST - preserve existing schema, add example
    path_item = paths[f"{prefix}/v2/samplesanalysis"]
    post_content = path_item["post"]["requestBody"]["content"]
    existing_schema = post_content["application/json"]["schema"]
    _set_request_body(path_item, existing_schema, "samples_analysis_v2.json")

    # MasterData record POST - fix $ref resolution
    _apply_masterdata_override(paths, prefix, openapi_schema)

    # ReservoirSimulationRockPhysicsModel data POST
    path_item = paths[f"{prefix}/v2/reservoirsimulationrockphysicsmodel/{{record_id}}/data"]
    _set_request_body(path_item, OrientSplit.schema(), "reservoir_simulation_rock_physics_content_model.json")


def _apply_masterdata_override(paths: dict, prefix: str, openapi_schema: dict) -> None:
    """Apply masterdata POST override with proper schema resolution."""
    route = f"{prefix}/v2/masterdata"
    osdu_record_schema = OsduStorageRecord.schema()
    _copy_definitions_to_root(osdu_record_schema, openapi_schema)
    array_schema = {
        "title": "MasterDataRecords",
        "description": "Master Data records payload",
        "type": "array",
        "items": osdu_record_schema,
    }
    _set_request_body(paths[route], array_schema, "master_data.json")
