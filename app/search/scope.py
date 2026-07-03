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
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger

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


_GEO_CONTEXT_SCOPE_FIELDS = MappingProxyType(
    {
        "BasinID": "basin_id",
        "FieldID": "field_id",
        "WellID": "well_id",
        "WellboreID": "wellbore_id",
    },
)


def extract_record_scope(record_data: Dict) -> Dict[str, str]:  # noqa: CCR001
    """Build a scope dict (`SearchScope.to_query_dict()` shape) from a WPC
    record's own `data` block, for use as the `scope` argument to
    `record_pending_write`.

    WPC records (SamplesAnalysis, DepthShift, ResSimRockPhysics,
    SaturationFunctionSet, ...) inherit `GeoContexts` from
    `AbstractWorkProductComponent`, a list of geo-context objects that may carry
    `BasinID`/`FieldID`/`WellID`. `WellboreID` is also checked as a flat field
    (present directly on e.g. DepthShift records, see
    `deployments/shared-schemas/osdu/work_product_component/DepthShift.1.0.0.json`).
    Only the first non-empty value found for each key is kept — a record is not
    expected to carry multiple values for the same scope key.

    Returns an empty dict for records that carry no scope fields directly (e.g.
    SamplesAnalysis). Call `enrich_scope_from_samples` afterwards to resolve
    Well/Wellbore context via the referenced Sample records.
    """
    scope: Dict[str, str] = {}
    for geo_context in record_data.get("GeoContexts") or []:
        for field_name, scope_key in _GEO_CONTEXT_SCOPE_FIELDS.items():
            if scope_key not in scope and geo_context.get(field_name):
                scope[scope_key] = geo_context[field_name]

    if "wellbore_id" not in scope and record_data.get("WellboreID"):
        scope["wellbore_id"] = record_data["WellboreID"]

    return scope


def _merge_sample_scope(scope: Dict[str, str], conflicted: Set[str], sample_data: Dict) -> None:  # noqa: CCR001, WPS231
    """Merge Well/Wellbore scope keys from a Sample record's data block into scope.

    Checks `SampleAcquisition.SampleAcquisitionDetail.WellboreID` and `GeoContexts`.
    When a key already has a value from a prior sample that differs from this sample's
    value, the key is added to `conflicted` and removed from scope — an ambiguous
    SamplesAnalysis must not incorrectly match a scoped search.
    """
    if "wellbore_id" not in conflicted:
        wellbore_id = sample_data.get("SampleAcquisition", {}).get("SampleAcquisitionDetail", {}).get("WellboreID")
        if wellbore_id:
            existing = scope.get("wellbore_id")
            if existing is None:
                scope["wellbore_id"] = wellbore_id
            elif existing != wellbore_id:
                conflicted.add("wellbore_id")
                scope.pop("wellbore_id", None)

    for geo_context in sample_data.get("GeoContexts") or []:
        for field_name, scope_key in _GEO_CONTEXT_SCOPE_FIELDS.items():
            if scope_key in conflicted:
                continue
            geo_value = geo_context.get(field_name)
            if not geo_value:
                continue
            existing = scope.get(scope_key)
            if existing is None:
                scope[scope_key] = geo_value
            elif existing != geo_value:
                conflicted.add(scope_key)
                scope.pop(scope_key, None)


async def enrich_scope_from_samples(  # noqa: ASYNC910, WPS231
    scope: Dict[str, str],
    sample_ids: List[str],
    storage_service: Any,
) -> Dict[str, str]:
    """Enrich a scope dict with Well/Wellbore IDs resolved from Sample records.

    SamplesAnalysis WPCs carry no GeoContexts; their Well/Wellbore context lives
    on the Sample master-data records they reference via `SampleIDs`. This fetches
    those records in a single batch query and merges any found scope keys.

    When referenced samples carry conflicting values for a scope key (e.g. two
    samples from different wellbores), that key is dropped from the result so an
    ambiguous record cannot incorrectly match a scoped search.

    Fails silently — returns the original scope on any error so the pending-write
    is still recorded (unscoped) rather than dropped.
    """
    if not sample_ids:
        return scope  # noqa: ASYNC910
    try:
        response = await storage_service.query_records(sample_ids)
        enriched = dict(scope)
        conflicted: Set[str] = set()
        for sample_record in response.get("records") or []:
            _merge_sample_scope(enriched, conflicted, sample_record.get("data") or {})
        if conflicted:
            logger.debug(
                "enrich_scope_from_samples: conflicting scope keys dropped (ambiguous samples): {0}",
                sorted(conflicted),
            )
        return enriched
    except Exception as exc:  # noqa: B902, WPS329
        logger.debug("enrich_scope_from_samples: Storage error, returning original scope: {0}", exc)
        return scope  # noqa: ASYNC910


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
