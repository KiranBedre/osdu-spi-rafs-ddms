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


def _is_non_boolean_number(raw_value: object) -> bool:
    """Check if a value is numeric while excluding booleans."""
    return isinstance(raw_value, (int, float)) and not isinstance(raw_value, bool)


def _normalize_ref_path(normalized_mapping: dict) -> None:
    """Rewrite legacy OpenAPI 2 definitions references to OpenAPI 3 components."""
    ref_path = normalized_mapping.get("$ref")
    if isinstance(ref_path, str) and ref_path.startswith("#/definitions/"):
        normalized_mapping["$ref"] = ref_path.replace(
            "#/definitions/",
            "#/components/schemas/",
            1,
        )


def _normalize_openapi_node(
    raw_node: object,
    component_schemas: dict,
) -> object:
    """Normalize OpenAPI nodes recursively."""
    normalized_node = raw_node

    if isinstance(raw_node, dict):
        normalized_node = _normalize_openapi_mapping(
            raw_node,
            component_schemas,
        )
    elif isinstance(raw_node, list):
        normalized_node = [_normalize_openapi_node(sequence_item, component_schemas) for sequence_item in raw_node]

    return normalized_node


def _normalize_openapi_mapping(
    raw_mapping: dict,
    component_schemas: dict,
) -> dict:
    """Normalize mapping nodes and promote OpenAPI 2 fields to OpenAPI 3 fields."""
    normalized_mapping = {}

    for field_name, field_value in raw_mapping.items():
        if field_name == "definitions" and isinstance(field_value, dict):
            for schema_name, schema_value in field_value.items():
                if schema_name not in component_schemas:
                    component_schemas[schema_name] = _normalize_openapi_node(
                        schema_value,
                        component_schemas,
                    )
            continue

        if field_name == "exclusiveMinimum" and _is_non_boolean_number(field_value):
            normalized_mapping["minimum"] = field_value
            normalized_mapping["exclusiveMinimum"] = True
            continue

        if field_name == "exclusiveMaximum" and _is_non_boolean_number(field_value):
            normalized_mapping["maximum"] = field_value
            normalized_mapping["exclusiveMaximum"] = True
            continue

        normalized_key = "title" if field_name == "app_name" else field_name
        normalized_mapping[normalized_key] = _normalize_openapi_node(
            field_value,
            component_schemas,
        )

    _normalize_ref_path(normalized_mapping)
    return normalized_mapping


def _normalize_openapi_schema(schema: dict) -> dict:
    """Normalize schema to the OpenAPI 3 structure used by the committed spec."""
    components = schema.setdefault("components", {}) if isinstance(schema, dict) else {}
    component_schemas = components.setdefault("schemas", {}) if isinstance(components, dict) else {}

    return _normalize_openapi_node(schema, component_schemas)


OPENAPI_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


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
    parameter_rank = _get_parameter_rank(openapi_param.get("name", ""))
    return (is_optional, location_rank, parameter_rank, openapi_param.get("name", ""))


def _get_parameter_rank(parameter_name: str) -> int:
    """Return a rank to keep query parameters grouped by purpose in Swagger."""
    parameter_rank = {
        "content_schema_version": 0,
        "basin_id": 10,
        "field_id": 11,
        "well_id": 12,
        "wellbore_id": 13,
        "depth_shift_policy": 20,
        "depth_shift_id": 21,
        "columns_filter": 30,
        "rows_filter": 31,
        "rows_multiple_filter": 32,
        "metadata": 33,
        "columns_aggregation": 34,
        "orient": 40,
        "offset": 50,
        "page_limit": 51,
        "indexed_start_date": 60,
        "indexed_end_date": 61,
    }
    return parameter_rank.get(parameter_name, 100)


