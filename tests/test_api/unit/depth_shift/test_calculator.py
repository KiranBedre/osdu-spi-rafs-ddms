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

"""Unit tests for app.depth_shift.calculator (no mocks, no I/O)."""

import pytest

from app.depth_shift.calculator import (
    _validate_intervals,
    _validate_no_bilinear,
    _validate_no_inversion,
    _validate_no_overlap,
    compute_shifted_depth,
    find_interval,
    shift_sample,
    validate_shift_values,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BULK_SHIFT_INTERVAL = {
    "OriginalTopDepth": 1000.0,
    "OriginalBaseDepth": 1010.0,
    "ShiftedTopDepth": 1001.5,
    "ShiftedBaseDepth": 1011.5,
}

# Domain design doc example: OrigTop=1870, OrigBase=1900, ShiftedTop=1875,
# ShiftedBase=1910.  SampleTop=1872 → relative_pos=2/30=0.0667,
# ShiftedSampleTop = 1875 + 0.0667 * 35 = 1875 + 2.333... = 1877.333...
INTERP_INTERVAL = {
    "OriginalTopDepth": 1870.0,
    "OriginalBaseDepth": 1900.0,
    "ShiftedTopDepth": 1875.0,
    "ShiftedBaseDepth": 1910.0,
}

INTERP_INTERVAL_NONE_METHOD = {
    "OriginalTopDepth": 1870.0,
    "OriginalBaseDepth": 1900.0,
    "ShiftedTopDepth": 1875.0,
    "ShiftedBaseDepth": 1910.0,
    "DepthShiftInterpolationMethodID": "None",
}

INTERP_INTERVAL_NONE_METHOD_FULL_ID = {
    "OriginalTopDepth": 1870.0,
    "OriginalBaseDepth": 1900.0,
    "ShiftedTopDepth": 1875.0,
    "ShiftedBaseDepth": 1910.0,
    "DepthShiftInterpolationMethodID": "osdu:reference-data--DepthShiftInterpolationMethod:None:",
}

INTERP_INTERVAL_LINEAR_METHOD = {
    "OriginalTopDepth": 1870.0,
    "OriginalBaseDepth": 1900.0,
    "ShiftedTopDepth": 1875.0,
    "ShiftedBaseDepth": 1910.0,
    "DepthShiftInterpolationMethodID": "Linear",
}

INTERP_INTERVAL_BILINEAR_METHOD = {
    "OriginalTopDepth": 1870.0,
    "OriginalBaseDepth": 1900.0,
    "ShiftedTopDepth": 1875.0,
    "ShiftedBaseDepth": 1910.0,
    "DepthShiftInterpolationMethodID": "Bilinear",
}

INTERP_INTERVAL_BILINEAR_FULL_OSDU_ID = {
    "OriginalTopDepth": 1870.0,
    "OriginalBaseDepth": 1900.0,
    "ShiftedTopDepth": 1875.0,
    "ShiftedBaseDepth": 1910.0,
    "DepthShiftInterpolationMethodID": "osdu:reference-data--DepthShiftInterpolationMethod:Bilinear:",
}

MULTI_INTERVAL_SHIFT_SET = [
    {
        "OriginalTopDepth": 1000.0,
        "OriginalBaseDepth": 1010.0,
        "ShiftedTopDepth": 1001.5,
        "ShiftedBaseDepth": 1011.5,
    },
    {
        "OriginalTopDepth": 1010.0,
        "OriginalBaseDepth": 1020.0,
        "ShiftedTopDepth": 1012.0,
        "ShiftedBaseDepth": 1022.0,
    },
    {
        "OriginalTopDepth": 1870.0,
        "OriginalBaseDepth": 1900.0,
        "ShiftedTopDepth": 1875.0,
        "ShiftedBaseDepth": 1910.0,
    },
]


# ---------------------------------------------------------------------------
# _validate_intervals
# ---------------------------------------------------------------------------


class TestValidateIntervals:
    def test_monotonic_passes(self):
        _validate_intervals(MULTI_INTERVAL_SHIFT_SET)  # must not raise

    def test_non_monotonic_raises(self):
        bad_set = [
            {
                "OriginalTopDepth": 1000.0,
                "OriginalBaseDepth": 1010.0,
                "ShiftedTopDepth": 1001.0,
                "ShiftedBaseDepth": 1011.0,
            },
            {
                "OriginalTopDepth": 990.0,
                "OriginalBaseDepth": 1000.0,
                "ShiftedTopDepth": 990.0,
                "ShiftedBaseDepth": 1000.0,
            },
        ]
        with pytest.raises(ValueError, match="strictly increasing"):
            _validate_intervals(bad_set)

    def test_equal_tops_raises(self):
        bad_set = [
            {
                "OriginalTopDepth": 1000.0,
                "OriginalBaseDepth": 1010.0,
                "ShiftedTopDepth": 1001.0,
                "ShiftedBaseDepth": 1011.0,
            },
            {
                "OriginalTopDepth": 1000.0,
                "OriginalBaseDepth": 1020.0,
                "ShiftedTopDepth": 1002.0,
                "ShiftedBaseDepth": 1022.0,
            },
        ]
        with pytest.raises(ValueError, match="strictly increasing"):
            _validate_intervals(bad_set)


# ---------------------------------------------------------------------------
# find_interval
# ---------------------------------------------------------------------------


class TestFindInterval:
    def test_returns_none_shallower_than_first(self):
        result = find_interval(MULTI_INTERVAL_SHIFT_SET, sample_top=999.0)
        assert result is None

    def test_exact_top_returns_interval(self):
        result = find_interval(MULTI_INTERVAL_SHIFT_SET, sample_top=1000.0)
        assert result["OriginalTopDepth"] == 1000.0

    def test_within_first_interval(self):
        result = find_interval(MULTI_INTERVAL_SHIFT_SET, sample_top=1005.0)
        assert result["OriginalTopDepth"] == 1000.0

    def test_boundary_selects_second_interval(self):
        result = find_interval(MULTI_INTERVAL_SHIFT_SET, sample_top=1010.0)
        assert result["OriginalTopDepth"] == 1010.0

    def test_deep_sample_selects_last_interval(self):
        result = find_interval(MULTI_INTERVAL_SHIFT_SET, sample_top=1880.0)
        assert result["OriginalTopDepth"] == 1870.0

    def test_beyond_last_base_returns_none(self):
        """Sample deeper than the last interval's base is not contained → None.

        Guards against fabricating a shifted value from the wrong interval
        when no interval actually covers the sample depth.
        """
        result = find_interval(MULTI_INTERVAL_SHIFT_SET, sample_top=2000.0)
        assert result is None

    def test_sample_in_gap_between_intervals_returns_none(self):
        """Sample in the gap between interval 2 (…1020) and 3 (1870…) → None."""
        result = find_interval(MULTI_INTERVAL_SHIFT_SET, sample_top=1500.0)
        assert result is None

    def test_exact_base_of_last_interval_is_not_contained(self):
        """Sample exactly at the last interval's OriginalBaseDepth is NOT contained.

        The interval is half-open [OriginalTopDepth, OriginalBaseDepth), so a
        sample depth equal to OriginalBaseDepth falls outside the interval.
        """
        result = find_interval(MULTI_INTERVAL_SHIFT_SET, sample_top=1900.0)
        assert result is None

    def test_just_inside_last_interval_is_contained(self):
        """Sample just below the last interval's OriginalBaseDepth is contained."""
        result = find_interval(MULTI_INTERVAL_SHIFT_SET, sample_top=1899.999)
        assert result is not None
        assert result["OriginalTopDepth"] == 1870.0


# ---------------------------------------------------------------------------
# compute_shifted_depth
# ---------------------------------------------------------------------------


class TestComputeShiftedDepth:
    def test_bulk_shift_constant_offset(self):
        """Equal-size interval: constant shift of +1.5."""
        result = compute_shifted_depth(1005.0, BULK_SHIFT_INTERVAL)
        assert abs(result - 1006.5) < 1e-6

    def test_bulk_shift_at_top(self):
        result = compute_shifted_depth(1000.0, BULK_SHIFT_INTERVAL)
        assert abs(result - 1001.5) < 1e-6

    def test_linear_interpolation_domain_example(self):
        """Domain design example: SampleTop=1872 → ShiftedSampleTop≈1877.333."""
        result = compute_shifted_depth(1872.0, INTERP_INTERVAL)
        expected = 1875.0 + (2.0 / 30.0) * 35.0
        assert abs(result - expected) < 1e-6

    def test_linear_interpolation_at_orig_top(self):
        result = compute_shifted_depth(1870.0, INTERP_INTERVAL)
        assert abs(result - 1875.0) < 1e-6

    def test_linear_interpolation_at_orig_base(self):
        result = compute_shifted_depth(1900.0, INTERP_INTERVAL)
        assert abs(result - 1910.0) < 1e-6

    def test_none_method_unequal_spans_uses_linear_interpolation(self):
        """DepthShiftInterpolationMethodID='None' with unequal spans must use linear interpolation.

        'None' means method not specified (auto-detect), NOT force-bulk.
        AC3 from Issue-752 was wrong; the correct rule is span-comparison auto-detect.
        """
        result = compute_shifted_depth(1872.0, INTERP_INTERVAL_NONE_METHOD)
        # Linear interpolation: 1875.0 + (2.0/30.0)*35.0 ≈ 1877.333
        expected = 1875.0 + (2.0 / 30.0) * 35.0
        assert abs(result - expected) < 1e-6

    def test_none_method_full_osdu_id_unequal_spans_uses_linear(self):
        """Full OSDU reference ID ':None:' with unequal spans must also use linear interpolation."""
        result = compute_shifted_depth(1872.0, INTERP_INTERVAL_NONE_METHOD_FULL_ID)
        expected = 1875.0 + (2.0 / 30.0) * 35.0
        assert abs(result - expected) < 1e-6

    def test_none_method_equal_spans_uses_bulk_shift(self):
        """Explicit 'None' with equal spans → bulk shift (span-equality path works correctly)."""
        equal_span_interval_none = {
            "OriginalTopDepth": 1000.0,
            "OriginalBaseDepth": 1010.0,
            "ShiftedTopDepth": 1001.5,
            "ShiftedBaseDepth": 1011.5,
            "DepthShiftInterpolationMethodID": "None",
        }
        result = compute_shifted_depth(1005.0, equal_span_interval_none)
        # Bulk shift: 1005.0 + (1001.5 - 1000.0) = 1006.5
        assert abs(result - 1006.5) < 1e-6

    def test_absent_method_unequal_spans_uses_linear(self):
        """Absent DepthShiftInterpolationMethodID with unequal spans → linear interpolation."""
        result = compute_shifted_depth(1872.0, INTERP_INTERVAL)
        expected = 1875.0 + (2.0 / 30.0) * 35.0
        assert abs(result - expected) < 1e-6

    def test_empty_string_method_unequal_spans_uses_linear(self):
        """Empty string DepthShiftInterpolationMethodID with unequal spans → linear interpolation."""
        interval_empty_method = {**INTERP_INTERVAL, "DepthShiftInterpolationMethodID": ""}
        result = compute_shifted_depth(1872.0, interval_empty_method)
        expected = 1875.0 + (2.0 / 30.0) * 35.0
        assert abs(result - expected) < 1e-6

    def test_linear_method_explicit_uses_interpolation(self):
        """DepthShiftInterpolationMethodID='Linear' with unequal spans uses linear interpolation."""
        result = compute_shifted_depth(1872.0, INTERP_INTERVAL_LINEAR_METHOD)
        expected = 1875.0 + (2.0 / 30.0) * 35.0
        assert abs(result - expected) < 1e-6

    def test_absent_interpolation_method_falls_back_to_span_comparison(self):
        """No DepthShiftInterpolationMethodID key → span comparison determines mode."""
        # INTERP_INTERVAL has unequal spans, no method key → linear interpolation
        result = compute_shifted_depth(1872.0, INTERP_INTERVAL)
        expected = 1875.0 + (2.0 / 30.0) * 35.0
        assert abs(result - expected) < 1e-6


# ---------------------------------------------------------------------------
# shift_sample
# ---------------------------------------------------------------------------


class TestShiftSample:
    def test_point_measurement_base_none(self):
        """SampleBase=None → ShiftedSampleBase=None."""
        shifted_top, shifted_base = shift_sample(1005.0, None, MULTI_INTERVAL_SHIFT_SET)
        assert abs(shifted_top - 1006.5) < 1e-6
        assert shifted_base is None

    def test_with_base_uses_top_interval(self):
        """Cross-interval guard: SampleBase in different interval still uses SampleTop's interval."""
        # SampleTop=1005 lands in interval [1000–1010]; SampleBase=1015 crosses into [1010–1020].
        # Both should use the [1000–1010] interval (constant shift +1.5).
        shifted_top, shifted_base = shift_sample(1005.0, 1015.0, MULTI_INTERVAL_SHIFT_SET)
        assert abs(shifted_top - 1006.5) < 1e-6
        assert abs(shifted_base - 1016.5) < 1e-6

    def test_no_enclosing_interval_returns_none(self):
        shifted_top, shifted_base = shift_sample(500.0, 510.0, MULTI_INTERVAL_SHIFT_SET)
        assert shifted_top is None
        assert shifted_base is None

    def test_both_depths_shifted_correctly(self):
        shifted_top, shifted_base = shift_sample(1000.0, 1010.0, MULTI_INTERVAL_SHIFT_SET)
        assert abs(shifted_top - 1001.5) < 1e-6
        assert abs(shifted_base - 1011.5) < 1e-6


# ---------------------------------------------------------------------------
# validate_shift_values
# ---------------------------------------------------------------------------

_VALID_INTERVAL = {
    "OriginalTopDepth": 100.0,
    "OriginalBaseDepth": 110.0,
    "ShiftedTopDepth": 101.5,
    "ShiftedBaseDepth": 111.5,
}


class TestValidateShiftValues:
    def test_valid_set_passes(self):
        validate_shift_values([_VALID_INTERVAL])

    def test_zero_shifted_depth_passes(self):
        """Zero is a valid depth value (no shift)."""
        interval = {**_VALID_INTERVAL, "ShiftedTopDepth": 0.0, "ShiftedBaseDepth": 0.0}
        validate_shift_values([interval])

    @pytest.mark.parametrize(
        "null_field",
        [
            "OriginalTopDepth",
            "OriginalBaseDepth",
            "ShiftedTopDepth",
            "ShiftedBaseDepth",
        ],
    )
    def test_null_field_raises(self, null_field):
        bad = {**_VALID_INTERVAL, null_field: None}
        with pytest.raises(ValueError, match=null_field):
            validate_shift_values([bad])

    def test_missing_field_raises(self):
        bad = {k: v for k, v in _VALID_INTERVAL.items() if k != "ShiftedTopDepth"}
        with pytest.raises(ValueError, match="ShiftedTopDepth"):
            validate_shift_values([bad])

    def test_reports_row_index(self):
        bad = {**_VALID_INTERVAL, "OriginalBaseDepth": None}
        with pytest.raises(ValueError, match="index 1"):
            validate_shift_values([_VALID_INTERVAL, bad])

    def test_empty_set_passes(self):
        """Empty shift set has no rows to validate — caught separately by _extract_depth_shift_set."""
        validate_shift_values([])

    def test_inverted_interval_raises(self):
        """Issue 4: OriginalBaseDepth < OriginalTopDepth must raise ValueError."""
        inverted = {
            "OriginalTopDepth": 1000.0,
            "OriginalBaseDepth": 990.0,  # inverted: base < top
            "ShiftedTopDepth": 1001.0,
            "ShiftedBaseDepth": 991.0,
        }
        with pytest.raises(ValueError, match="OriginalBaseDepth"):
            validate_shift_values([inverted])

    def test_zero_width_interval_raises(self):
        """Issue 4: OriginalBaseDepth == OriginalTopDepth must raise ValueError."""
        zero_width = {
            "OriginalTopDepth": 1000.0,
            "OriginalBaseDepth": 1000.0,
            "ShiftedTopDepth": 1001.0,
            "ShiftedBaseDepth": 1001.0,
        }
        with pytest.raises(ValueError, match="OriginalBaseDepth"):
            validate_shift_values([zero_width])

    def test_overlapping_intervals_raises(self):
        """Issue 3: intervals [1000,1100] and [1050,1200] overlap → ValueError."""
        overlapping = [
            {
                "OriginalTopDepth": 1000.0,
                "OriginalBaseDepth": 1100.0,
                "ShiftedTopDepth": 1001.0,
                "ShiftedBaseDepth": 1101.0,
            },
            {
                "OriginalTopDepth": 1050.0,
                "OriginalBaseDepth": 1200.0,
                "ShiftedTopDepth": 1051.0,
                "ShiftedBaseDepth": 1201.0,
            },
        ]
        with pytest.raises(ValueError, match="overlap"):
            validate_shift_values(overlapping)

    def test_adjacent_touching_intervals_pass(self):
        """Issue 3: touching intervals (base[i] == top[i+1]) must not raise.

        MULTI_INTERVAL_SHIFT_SET has interval 0 base=1010 and interval 1 top=1010.
        These are touching, not overlapping — the existing fixture must keep passing.
        """
        validate_shift_values(MULTI_INTERVAL_SHIFT_SET)  # must not raise

    def test_bilinear_method_raises(self):
        """Issue 2: DepthShiftInterpolationMethodID='Bilinear' must raise ValueError."""
        bilinear_set = [
            {
                "OriginalTopDepth": 1000.0,
                "OriginalBaseDepth": 1010.0,
                "ShiftedTopDepth": 1001.0,
                "ShiftedBaseDepth": 1011.0,
                "DepthShiftInterpolationMethodID": "Bilinear",
            }
        ]
        with pytest.raises(ValueError, match="[Bb]ilinear"):
            validate_shift_values(bilinear_set)

    def test_bilinear_full_osdu_id_raises(self):
        """Issue 2: full OSDU reference ID ending in ':Bilinear:' must raise ValueError."""
        bilinear_full_id_set = [
            {
                "OriginalTopDepth": 1000.0,
                "OriginalBaseDepth": 1010.0,
                "ShiftedTopDepth": 1001.0,
                "ShiftedBaseDepth": 1011.0,
                "DepthShiftInterpolationMethodID": ("osdu:reference-data--DepthShiftInterpolationMethod:Bilinear:"),
            }
        ]
        with pytest.raises(ValueError, match="[Bb]ilinear"):
            validate_shift_values(bilinear_full_id_set)

    def test_linear_method_passes(self):
        """Issue 2: explicit 'Linear' is a supported method and must not raise."""
        linear_set = [
            {
                "OriginalTopDepth": 1000.0,
                "OriginalBaseDepth": 1010.0,
                "ShiftedTopDepth": 1001.0,
                "ShiftedBaseDepth": 1011.0,
                "DepthShiftInterpolationMethodID": "Linear",
            }
        ]
        validate_shift_values(linear_set)  # must not raise


# ---------------------------------------------------------------------------
# _validate_no_inversion, _validate_no_overlap, _validate_no_bilinear
# ---------------------------------------------------------------------------


class TestValidateNoInversion:
    """Direct tests for the _validate_no_inversion helper."""

    def test_valid_interval_passes(self):
        _validate_no_inversion([_VALID_INTERVAL])  # must not raise

    def test_inverted_raises_with_index(self):
        second_inverted = {
            "OriginalTopDepth": 2000.0,
            "OriginalBaseDepth": 1999.0,
            "ShiftedTopDepth": 2001.0,
            "ShiftedBaseDepth": 2000.0,
        }
        with pytest.raises(ValueError, match="index 1"):
            _validate_no_inversion([_VALID_INTERVAL, second_inverted])


class TestValidateNoOverlap:
    """Direct tests for the _validate_no_overlap helper."""

    def test_no_overlap_passes(self):
        _validate_no_overlap(MULTI_INTERVAL_SHIFT_SET)  # touching intervals, must not raise

    def test_overlap_raises(self):
        overlap_set = [
            {
                "OriginalTopDepth": 100.0,
                "OriginalBaseDepth": 200.0,
                "ShiftedTopDepth": 101.0,
                "ShiftedBaseDepth": 201.0,
            },
            {
                "OriginalTopDepth": 150.0,
                "OriginalBaseDepth": 300.0,
                "ShiftedTopDepth": 151.0,
                "ShiftedBaseDepth": 301.0,
            },
        ]
        with pytest.raises(ValueError, match="overlap"):
            _validate_no_overlap(overlap_set)

    def test_touching_does_not_raise(self):
        touching = [
            {
                "OriginalTopDepth": 100.0,
                "OriginalBaseDepth": 200.0,
                "ShiftedTopDepth": 101.0,
                "ShiftedBaseDepth": 201.0,
            },
            {
                "OriginalTopDepth": 200.0,
                "OriginalBaseDepth": 300.0,
                "ShiftedTopDepth": 201.0,
                "ShiftedBaseDepth": 301.0,
            },
        ]
        _validate_no_overlap(touching)  # must not raise


class TestValidateNoBilinear:
    """Direct tests for the _validate_no_bilinear helper."""

    def test_no_method_passes(self):
        _validate_no_bilinear([_VALID_INTERVAL])  # must not raise

    def test_linear_method_passes(self):
        linear_row = {**_VALID_INTERVAL, "DepthShiftInterpolationMethodID": "Linear"}
        _validate_no_bilinear([linear_row])  # must not raise

    def test_bilinear_bare_raises(self):
        with pytest.raises(ValueError, match="[Bb]ilinear"):
            _validate_no_bilinear([INTERP_INTERVAL_BILINEAR_METHOD])

    def test_bilinear_full_osdu_id_raises(self):
        with pytest.raises(ValueError, match="[Bb]ilinear"):
            _validate_no_bilinear([INTERP_INTERVAL_BILINEAR_FULL_OSDU_ID])
