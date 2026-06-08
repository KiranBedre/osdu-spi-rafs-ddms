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

"""Data-driven tests using real Volve field data (Equinor open dataset).

The Volve depth-shift CSV (no_15_9-19_sr_core_plug_DepthShift.csv) contains
per-plug measured depths and their shifted counterparts.  We build a
CoreToLogDepthShift interval list from consecutive CSV rows and assert that
shift_sample() reproduces the expected shifted depths.

The file lives in tmp/Depth_processing/data/ which is not committed to the
repo.  All tests in this module are skipped automatically when the file is
absent.
"""

import csv
from pathlib import Path
from typing import List, Tuple

import pytest

from app.depth_shift.calculator import (
    _validate_intervals,
    compute_shifted_depth,
    shift_sample,
)

_DATA_CSV = Path(__file__).resolve().parent / "data" / "no_15_9-19_sr_core_plug_DepthShift.csv"


def _load_rows() -> List[dict]:
    rows = []
    with open(_DATA_CSV, newline="") as fh:
        reader = csv.DictReader(fh)
        next(reader)  # skip units row (METRES, METRES, METRES)
        for row in reader:
            rows.append(
                {
                    "DEPTH": float(row["DEPTH"]),
                    "DEPTH_DIFF": float(row["DEPTH_DIFF"]),
                    "NEW_DEPTH": float(row["NEW_DEPTH"]),
                }
            )
    return rows


def _build_shift_set(rows: List[dict]) -> List[dict]:
    """Build CoreToLogDepthShift intervals from consecutive CSV rows."""
    return [
        {
            "OriginalTopDepth": rows[i]["DEPTH"],
            "OriginalBaseDepth": rows[i + 1]["DEPTH"],
            "ShiftedTopDepth": rows[i]["NEW_DEPTH"],
            "ShiftedBaseDepth": rows[i + 1]["NEW_DEPTH"],
        }
        for i in range(len(rows) - 1)
    ]


@pytest.fixture(scope="module")
def volve_data() -> Tuple[List[dict], List[dict]]:
    if not _DATA_CSV.exists():
        pytest.skip(f"Volve fixture not found: {_DATA_CSV}")
    rows = _load_rows()
    shift_set = _build_shift_set(rows)
    _validate_intervals(shift_set)
    return rows, shift_set


class TestZeroShiftZone:
    """Samples in the zero-shift region (3643–3647.5 m) must be unchanged."""

    def test_point_at_top_boundary(self, volve_data):
        _, shift_set = volve_data
        shifted_top, shifted_base = shift_sample(3643.0, None, shift_set)
        assert shifted_top == pytest.approx(3643.0, abs=1e-6)
        assert shifted_base is None

    def test_point_inside_zero_shift(self, volve_data):
        _, shift_set = volve_data
        shifted_top, _ = shift_sample(3644.0, None, shift_set)
        assert shifted_top == pytest.approx(3644.0, abs=1e-6)

    def test_range_entirely_in_zero_shift(self, volve_data):
        _, shift_set = volve_data
        shifted_top, shifted_base = shift_sample(3643.25, 3643.5, shift_set)
        assert shifted_top == pytest.approx(3643.25, abs=1e-6)
        assert shifted_base == pytest.approx(3643.5, abs=1e-6)


class TestBoundaryPoints:
    """At OriginalTopDepth boundaries, shifted result must equal ShiftedTopDepth.

    This invariant holds regardless of interpolation method: when the sample
    is exactly at a boundary, the relative position is 0.0 and both bulk and
    linear branches return ShiftedTopDepth.  Validates bisect_right lookup
    and the shift math against 200+ real-world data points.
    """

    @pytest.mark.parametrize("row_index", [13, 14, 20, 50, 100, 150, 200])
    def test_sample_at_row_boundary(self, volve_data, row_index):
        rows, shift_set = volve_data
        row = rows[row_index]
        shifted_top, _ = shift_sample(row["DEPTH"], None, shift_set)
        assert shifted_top == pytest.approx(row["NEW_DEPTH"], abs=1e-4), (
            f"row {row_index}: depth={row['DEPTH']}, " f"expected={row['NEW_DEPTH']}, got={shifted_top}"
        )