def _route_record_id_info() -> dict:
    """Return mapping of URL route segment to (entity_type, route_segment) for record_id annotations."""
    return {
        "masterdata": ("master-data--Sample", "masterdata"),
        "samplesanalysis": ("work-product-component--SamplesAnalysis", "samplesanalysis"),
        "samplesanalysesreport": ("work-product-component--SamplesAnalysesReport", "samplesanalysesreport"),
        "saturationfunctionset": ("work-product-component--SaturationFunctionSet", "saturationfunctionset"),
        "reservoirsimulationrockphysicsmodel": (
            "work-product-component--ReservoirSimulationRockPhysicsModel",
            "reservoirsimulationrockphysicsmodel",
        ),
        "fluidmodel": ("work-product-component--FluidModel", "fluidmodel"),
        "depthshift": ("work-product-component--DepthShift", "depthshift"),
    }


def _build_record_id_description(entity_type: str, route_segment: str) -> str:
    """Build a tailored record_id parameter description for a specific resource endpoint.

    :param str entity_type: OSDU entity type fragment (e.g. 'master-data--Sample').
    :param str route_segment: URL route segment for examples (e.g. 'masterdata').
    :return str: HTML description string for the Swagger UI parameter.
    """
    pct = "&#37;"  # HTML entity for the percent-sign character
    return "".join(
        [
            "OSDU record identifier for a <code>{0}</code> entity.<br><br>".format(entity_type),
            "<b>URL Encoding:</b> If the record ID contains literal ",
            "<code>{0}</code> characters ".format(pct),
            "(e.g., <code>osdu:{0}:".format(entity_type),
            "7{0}2F12-A-7{0}20D_Sample_249</code>), ".format(pct),
            "the <code>{0}</code> must be ".format(pct),
            "<b>double-encoded</b> in the URL path. ",
            "This is standard HTTP behavior per ",
            "<a href='https://datatracker.ietf.org/doc/html/rfc3986'>RFC 3986</a>.",
            "<br><br><b>Examples:</b><br>",
            "<code>osdu:{0}:simple_id</code>".format(entity_type),
            "&nbsp;&nbsp;→&nbsp; <code>/v2/{0}/osdu:{1}:simple_id</code><br><br>".format(
                route_segment,
                entity_type,
            ),
            "<code>osdu:{0}:7{1}2F12-A-7{1}20D</code>".format(entity_type, pct),
            "&nbsp;&nbsp;→&nbsp; <code>/v2/{0}/".format(route_segment),
            "osdu:{0}:7{1}252F12-A-7{1}2520D</code>".format(entity_type, pct),
            "<br><br><b>Encoding reference:</b><br>",
            "<code>{0}</code> &nbsp;→&nbsp; <code>{0}25</code><br>".format(pct),
            "<code>{0}2F</code> →&nbsp; <code>{0}252F</code><br>".format(pct),
            "<code>{0}20</code> →&nbsp; <code>{0}2520</code>".format(pct),
        ],
    )


def _get_route_segment(path_key: str) -> str:
    """Extract the top-level v2/dev route segment from a path key.

    e.g. '/api/os-rafs-ddms/v2/samplesanalysis/{record_id}/...' → 'samplesanalysis'
    """
    parts = path_key.strip("/").split("/")
    for idx, part in enumerate(parts):
        if part in {"v2", "dev"} and idx + 1 < len(parts):
            return parts[idx + 1]
    return ""


def _annotate_record_id_param(openapi_param: dict, route_info: tuple) -> None:
    """Inject a tailored URL encoding description into a record_id path parameter.

    :param dict openapi_param: The OpenAPI parameter object to annotate.
    :param tuple route_info: Tuple of (entity_type, route_segment) for this resource.
    """
    is_record_id_path = openapi_param.get("name") == "record_id" and openapi_param.get("in") == "path"
    if is_record_id_path:
        entity_type, segment = route_info
        openapi_param["description"] = _build_record_id_description(entity_type, segment)


def _mark_content_schema_version_required(openapi_schema: dict) -> None:
    """Mark content_schema_version query parameter as required in the live OpenAPI schema.

    The FastAPI dependency declares it Optional to allow Accept header fallback,
    but it must be shown as required in Swagger UI.
    """
    for path_item in openapi_schema.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            for openapi_param in operation.get("parameters", []):
                if openapi_param.get("name") == "content_schema_version" and openapi_param.get("in") == "query":
                    openapi_param["required"] = True


def _is_protected_path(path_key: str) -> bool:
    """Return whether a path requires auth and partition header in Swagger UI."""
    return "/v2/" in path_key or "/dev/" in path_key


