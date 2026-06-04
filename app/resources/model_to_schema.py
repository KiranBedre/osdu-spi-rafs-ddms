# Copyright 2025 ExxonMobil Technology and Engineering Company
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

import copy
from typing import Any, Dict

import jsonref
from pydantic import BaseModel


def _deep_merge_dicts(first_dict: Dict[str, Any], second_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dicts, with second overriding first where needed."""
    merged = copy.deepcopy(first_dict)
    for prop_key, prop_value in second_dict.items():
        if prop_key in merged and isinstance(merged[prop_key], dict) and isinstance(prop_value, dict):
            merged[prop_key] = _deep_merge_dicts(merged[prop_key], prop_value)
        else:
            merged[prop_key] = copy.deepcopy(prop_value)
    return merged


def _normalize_schema(node: Any) -> Any:  # noqa: WPS231, CCR001
    """
    Recursively normalize a JSON schema node:
    - Resolve anyOf/oneOf/allOf by merging branches.
    - Ensure 'type' is inferred where missing (object/array).
    """
    # Lists: normalize elements
    if isinstance(node, list):
        return [_normalize_schema(element) for element in node]

    # Non-dict scalars: return as-is
    if not isinstance(node, dict):
        return node

    # 1) Handle combiners at this level: anyOf / oneOf / allOf
    for combiner in ("anyOf", "oneOf", "allOf"):
        if combiner in node:
            merged: Dict[str, Any] = {}
            for variant in node[combiner]:  # noqa: WPS529
                normalized_variant = _normalize_schema(variant)
                merged = _deep_merge_dicts(merged, normalized_variant)
            # After merging, treat as canonical schema for this node
            node = merged
            break  # only handle one combiner at this level

    # 2) Recursively normalize children (properties, items, etc.)
    schema_result: Dict[str, Any] = {}
    for prop_key, prop_value in node.items():
        if prop_key == "properties" and isinstance(prop_value, dict):
            schema_result[prop_key] = {
                prop_name: _normalize_schema(prop_schema) for prop_name, prop_schema in prop_value.items()
            }
        elif prop_key == "items":
            schema_result[prop_key] = _normalize_schema(prop_value)
        else:
            schema_result[prop_key] = _normalize_schema(prop_value)

    # 3) Infer type if missing
    if "type" not in schema_result:
        if "properties" in schema_result:
            schema_result["type"] = "object"
        elif "items" in schema_result:
            schema_result["type"] = "array"

    return schema_result


def build_normalized_schema_from_model(model: BaseModel) -> Dict[str, Any]:
    """
    Given a Pydantic model, return a fully expanded and normalized JSON schema:
    - All $ref resolved via jsonref
    - anyOf/oneOf/allOf merged
    - type inferred when possible
    """
    raw_schema = model.schema()
    expanded = jsonref.replace_refs(copy.deepcopy(raw_schema))
    return _normalize_schema(expanded)