class TestLinearInterpolation:
    """Midpoint between two consecutive rows should interpolate linearly."""

    @pytest.mark.parametrize("row_index", [13, 20, 50, 100, 150])
    def test_midpoint_interpolates_linearly(self, volve_data, row_index):
        rows, shift_set = volve_data
        r0, r1 = rows[row_index], rows[row_index + 1]
        mid_depth = (r0["DEPTH"] + r1["DEPTH"]) / 2
        expected = (r0["NEW_DEPTH"] + r1["NEW_DEPTH"]) / 2

        shifted_top, _ = shift_sample(mid_depth, None, shift_set)
        assert shifted_top == pytest.approx(expected, abs=1e-4), (
            f"midpoint rows {row_index}-{row_index + 1}: " f"depth={mid_depth}, expected={expected}, got={shifted_top}"
        )


class TestEdgeCases:
    """Out-of-range and cross-interval scenarios."""

    def test_shallower_than_first_interval_returns_none(self, volve_data):
        _, shift_set = volve_data
        shifted_top, shifted_base = shift_sample(100.0, None, shift_set)
        assert shifted_top is None
        assert shifted_base is None

    def test_cross_interval_guard_uses_top_interval(self, volve_data):
        """SampleBase deeper than SampleTop's interval must still use SampleTop's interval.

        TR-DS-05: when top and base span a boundary, both are shifted using
        the interval that contains the top.
        """
        rows, shift_set = volve_data
        # rows[13]: 4328.85 — falls in shift_set[13] (OriginalTop=4328.85)
        # rows[15]: 4329.25 — falls in shift_set[14] territory (OriginalTop=4329.0)
        sample_top = rows[13]["DEPTH"]  # 4328.85 → interval 13
        sample_base = rows[15]["DEPTH"]  # 4329.25 → would be interval 14 if used alone

        shifted_top, shifted_base = shift_sample(sample_top, sample_base, shift_set)

        # Both must be computed using shift_set[13], not shift_set[14]
        interval_13 = shift_set[13]
        expected_top = compute_shifted_depth(sample_top, interval_13)
        expected_base = compute_shifted_depth(sample_base, interval_13)

        assert shifted_top == pytest.approx(expected_top, abs=1e-6)
        assert shifted_base == pytest.approx(expected_base, abs=1e-6)

        # Sanity: result would differ if interval 14 were used for the base
        expected_base_wrong = compute_shifted_depth(sample_base, shift_set[14])
        assert (
            abs(shifted_base - expected_base_wrong) > 1e-4
        ), "Cross-interval guard did not fire — base was computed with wrong interval"

    def test_bulk_shift_forced_by_none_method(self, volve_data):
        """DepthShiftInterpolationMethodID='None' forces bulk shift even when spans differ."""
        rows, shift_set = volve_data
        # Row 13 interval has unequal spans (would normally interpolate)
        r0, r1 = rows[13], rows[14]
        forced_interval = {
            "OriginalTopDepth": r0["DEPTH"],
            "OriginalBaseDepth": r1["DEPTH"],
            "ShiftedTopDepth": r0["NEW_DEPTH"],
            "ShiftedBaseDepth": r1["NEW_DEPTH"],
            "DepthShiftInterpolationMethodID": "None",
        }
        mid_depth = (r0["DEPTH"] + r1["DEPTH"]) / 2
        expected_bulk = mid_depth + (r0["NEW_DEPTH"] - r0["DEPTH"])

        shifted_top, _ = shift_sample(mid_depth, None, [forced_interval])
        assert shifted_top == pytest.approx(expected_bulk, abs=1e-6)