def _ensure_http_bearer_scheme(openapi_schema: dict) -> None:
    """Ensure HTTP Bearer scheme exists in OpenAPI components."""
    components = openapi_schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes.setdefault(
        "HTTPBearer",
        {
            "type": "http",
            "scheme": "bearer",
        },
    )


def _ensure_operation_security(operation: dict) -> None:
    """Ensure operation declares HTTPBearer security requirement."""
    existing = operation.setdefault("security", [])
    has_http_bearer = any(
        isinstance(security_entry, dict) and "HTTPBearer" in security_entry for security_entry in existing
    )
    if not has_http_bearer:
        existing.append({"HTTPBearer": []})


def _ensure_operation_data_partition_header(operation: dict) -> None:
    """Ensure operation declares required data-partition-id header parameter."""
    operation_params = operation.setdefault("parameters", [])
    has_partition_header = any(
        openapi_parameter.get("in") == "header" and openapi_parameter.get("name") == "data-partition-id"
        for openapi_parameter in operation_params
        if isinstance(openapi_parameter, dict)
    )
    if has_partition_header:
        return

    operation_params.append(
        {
            "in": "header",
            "name": "data-partition-id",
            "required": True,
            "description": "Specifies the proper data partition id",
            "schema": {
                "title": "data-partition-id",
                "type": "string",
                "description": "Specifies the proper data partition id",
            },
            "examples": {
                "example": {
                    "value": "opendes",
                },
            },
        },
    )


def _ensure_operation_x_collaboration_header(operation: dict) -> None:
    """Ensure operation declares optional x-collaboration header parameter."""
    operation_params = operation.setdefault("parameters", [])
    has_x_collaboration_header = any(
        openapi_parameter.get("in") == "header" and openapi_parameter.get("name") == "x-collaboration"
        for openapi_parameter in operation_params
        if isinstance(openapi_parameter, dict)
    )
    if has_x_collaboration_header:
        return

    operation_params.append(
        {
            "in": "header",
            "name": "x-collaboration",
            "required": False,
            "description": (
                "Optional namespace isolation header. " "Supports '<uuid>' or 'id=<uuid>,application=<app-name>'."
            ),
            "schema": {
                "title": "x-collaboration",
                "type": "string",
                "description": "Optional namespace isolation header.",
            },
            "examples": {
                "uuid": {
                    "value": "123e4567-e89b-12d3-a456-426614174051",
                },
                "id_with_application": {
                    "value": "id=123e4567-e89b-12d3-a456-426614174051,application=rafsddms",
                },
            },
        },
    )


def _apply_swagger_auth_partition_reqs(openapi_schema: dict) -> None:
    """Ensure protected endpoints expose auth and partition header in Swagger UI."""
    _ensure_http_bearer_scheme(openapi_schema)
    for path_key, path_item in openapi_schema.get("paths", {}).items():
        if not _is_protected_path(path_key):
            continue
        for method, operation in path_item.items():
            if method not in OPENAPI_METHODS or not isinstance(operation, dict):
                continue
            _ensure_operation_security(operation)
            _ensure_operation_data_partition_header(operation)
            _ensure_operation_x_collaboration_header(operation)


def _sort_and_annotate_parameters(openapi_schema: dict) -> None:  # noqa: WPS231
    """Sort parameters and inject tailored record_id descriptions per resource endpoint.

    Sorts: required first, then by location (path, header, query).
    Annotates: injects a URL double-encoding note into each record_id path parameter,
    with examples tailored to the specific resource entity type and URL path for that
    endpoint group (RFC 3986).
    """
    route_info_map = _route_record_id_info()
    for path_key, path_item in openapi_schema.get("paths", {}).items():
        route_info = route_info_map.get(_get_route_segment(path_key))
        for operation in path_item.values():
            if not isinstance(operation, dict) or "parameters" not in operation:
                continue
            if route_info is not None:
                for openapi_param in operation["parameters"]:
                    _annotate_record_id_param(openapi_param, route_info)
            operation["parameters"].sort(key=_get_parameter_sort_key)


