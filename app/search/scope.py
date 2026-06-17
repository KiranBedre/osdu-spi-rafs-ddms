# noqa: WPS202
#  Copyright 2026 ExxonMobil Technology and Engineering Company
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

from types import MappingProxyType
from typing import Dict, List, Optional, Tuple

from app.models.schemas.search_scope import SearchScope

_SCOPE_PROFILE_DEFAULT = "default"
_SCOPE_PROFILE_SAMPLESANALYSIS = "samplesanalysis"
SCOPE_PROFILE_SAMPLE = "sample"
SCOPE_PROFILE_DEPTH_SHIFT = "depth_shift"
_SCOPE_PROFILE_SATURATION_FUNCTION_SET = "saturation_function_set"
_SCOPE_PROFILE_RES_SIM_ROCK_PHYSICS = "res_sim_rock_physics"

SCOPE_PROFILE_DEFAULT = _SCOPE_PROFILE_DEFAULT
SCOPE_PROFILE_SAMPLESANALYSIS = _SCOPE_PROFILE_SAMPLESANALYSIS
SCOPE_PROFILE_SATURATION_FUNCTION_SET = _SCOPE_PROFILE_SATURATION_FUNCTION_SET
SCOPE_PROFILE_RES_SIM_ROCK_PHYSICS = _SCOPE_PROFILE_RES_SIM_ROCK_PHYSICS

# Scope keys that cannot be queried directly on SamplesAnalysis records.
# They are resolved via hop(s) against master-data (Wellbore and/or Sample).
SAMPLE_HOP_SCOPE_KEYS: frozenset = frozenset(("basin_id", "field_id", "wellbore_id", "well_id"))

_QueryFieldPaths = Tuple[str, ...]
_ScopeQueryMap = Dict[str, _QueryFieldPaths]

SEARCH_SCOPE_QUERY_FIELDS_BY_PROFILE = MappingProxyType(
    {
        _SCOPE_PROFILE_DEFAULT: {
            # Keep root-level IDs first for existing RAFS records.
            "basin_id": ("data.BasinID",),
            "field_id": ("data.FieldID",),
            "well_id": ("data.WellID",),
            # Sample schemas often carry WellboreID under acquisition details.
            "wellbore_id": (
                "data.WellboreID",
                "data.SampleAcquisition.SampleAcquisitionDetail.WellboreID",
            ),
        },
        # SamplesAnalysis records do not carry basin/field/wellbore directly.
        # Those scope keys are resolved via a first-hop Sample query (see SAMPLE_HOP_SCOPE_KEYS).
        _SCOPE_PROFILE_SAMPLESANALYSIS: {},
        # Sample master-data fields used for the scope resolution hop.
        # Include both root and nested paths because indexed records vary by schema version.
        # well_id is NOT used here; it requires a Wellbore resolution hop first.
        SCOPE_PROFILE_SAMPLE: {
            "basin_id": ("data.BasinID",),
            "field_id": ("data.FieldID",),
            "wellbore_id": (
                "data.WellboreID",
                "data.SampleAcquisition.SampleAcquisitionDetail.WellboreID",
            ),
        },
        # Wellbore master-data fields used for well_id scope resolution (first hop for well_id).
        "wellbore": {
            "well_id": ("data.WellID",),
        },
        # Based on provided depth-shift schema examples.
        SCOPE_PROFILE_DEPTH_SHIFT: {
            "basin_id": (),
            "field_id": (),
            "wellbore_id": ("data.WellboreID",),
        },
        # Effective schema fields expose GeoContexts; no direct well/wellbore IDs.
        _SCOPE_PROFILE_SATURATION_FUNCTION_SET: {
            "basin_id": (),
            "field_id": (),
        },
        # Effective schema fields expose GeoContexts; no direct well/wellbore IDs.
        _SCOPE_PROFILE_RES_SIM_ROCK_PHYSICS: {
            "basin_id": (),
            "field_id": (),
        },
    },
)

_NESTED_SCOPE_QUERY_FIELDS_BY_PROFILE = MappingProxyType(
    {
        _SCOPE_PROFILE_DEFAULT: {
            "basin_id": ("nested(data.GeoContexts, (BasinID:{value}))",),
            "field_id": ("nested(data.GeoContexts, (FieldID:{value}))",),
            "well_id": ("nested(data.GeoContexts, (WellID:{value}))",),
            "wellbore_id": ("nested(data.GeoContexts, (WellboreID:{value}))",),
        },
        SCOPE_PROFILE_SAMPLE: {
            "basin_id": ("nested(data.GeoContexts, (BasinID:{value}))",),
            "field_id": ("nested(data.GeoContexts, (FieldID:{value}))",),
            "wellbore_id": ("nested(data.GeoContexts, (WellboreID:{value}))",),
        },
        SCOPE_PROFILE_DEPTH_SHIFT: {
            "basin_id": ("nested(data.GeoContexts, (BasinID:{value}))",),
            "field_id": ("nested(data.GeoContexts, (FieldID:{value}))",),
            "wellbore_id": ("nested(data.GeoContexts, (WellboreID:{value}))",),
        },
        _SCOPE_PROFILE_SATURATION_FUNCTION_SET: {
            "basin_id": ("nested(data.GeoContexts, (BasinID:{value}))",),
            "field_id": ("nested(data.GeoContexts, (FieldID:{value}))",),
        },
        _SCOPE_PROFILE_RES_SIM_ROCK_PHYSICS: {
            "basin_id": ("nested(data.GeoContexts, (BasinID:{value}))",),
            "field_id": ("nested(data.GeoContexts, (FieldID:{value}))",),
        },
    },
)


