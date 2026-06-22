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

import pytest

from app.models.schemas.search_scope import SearchScope
from app.search.scope import (
    SCOPE_PROFILE_DEPTH_SHIFT,
    SCOPE_PROFILE_SAMPLE,
    SCOPE_PROFILE_SAMPLESANALYSIS,
    UnsupportedSearchScopeError,
    build_search_scope_clauses,
    extract_record_scope,
)


def test_build_search_scope_clauses_empty_scope_returns_empty_list():
    assert build_search_scope_clauses(SearchScope()) == []


def test_build_search_scope_clauses_default_wellbore_uses_all_supported_paths():
    clauses = build_search_scope_clauses(
        SearchScope(wellbore_id="opendes:master-data--Wellbore:wb-1:"),
    )

    assert len(clauses) == 1
    clause = clauses[0]
    assert 'data.WellboreID:"opendes:master-data--Wellbore:wb-1:"' in clause
    assert 'data.SampleAcquisition.SampleAcquisitionDetail.WellboreID:"opendes:master-data--Wellbore:wb-1:"' in clause
    assert 'nested(data.GeoContexts, (WellboreID:"opendes:master-data--Wellbore:wb-1:"))' in clause


def test_build_search_scope_clauses_samplesanalysis_profile_returns_no_direct_clauses():
    # SamplesAnalysis records do not carry these fields; they are resolved via Sample hop.
    assert (
        build_search_scope_clauses(
            SearchScope(wellbore_id="opendes:master-data--Wellbore:wb-1:"),
            scope_profile=SCOPE_PROFILE_SAMPLESANALYSIS,
        )
        == []
    )
    assert (
        build_search_scope_clauses(
            SearchScope(basin_id="opendes:master-data--Basin:b-1:"),
            scope_profile=SCOPE_PROFILE_SAMPLESANALYSIS,
        )
        == []
    )


def test_build_search_scope_clauses_sample_profile_uses_correct_field_paths():
    clauses = build_search_scope_clauses(
        SearchScope(wellbore_id="opendes:master-data--Wellbore:wb-1:"),
        scope_profile=SCOPE_PROFILE_SAMPLE,
    )
    assert len(clauses) == 1
    clause = clauses[0]
    assert 'data.WellboreID:"opendes:master-data--Wellbore:wb-1:"' in clause
    assert 'data.SampleAcquisition.SampleAcquisitionDetail.WellboreID:"opendes:master-data--Wellbore:wb-1:"' in clause
    assert 'nested(data.GeoContexts, (WellboreID:"opendes:master-data--Wellbore:wb-1:"))' in clause

    clauses = build_search_scope_clauses(
        SearchScope(basin_id="opendes:master-data--Basin:b-1:"),
        scope_profile=SCOPE_PROFILE_SAMPLE,
    )
    assert len(clauses) == 1
    clause = clauses[0]
    assert 'data.BasinID:"opendes:master-data--Basin:b-1:"' in clause
    assert 'nested(data.GeoContexts, (BasinID:"opendes:master-data--Basin:b-1:"))' in clause

    clauses = build_search_scope_clauses(
        SearchScope(field_id="opendes:master-data--Field:f-1:"),
        scope_profile=SCOPE_PROFILE_SAMPLE,
    )
    assert len(clauses) == 1
    clause = clauses[0]
    assert 'data.FieldID:"opendes:master-data--Field:f-1:"' in clause
    assert 'nested(data.GeoContexts, (FieldID:"opendes:master-data--Field:f-1:"))' in clause


def test_build_search_scope_clauses_depth_shift_supports_root_and_geocontexts_wellbore_paths():
    clauses = build_search_scope_clauses(
        SearchScope(wellbore_id="opendes:master-data--Wellbore:wb-1:"),
        scope_profile=SCOPE_PROFILE_DEPTH_SHIFT,
    )

    assert len(clauses) == 1
    clause = clauses[0]
    assert 'data.WellboreID:"opendes:master-data--Wellbore:wb-1:"' in clause
    assert 'nested(data.GeoContexts, (WellboreID:"opendes:master-data--Wellbore:wb-1:"))' in clause


def test_build_search_scope_clauses_strict_rejects_unsupported_samplesanalysis_scope_key():
    # SAMPLESANALYSIS profile is empty: all scope keys are unsupported for direct querying.
    with pytest.raises(UnsupportedSearchScopeError):
        build_search_scope_clauses(
            SearchScope(well_id="opendes:master-data--Well:w-1:"),
            scope_profile=SCOPE_PROFILE_SAMPLESANALYSIS,
            strict=True,
        )


def test_build_search_scope_clauses_strict_rejects_unsupported_depth_shift_scope_key():
    with pytest.raises(UnsupportedSearchScopeError):
        build_search_scope_clauses(
            SearchScope(well_id="opendes:master-data--Well:w-1:"),
            scope_profile=SCOPE_PROFILE_DEPTH_SHIFT,
            strict=True,
        )


def test_build_search_scope_clauses_basin_and_field_are_anded():
    clauses = build_search_scope_clauses(
        SearchScope(
            basin_id="opendes:master-data--Basin:b-1:",
            field_id="opendes:master-data--Field:f-1:",
        ),
    )

    assert len(clauses) == 2
    assert clauses[0].startswith("(")
    assert clauses[1].startswith("(")


# --- extract_record_scope (resolves plan's Open Question 1) ---


def test_extract_record_scope_empty_record_returns_empty_dict():
    # Plain SamplesAnalysis records carry no GeoContexts/WellboreID; only SampleIDs,
    # which require an additional Sample-record hop out of scope for write-time checks.
    assert extract_record_scope({"SampleIDs": ["partition:master-data--Sample:s-1:"]}) == {}


def test_extract_record_scope_reads_basin_and_field_from_geo_contexts():
    record_data = {
        "GeoContexts": [
            {"BasinID": "partition:master-data--Basin:b-1:"},
            {"FieldID": "partition:master-data--Field:f-1:"},
        ],
    }
    assert extract_record_scope(record_data) == {
        "basin_id": "partition:master-data--Basin:b-1:",
        "field_id": "partition:master-data--Field:f-1:",
    }


def test_extract_record_scope_reads_flat_wellbore_id():
    # DepthShift records carry WellboreID as a flat field (not via GeoContexts).
    record_data = {"WellboreID": "partition:master-data--Wellbore:wb-1:"}
    assert extract_record_scope(record_data) == {"wellbore_id": "partition:master-data--Wellbore:wb-1:"}


def test_extract_record_scope_geo_context_wellbore_id_takes_precedence_over_flat():
    record_data = {
        "GeoContexts": [{"WellboreID": "partition:master-data--Wellbore:from-geo-context:"}],
        "WellboreID": "partition:master-data--Wellbore:flat-fallback:",
    }
    assert extract_record_scope(record_data) == {
        "wellbore_id": "partition:master-data--Wellbore:from-geo-context:",
    }


def test_extract_record_scope_ignores_geo_context_entries_without_recognized_fields():
    record_data = {"GeoContexts": [{"GeoTypeID": "Field"}]}
    assert extract_record_scope(record_data) == {}


def test_extract_record_scope_no_geo_contexts_key_does_not_raise():
    assert extract_record_scope({}) == {}