_SCOPE_PARAMS_FULL = [  # noqa: WPS407
    {
        "in": "query",
        "name": "basin_id",
        "required": False,
        "description": (
            "Optional scope parameter to filter search results to a specific basin. "
            "Must be a valid OSDU record ID of kind 'master-data--Basin' "
            "(e.g., 'authority:master-data--Basin:identifier'). "
            "Scope parameters filter results hierarchically: basin -> field -> well -> wellbore."
        ),
        "schema": {
            "title": "Basin ID",
            "type": "string",
            "pattern": r"^[\w\-\.]+:master-data--Basin:[\w\-\.\:\%]+$",
        },
    },
    {
        "in": "query",
        "name": "field_id",
        "required": False,
        "description": (
            "Optional scope parameter to filter search results to a specific field. "
            "Must be a valid OSDU record ID of kind 'master-data--Field'. "
            "Used with or without basin_id scope."
        ),
        "schema": {
            "title": "Field ID",
            "type": "string",
            "pattern": r"^[\w\-\.]+:master-data--Field:[\w\-\.\:\%]+$",
        },
    },
    {
        "in": "query",
        "name": "well_id",
        "required": False,
        "description": (
            "Optional scope parameter to filter search results to a specific well. "
            "Must be a valid OSDU record ID of kind 'master-data--Well'. "
            "Used with or without basin_id/field_id scope."
        ),
        "schema": {
            "title": "Well ID",
            "type": "string",
            "pattern": r"^[\w\-\.]+:master-data--Well:[\w\-\.\:\%]+$",
        },
    },
    {
        "in": "query",
        "name": "wellbore_id",
        "required": False,
        "description": (
            "Optional scope parameter to filter search results to a specific wellbore. "
            "Must be a valid OSDU record ID of kind 'master-data--Wellbore'. "
            "Most restrictive scope parameter. "
            "Required when depth_shift_policy is provided on SamplesAnalysis search/data."
        ),
        "schema": {
            "title": "Wellbore ID",
            "type": "string",
            "pattern": r"^[\w\-\.]+:master-data--Wellbore:[\w\-\.\:\%]+$",
        },
    },
]

_SCOPE_PARAMS_GEO_CONTEXT = [  # noqa: WPS407
    {
        "in": "query",
        "name": "basin_id",
        "required": False,
        "description": (
            "Optional scope parameter to filter search results to a specific basin. "
            "Must be a valid OSDU record ID of kind 'master-data--Basin' "
            "(e.g., 'authority:master-data--Basin:identifier')."
        ),
        "schema": {
            "title": "Basin ID",
            "type": "string",
            "pattern": r"^[\w\-\.]+:master-data--Basin:[\w\-\.\:\%]+$",
        },
    },
    {
        "in": "query",
        "name": "field_id",
        "required": False,
        "description": (
            "Optional scope parameter to filter search results to a specific field. "
            "Must be a valid OSDU record ID of kind 'master-data--Field'. "
            "Used with or without basin_id scope."
        ),
        "schema": {
            "title": "Field ID",
            "type": "string",
            "pattern": r"^[\w\-\.]+:master-data--Field:[\w\-\.\:\%]+$",
        },
    },
]

_SCOPE_PARAMS_DEPTH_SHIFT = [  # noqa: WPS407
    {
        "in": "query",
        "name": "basin_id",
        "required": False,
        "description": (
            "Optional scope parameter to filter search results to a specific basin. "
            "Must be a valid OSDU record ID of kind 'master-data--Basin' "
            "(e.g., 'authority:master-data--Basin:identifier')."
        ),
        "schema": {
            "title": "Basin ID",
            "type": "string",
            "pattern": r"^[\w\-\.]+:master-data--Basin:[\w\-\.\:\%]+$",
        },
    },
    {
        "in": "query",
        "name": "field_id",
        "required": False,
        "description": (
            "Optional scope parameter to filter search results to a specific field. "
            "Must be a valid OSDU record ID of kind 'master-data--Field'. "
            "Used with or without basin_id scope."
        ),
        "schema": {
            "title": "Field ID",
            "type": "string",
            "pattern": r"^[\w\-\.]+:master-data--Field:[\w\-\.\:\%]+$",
        },
    },
    {
        "in": "query",
        "name": "wellbore_id",
        "required": False,
        "description": (
            "Optional scope parameter to filter search results to a specific wellbore. "
            "Must be a valid OSDU record ID of kind 'master-data--Wellbore'. "
            "DepthShift does not support well_id; only basin_id, field_id, and wellbore_id."
        ),
        "schema": {
            "title": "Wellbore ID",
            "type": "string",
            "pattern": r"^[\w\-\.]+:master-data--Wellbore:[\w\-\.\:\%]+$",
        },
    },
]