class UnsupportedSearchScopeError(ValueError):
    """Raised when a scope value is provided for an unsupported profile key."""

    def __init__(self, profile: str, unsupported_scope_keys: List[str]) -> None:
        unsupported = ", ".join(sorted(unsupported_scope_keys))
        super().__init__(
            f"Unsupported scope filters for profile '{profile}': {unsupported}",
        )
        self.profile = profile
        self.unsupported_scope_keys = unsupported_scope_keys


def escape_query_value(raw_value: str) -> str:
    return raw_value.replace('"', r"\"")


def _get_present_scope_keys(scope: SearchScope) -> List[str]:
    return [scope_key for scope_key, scope_filter_value in scope.to_query_dict().items() if scope_filter_value]


def _validate_scope_profile_keys(
    scope: SearchScope,
    query_fields_map: _ScopeQueryMap,
    nested_query_templates_map: _ScopeQueryMap,
    scope_profile: str,
) -> None:
    present_scope_keys = _get_present_scope_keys(scope)
    supported_scope_keys = set(query_fields_map.keys()) | set(nested_query_templates_map.keys())
    unsupported_scope_keys = [scope_key for scope_key in present_scope_keys if scope_key not in supported_scope_keys]
    if unsupported_scope_keys:
        raise UnsupportedSearchScopeError(scope_profile, unsupported_scope_keys)


def _build_scope_clause(query_fields: _QueryFieldPaths, scope_filter_value: str) -> str:
    escaped_value = escape_query_value(scope_filter_value)
    if len(query_fields) == 1:
        return f'{query_fields[0]}:"{escaped_value}"'

    alternatives = " OR ".join(f'{query_field}:"{escaped_value}"' for query_field in query_fields)
    return f"({alternatives})"


def _build_nested_scope_clause(nested_templates: _QueryFieldPaths, scope_filter_value: str) -> str:
    escaped_value = escape_query_value(scope_filter_value)
    quoted_value = f'"{escaped_value}"'
    alternatives = " OR ".join(template.format(value=quoted_value) for template in nested_templates)
    if len(nested_templates) == 1:
        return alternatives
    return f"({alternatives})"


def _build_scope_key_clause(
    scope_key: str,
    scope_values: Dict[str, Optional[str]],
    query_fields_map: _ScopeQueryMap,
    nested_query_templates_map: _ScopeQueryMap,
) -> Optional[str]:
    scope_filter_value = scope_values.get(scope_key)
    if not scope_filter_value:
        return None

    alternatives: List[str] = []
    query_fields = query_fields_map.get(scope_key, ())
    if query_fields:
        alternatives.append(_build_scope_clause(query_fields, scope_filter_value))

    nested_templates = nested_query_templates_map.get(scope_key)
    if nested_templates:
        alternatives.append(_build_nested_scope_clause(nested_templates, scope_filter_value))

    clause = None
    if alternatives:
        clause = alternatives[0]
        if len(alternatives) > 1:
            alternatives_query = " OR ".join(alternatives)
            clause = "({0})".format(alternatives_query)
    return clause


def build_search_scope_clauses(
    scope: Optional[SearchScope],
    scope_profile: str = _SCOPE_PROFILE_DEFAULT,
    strict: bool = False,
) -> List[str]:
    """Build exact-match search clauses from a scope object."""
    if scope is None:
        return []

    query_fields_map = SEARCH_SCOPE_QUERY_FIELDS_BY_PROFILE.get(
        scope_profile,
        SEARCH_SCOPE_QUERY_FIELDS_BY_PROFILE[_SCOPE_PROFILE_DEFAULT],
    )
    nested_query_templates_map = _NESTED_SCOPE_QUERY_FIELDS_BY_PROFILE.get(scope_profile, {})

    if strict:
        _validate_scope_profile_keys(scope, query_fields_map, nested_query_templates_map, scope_profile)

    scope_values = scope.to_query_dict()
    scope_keys = set(query_fields_map.keys()) | set(nested_query_templates_map.keys())
    clauses: List[str] = []
    for scope_key in scope_keys:
        clause = _build_scope_key_clause(
            scope_key,
            scope_values,
            query_fields_map,
            nested_query_templates_map,
        )
        if clause:
            clauses.append(clause)

    if not clauses:
        return []
    return clauses
