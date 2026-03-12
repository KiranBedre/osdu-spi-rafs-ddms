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


def _sort_and_annotate_parameters(openapi_schema: dict) -> None:
    """Sort parameters: required first, then by location (path, header, query).

    Sorts: required first, then by location (path, header, query).
    Annotates: adds URL double-encoding description to record_id path parameters
    to document the requirement when IDs contain literal percent characters (RFC 3986).
    """
    pct = "&#37;"  # HTML entity for the percent-sign character
    record_id_description = "".join(
        [
            "OSDU record identifier.<br><br>",
            "<b>URL Encoding:</b> If the record ID contains literal ",
            "<code>{0}</code> characters ".format(pct),
            "(e.g., <code>osdu:master-data--Sample:",
            "7{0}2F12-A-7{0}20D_Sample_249</code>), ".format(pct),
            "the <code>{0}</code> must be ".format(pct),
            "<b>double-encoded</b> in the URL path. ",
            "This is standard HTTP behavior per ",
            "<a href='https://datatracker.ietf.org/doc/html/rfc3986'>RFC 3986</a>.",
            "<br><br><b>Examples:</b><br>",
            "<code>osdu:...:simple_id</code>",
            "→<code>/v2/masterdata/osdu:...:simple_id</code><br><br>",
            "<code>osdu:...:7{0}2F12-A-7{0}20D</code>".format(pct),
            "&nbsp;&nbsp;→ <code>/v2/masterdata/",
            "osdu:...:7{0}252F12-A-7{0}2520D</code>".format(pct),
            "<br><br><b>Encoding reference:</b><br>",
            "<code>{0}</code> &nbsp;→&nbsp; <code>{0}25</code><br>".format(pct),
            "<code>{0}2F</code> →&nbsp; <code>{0}252F</code><br>".format(pct),
            "<code>{0}20</code> →&nbsp; <code>{0}2520</code>".format(pct),
        ],
    )

    all_operations = (
        operation
        for path_item in openapi_schema.get("paths", {}).values()
        for operation in path_item.values()
        if isinstance(operation, dict) and "parameters" in operation
    )
    for operation in all_operations:
        for openapi_param in operation["parameters"]:
            is_record_id_path = openapi_param.get("name") == "record_id" and openapi_param.get("in") == "path"
            if is_record_id_path:
                openapi_param["description"] = record_id_description
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
    _sort_and_annotate_parameters(custom_openapi_schema)
    return custom_openapi_schema


def _apply_request_body_overrides(openapi_schema: dict, settings: AppSettings) -> None:
    """Apply custom request body overrides to OpenAPI schema."""
    paths = openapi_schema["paths"]
    prefix = settings.openapi_prefix

    # SamplesAnalysis data POST
    path_key = "{0}/v2/samplesanalysis/{{record_id}}/data/{{analysis_type}}".format(
        prefix,
    )
    _set_request_body(paths[path_key], OrientSplit.schema(), "multiple_salinity.json")

    # SaturationFunctionSet data POST
    path_key = "{0}/v2/saturationfunctionset/{{record_id}}/data".format(prefix)
    _set_request_body(
        paths[path_key],
        OrientSplit.schema(),
        "saturation_function_set_post_content_example.json",
    )

    # SamplesAnalysis record POST - preserve existing schema, add example
    path_item = paths["{0}/v2/samplesanalysis".format(prefix)]
    post_content = path_item["post"]["requestBody"]["content"]
    existing_schema = post_content["application/json"]["schema"]
    _set_request_body(path_item, existing_schema, "samples_analysis_v2.json")

    # MasterData record POST - fix $ref resolution
    _apply_masterdata_override(paths, prefix, openapi_schema)

    # ReservoirSimulationRockPhysicsModel data POST
    path_key = "{0}/v2/reservoirsimulationrockphysicsmodel/{{record_id}}/data".format(
        prefix,
    )
    _set_request_body(
        paths[path_key],
        OrientSplit.schema(),
        "reservoir_simulation_rock_physics_content_model.json",
    )


def _apply_masterdata_override(
    paths: dict,
    prefix: str,
    openapi_schema: dict,
) -> None:
    """Apply masterdata POST override with proper schema resolution."""
    route = "{0}/v2/masterdata".format(prefix)
    osdu_record_schema = OsduStorageRecord.schema()
    _copy_definitions_to_root(osdu_record_schema, openapi_schema)
    array_schema = {
        "title": "MasterDataRecords",
        "description": "Master Data records payload",
        "type": "array",
        "items": osdu_record_schema,
    }
    _set_request_body(paths[route], array_schema, "master_data.json")