_DEPTH_SHIFT_PARAMS = [  # noqa: WPS407
    {
        "in": "query",
        "name": "depth_shift_policy",
        "required": False,
        "description": (
            "Depth shift resolution strategy: 'definitive' uses the sample's definitive "
            "depth shift, 'id_provided' uses the explicit depth_shift_id."
        ),
        "schema": {
            "title": "Depth Shift Policy",
            "type": "string",
            "description": (
                "Depth shift resolution strategy: 'definitive' uses the sample's definitive "
                "depth shift, 'id_provided' uses the explicit depth_shift_id."
            ),
            "enum": ["definitive", "id_provided"],
        },
    },
    {
        "in": "query",
        "name": "depth_shift_id",
        "required": False,
        "description": "DepthShift WPC record ID to apply to the response data.",
        "schema": {
            "title": "Depth Shift Id",
            "type": "string",
            "description": "DepthShift WPC record ID to apply to the response data.",
            "pattern": r"^[\w\-\.]+:work-product-component--DepthShift:[\w\-\.\:\%]+$",
        },
    },
]

_SEARCH_DATA_DEPTH_SHIFT_PATHS = frozenset(("samplesanalysis",))


def _inject_depth_shift_params_into_search_data(openapi_schema: dict) -> None:  # noqa: WPS231, CCR001
    """Add depth_shift_policy and depth_shift_id query parameters to search-data endpoints.

    The search-data endpoints for SamplesAnalysis support the same depth-shift
    augmentation as the get-data endpoint.  FastAPI does not automatically include
    these parameters in the generated schema for the search endpoint (they are
    injected at route-build time only for the get-data route).  This function adds
    them manually so that Swagger UI and API consumers see the correct contract.
    """
    for path_key, path_item in openapi_schema.get("paths", {}).items():
        route_segment = _get_route_segment(path_key)
        if route_segment not in _SEARCH_DATA_DEPTH_SHIFT_PATHS:
            continue
        if not path_key.endswith("/search/data"):
            continue
        operation = path_item.get("get")
        if not isinstance(operation, dict):
            continue
        existing_names = {op_param.get("name") for op_param in operation.get("parameters", [])}
        for ds_param in _DEPTH_SHIFT_PARAMS:
            if ds_param["name"] not in existing_names:
                operation.setdefault("parameters", []).append(ds_param)


def _annotate_depth_shift_parameter_constraints(openapi_schema: dict) -> None:
    """Ensure all depth-shift query parameters expose consistent OpenAPI constraints."""
    for path_item in openapi_schema.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            for openapi_param in operation.get("parameters", []):
                if openapi_param.get("name") != "depth_shift_id" or openapi_param.get("in") != "query":
                    continue
                openapi_param.setdefault("description", "DepthShift WPC record ID to apply to the response data.")
                schema = openapi_param.setdefault("schema", {})
                schema.setdefault("type", "string")
                schema["pattern"] = r"^[\w\-\.]+:work-product-component--DepthShift:[\w\-\.\:\%]+$"


def _inject_scope_params_into_endpoints(openapi_schema: dict) -> None:
    """Add scope parameters (basin_id, field_id, well_id, wellbore_id) to search endpoints.

    Scope parameters are injected dynamically via Depends() in the endpoint builders,
    which FastAPI's automatic OpenAPI schema generator cannot pick up at route-build time.
    This function manually adds the appropriate scope parameters to the schema based on
    the endpoint type:
    - SamplesAnalysis: all 4 scope params (basin_id, field_id, well_id, wellbore_id)
    - DepthShift: 3 scope params (basin_id, field_id, wellbore_id - NO well_id)
    - SaturationFunctionSet: 2 scope params (basin_id, field_id)
    - ReservoirSimulationRockPhysicsModel: 2 scope params (basin_id, field_id)
    """
    for path_key, path_item in openapi_schema.get("paths", {}).items():
        route_segment = _get_route_segment(path_key)

        # Determine which scope parameters to add based on route
        if route_segment == "samplesanalysis":
            scope_params = _SCOPE_PARAMS_FULL
        elif route_segment == "depthshift":
            scope_params = _SCOPE_PARAMS_DEPTH_SHIFT
        elif route_segment in ("saturationfunctionset", "reservoirsimulationrockphysicsmodel"):
            scope_params = _SCOPE_PARAMS_GEO_CONTEXT
        else:
            continue

        # Only add scope params to search endpoints
        if not path_key.endswith(("/search", "/search/", "/search/data")):
            continue

        operation = path_item.get("get")
        if not isinstance(operation, dict):
            continue

        existing_names = {op_param.get("name") for op_param in operation.get("parameters", [])}
        for scope_param in scope_params:
            if scope_param["name"] not in existing_names:
                operation.setdefault("parameters", []).append(scope_param)


def _contains_query_parameter(operation: dict, parameter_name: str) -> bool:
    return any(
        openapi_param.get("in") == "query" and openapi_param.get("name") == parameter_name
        for openapi_param in operation.get("parameters", [])
    )


def _append_unique_description_sentence(operation: dict, sentence: str) -> None:
    """Append a sentence once, preserving existing route descriptions."""
    description = operation.get("description") or ""
    if sentence in description:
        return
    normalized_description = description.rstrip()
    while normalized_description.endswith("<br><br>"):
        normalized_description = normalized_description[: -len("<br><br>")].rstrip()
    operation["description"] = (
        "{0}<br><br>{1}".format(normalized_description, sentence) if normalized_description else sentence
    )


def _enrich_depth_shift_descriptions(openapi_schema: dict) -> None:  # noqa: WPS231
    """Add explicit depth-shift and scope notes to SamplesAnalysis data endpoints."""
    for path_key, path_item in openapi_schema.get("paths", {}).items():
        route_segment = _get_route_segment(path_key)
        if route_segment != "samplesanalysis":
            continue

        get_operation = path_item.get("get")
        if not isinstance(get_operation, dict):
            continue

        has_depth_shift = _contains_query_parameter(get_operation, "depth_shift_policy") or _contains_query_parameter(
            get_operation,
            "depth_shift_id",
        )
        if not has_depth_shift:
            continue

        _append_unique_description_sentence(
            get_operation,
            "Depth-shift augmentation parameters: use <code>depth_shift_policy</code> "
            "(<code>definitive</code> or <code>id_provided</code>) and optional "
            "<code>depth_shift_id</code>.",
        )

        if path_key.endswith("/search/data"):
            _append_unique_description_sentence(
                get_operation,
                "Scope parameters filter results hierarchically by organizational level: "
                "<code>basin_id</code> (broadest), <code>field_id</code>, <code>well_id</code>, "
                "<code>wellbore_id</code> (most restrictive). Scope parameters are optional for regular search, "
                "but <code>wellbore_id</code> is required when <code>depth_shift_policy</code> is provided.",
            )


def get_custom_openapi_schema(app: FastAPI, settings: AppSettings) -> dict:
    """Override OpenAPI with custom values.

    :param FastAPI app: FastAPI app
    :param AppSettings settings: App settings
    :return dict: Modified and normalized OpenAPI schema
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
    _apply_swagger_auth_partition_reqs(custom_openapi_schema)
    _mark_content_schema_version_required(custom_openapi_schema)
    _inject_depth_shift_params_into_search_data(custom_openapi_schema)
    _inject_scope_params_into_endpoints(custom_openapi_schema)
    _annotate_depth_shift_parameter_constraints(custom_openapi_schema)
    _enrich_depth_shift_descriptions(custom_openapi_schema)
    _sort_and_annotate_parameters(custom_openapi_schema)

    return _normalize_openapi_schema(custom_openapi_schema)


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
