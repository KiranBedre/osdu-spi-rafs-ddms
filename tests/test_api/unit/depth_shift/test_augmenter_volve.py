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

"""Augmenter integration tests using real Volve field data (Equinor open dataset).

These tests exercise the full in-process pipeline:

    base_df (SampleID) → augment_dataframe
        → _collect_row_warnings (extractor validators)
        → extract_depths (DepthMeasurements navigation)
        → shift_sample (calculator)
        → output columns (SampleTop, ShiftedSampleTop, DepthShiftWarnings)

The Volve depth-shift CSV provides 218 real core-plug pairs used to build
both the shift_set and the expected ShiftedSampleTop values.  Resolver and
UOM validation are not exercised here — those require OSDU connectivity.

All tests are skipped automatically when the CSV is absent from tmp/.
"""

import csv
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import pytest

from app.depth_shift.augmenter import augment_dataframe
from app.depth_shift.calculator import compute_shifted_depth

_DATA_CSV = Path(__file__).resolve().parent / "data" / "no_15_9-19_sr_core_plug_DepthShift.csv"

_WELLBORE_SHIFT = "osdu:master-data--Wellbore:volve-15-9-19-shift:"
_WELLBORE_SAMPLE = "osdu:master-data--Wellbore:volve-15-9-19-shift:"  # matching


def _load_rows() -> List[dict]:
    rows = []
    with open(_DATA_CSV, newline="") as fh:
        reader = csv.DictReader(fh)
        next(reader)  # skip units row
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
    return [
        {
            "OriginalTopDepth": rows[i]["DEPTH"],
            "OriginalBaseDepth": rows[i + 1]["DEPTH"],
            "ShiftedTopDepth": rows[i]["NEW_DEPTH"],
            "ShiftedBaseDepth": rows[i + 1]["NEW_DEPTH"],
        }
        for i in range(len(rows) - 1)
    ]


def _build_sample_records(rows: List[dict], wellbore_id: str) -> Dict[str, dict]:
    """Build fake OSDU Sample records keyed by sample-{i}."""
    return {
        f"sample-{i}": {
            "data": {
                "WellboreID": wellbore_id,
                "DepthMeasurements": [
                    {
                        "VerticalMeasurementTypeID": "SampleTop",
                        "VerticalMeasurementSourceID": "DRL",
                        "VerticalMeasurement": row["DEPTH"],
                    }
                ],
            }
        }
        for i, row in enumerate(rows)
    }


def _build_base_df(rows: List[dict]) -> pd.DataFrame:
    return pd.DataFrame({"SampleID": [f"sample-{i}" for i in range(len(rows))]})


@pytest.fixture(scope="module")
def volve_data() -> Tuple[List[dict], List[dict]]:
    if not _DATA_CSV.exists():
        pytest.skip(f"Volve fixture not found: {_DATA_CSV}")
    rows = _load_rows()
    shift_set = _build_shift_set(rows)
    return rows, shift_set


@pytest.fixture(scope="module")
def volve_augmented(volve_data):
    """Run augment_dataframe once for the interior Volve plugs, matching wellbore.

    The last CSV row (plug 217, depth=4383.0) is the OriginalBaseDepth boundary of
    the last shift interval.  Under the half-open [Top, Base) interval semantics, a
    sample at exactly OriginalBaseDepth falls outside the interval — which is
    spec-correct behaviour.  The fixture excludes this boundary row so that all
    remaining rows (0–216) are genuinely inside an interval and produce stable
    expected results.
    """
    rows, shift_set = volve_data
    interior_rows = rows[:-1]  # exclude boundary row at OriginalBaseDepth
    sample_records = _build_sample_records(interior_rows, _WELLBORE_SAMPLE)
    base_df = _build_base_df(interior_rows)
    result_df, all_warnings = augment_dataframe(
        base_df,
        resolver=None,
        shift_set=shift_set,
        shift_wellbore=_WELLBORE_SHIFT,
        sample_records=sample_records,
    )
    return result_df, interior_rows, all_warnings


class TestShiftedDepthsMatchExpected:
    """ShiftedSampleTop must reproduce the expected NEW_DEPTH for interior plugs.

    The last CSV row is the OriginalBaseDepth of the final interval and is excluded
    from the fixture — see volve_augmented docstring for details.
    """

    def test_all_plugs_shifted_correctly(self, volve_augmented):
        result_df, rows, _ = volve_augmented
        failures = []
        for i, row in enumerate(rows):
            actual = result_df.iloc[i]["ShiftedSampleTop"]
            expected = row["NEW_DEPTH"]
            if abs(actual - expected) > 1e-4:
                failures.append(f"plug {i}: depth={row['DEPTH']}, expected={expected}, got={actual}")
        assert not failures, f"{len(failures)} plug(s) failed:\n" + "\n".join(failures[:5])

    def test_boundary_plug_is_out_of_range(self, volve_data):
        """The last CSV row (depth == OriginalBaseDepth of last interval) is out-of-range.

        Under the half-open [Top, Base) rule, a sample depth equal to OriginalBaseDepth
        falls outside the interval and is passed through unchanged with a warning.
        """
        rows, shift_set = volve_data
        boundary_depth = rows[-1]["DEPTH"]
        sample_records = {
            "sample-boundary": {
                "data": {
                    "WellboreID": _WELLBORE_SAMPLE,
                    "DepthMeasurements": [
                        {
                            "VerticalMeasurementTypeID": "SampleTop",
                            "VerticalMeasurementSourceID": "DRL",
                            "VerticalMeasurement": boundary_depth,
                        }
                    ],
                }
            }
        }
        base_df = pd.DataFrame({"SampleID": ["sample-boundary"]})
        result_df, all_warnings = augment_dataframe(
            base_df,
            resolver=None,
            shift_set=shift_set,
            shift_wellbore=_WELLBORE_SHIFT,
            sample_records=sample_records,
        )
        assert any("Sample not shifted" in w for w in all_warnings)
        assert result_df.iloc[0]["ShiftedSampleTop"] == pytest.approx(boundary_depth, abs=1e-6)

    def test_zero_shift_zone_unchanged(self, volve_augmented):
        """Plugs 0-12 (3643–3647.5 m, DEPTH_DIFF=0) must not be shifted."""
        result_df, rows, _ = volve_augmented
        for i in range(13):
            actual = result_df.iloc[i]["ShiftedSampleTop"]
            assert actual == pytest.approx(
                rows[i]["DEPTH"], abs=1e-6
            ), f"zero-shift plug {i}: expected no shift, got {actual}"

    def test_sample_top_column_holds_original_depth(self, volve_augmented):
        """SampleTop column must preserve the original unshifted depth."""
        result_df, rows, _ = volve_augmented
        for i, row in enumerate(rows):
            assert result_df.iloc[i]["SampleTop"] == pytest.approx(row["DEPTH"], abs=1e-6)

    def test_point_samples_have_no_base(self, volve_augmented):
        """Core plugs are point measurements — SampleBase and ShiftedSampleBase must be None."""
        result_df, _, _ = volve_augmented
        assert result_df["SampleBase"].isna().all()
        assert result_df["ShiftedSampleBase"].isna().all()


class TestWarnings:
    """Warning propagation through the augmenter pipeline."""

    def test_no_warnings_when_wellbore_matches(self, volve_augmented):
        """Matching wellbore + DRL source produces no warnings."""
        result_df, _, all_warnings = volve_augmented
        assert all_warnings == []
        assert all(len(w) == 0 for w in result_df["DepthShiftWarnings"])

    def test_wellbore_mismatch_warns_every_row(self, volve_data):
        """Each interior row gets exactly one warning when sample and shift wellbores differ.

        The last CSV row (boundary point at OriginalBaseDepth) is excluded so that
        every row is genuinely inside an interval and produces only the mismatch warning.
        """
        rows, shift_set = volve_data
        interior_rows = rows[:-1]
        sample_records = _build_sample_records(interior_rows, "osdu:master-data--Wellbore:other:")
        base_df = _build_base_df(interior_rows)
        result_df, all_warnings = augment_dataframe(
            base_df,
            resolver=None,
            shift_set=shift_set,
            shift_wellbore=_WELLBORE_SHIFT,
            sample_records=sample_records,
        )
        assert len(all_warnings) == len(interior_rows)
        assert all(len(w) == 1 for w in result_df["DepthShiftWarnings"])
        assert "mismatch" in all_warnings[0].lower()

    def test_non_driller_source_warns(self, volve_data):
        """VerticalMeasurementSourceID other than DRL triggers a warning."""
        rows, shift_set = volve_data
        # Override source on just the first plug
        sample_records = _build_sample_records(rows, _WELLBORE_SAMPLE)
        sample_records["sample-0"]["data"]["DepthMeasurements"][0]["VerticalMeasurementSourceID"] = "Logger"
        base_df = _build_base_df(rows[:1])
        _, all_warnings = augment_dataframe(
            base_df,
            resolver=None,
            shift_set=shift_set,
            shift_wellbore=_WELLBORE_SHIFT,
            sample_records=sample_records,
        )
        assert len(all_warnings) == 1
        assert "may not need to be shifted" in all_warnings[0]

    def test_unrelated_measurement_non_driller_does_not_warn(self, volve_data):
        """Non-DRL source on a non-Sample measurement must not warn.

        Only SampleTop/SampleBase entries drive the shift, so a non-DRL
        source on e.g. a KB elevation entry is irrelevant (review finding #2).
        """
        rows, shift_set = volve_data
        sample_records = _build_sample_records(rows[:1], _WELLBORE_SAMPLE)
        # SampleTop entry stays DRL; append an unrelated non-DRL entry.
        sample_records["sample-0"]["data"]["DepthMeasurements"].append(
            {
                "VerticalMeasurementTypeID": "osdu:reference-data--VerticalMeasurementType:KB:",
                "VerticalMeasurementSourceID": "Logger",
                "VerticalMeasurement": 25.0,
            }
        )
        base_df = _build_base_df(rows[:1])
        _, all_warnings = augment_dataframe(
            base_df,
            resolver=None,
            shift_set=shift_set,
            shift_wellbore=_WELLBORE_SHIFT,
            sample_records=sample_records,
        )
        assert all_warnings == []


class TestOutOfRangePassThrough:
    """Issue 1: sample depth outside all intervals must pass through unchanged with a warning."""

    def test_out_of_range_sample_passes_through_with_warning(self, volve_data):
        """SampleTop beyond the last interval returns ShiftedSampleTop==SampleTop + warning."""
        rows, shift_set = volve_data
        # Use a depth well beyond the last interval in the Volve shift set.
        out_of_range_depth = 9999.0

        sample_records = {
            "sample-oor": {
                "data": {
                    "WellboreID": _WELLBORE_SAMPLE,
                    "DepthMeasurements": [
                        {
                            "VerticalMeasurementTypeID": "SampleTop",
                            "VerticalMeasurementSourceID": "DRL",
                            "VerticalMeasurement": out_of_range_depth,
                        }
                    ],
                }
            }
        }
        base_df = pd.DataFrame({"SampleID": ["sample-oor"]})
        result_df, all_warnings = augment_dataframe(
            base_df,
            resolver=None,
            shift_set=shift_set,
            shift_wellbore=_WELLBORE_SHIFT,
            sample_records=sample_records,
        )

        shifted_top = result_df.iloc[0]["ShiftedSampleTop"]
        assert shifted_top == pytest.approx(out_of_range_depth, abs=1e-6), (
            f"Expected ShiftedSampleTop == SampleTop ({out_of_range_depth}) for out-of-range sample, "
            f"got {shifted_top}"
        )

        row_warnings = result_df.iloc[0]["DepthShiftWarnings"]
        assert any(
            "Sample not shifted" in warning_msg for warning_msg in row_warnings
        ), f"Expected 'Sample not shifted' warning for out-of-range sample, got: {row_warnings}"
        assert any(
            "9999" in warning_msg for warning_msg in row_warnings
        ), f"Expected warning to include depth value, got: {row_warnings}"
        assert len(all_warnings) >= 1

    def test_in_range_sample_does_not_get_out_of_range_warning(self, volve_augmented):
        """Samples within the shift set must not receive an out-of-range warning."""
        result_df, _, all_warnings = volve_augmented
        for row_warnings in result_df["DepthShiftWarnings"]:
            assert not any(
                "Sample not shifted" in warning_msg for warning_msg in row_warnings
            ), f"Unexpected out-of-range warning on in-range sample: {row_warnings}"


class TestMissingSampleRecords:
    """Rows with no matching sample record must degrade gracefully."""

    def test_missing_record_gives_none_columns(self, volve_data):
        rows, shift_set = volve_data
        base_df = _build_base_df(rows[:5])
        result_df, _ = augment_dataframe(
            base_df,
            resolver=None,
            shift_set=shift_set,
            shift_wellbore=None,
            sample_records={},  # no records at all
        )
        assert result_df["SampleTop"].isna().all()
        assert result_df["ShiftedSampleTop"].isna().all()

    def test_partial_records_shifts_present_only(self, volve_data):
        """Rows with a record are shifted; rows without are None."""
        rows, shift_set = volve_data
        # Only provide records for plugs 0 and 2; plug 1 is missing
        sample_records = _build_sample_records(rows[:3], _WELLBORE_SAMPLE)
        del sample_records["sample-1"]
        base_df = _build_base_df(rows[:3])
        result_df, _ = augment_dataframe(
            base_df,
            resolver=None,
            shift_set=shift_set,
            shift_wellbore=_WELLBORE_SHIFT,
            sample_records=sample_records,
        )
        assert result_df.iloc[0]["ShiftedSampleTop"] is not None
        assert pd.isna(result_df.iloc[1]["ShiftedSampleTop"])
        assert result_df.iloc[2]["ShiftedSampleTop"] is not None

    def test_missing_sample_id_column_raises_400(self, volve_data):
        rows, shift_set = volve_data
        bad_df = pd.DataFrame({"SomethingElse": ["a", "b"]})
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            augment_dataframe(bad_df, None, shift_set, None, {})
        assert exc_info.value.status_code == 400


class TestWellboreMismatchNestedRecord:
    """F1 regression tests — wellbore lookup must use the nested acquisition path."""

    _SHIFT_SET = [
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
    ]

    _SHIFT_WELLBORE = "osdu:master-data--Wellbore:shift-wb:"

    def _make_nested_sample(self, wellbore_id: str) -> dict:
        """Build a sample record with WellboreID only under SampleAcquisitionDetail."""
        return {
            "data": {
                "SampleAcquisition": {
                    "SampleAcquisitionDetail": {
                        "WellboreID": wellbore_id,
                        "TopDepth": 1005.0,
                    }
                }
            }
        }

    def test_nested_wellbore_mismatch_warns(self):
        """Warning fires when WellboreID is nested-only and differs from shift wellbore.

        Before the fix, record_data.get("WellboreID") returned None and no
        warning was emitted.  After the fix, the nested path is checked and
        the mismatch is detected.
        """
        sample_records = {"sample-0": self._make_nested_sample("osdu:master-data--Wellbore:sample-wb:")}
        base_df = pd.DataFrame({"SampleID": ["sample-0"]})
        _, all_warnings = augment_dataframe(
            base_df,
            resolver=None,
            shift_set=self._SHIFT_SET,
            shift_wellbore=self._SHIFT_WELLBORE,
            sample_records=sample_records,
        )
        assert len(all_warnings) >= 1
        assert any("mismatch" in w.lower() for w in all_warnings)

    def test_nested_wellbore_match_no_warning(self):
        """No wellbore warning when nested WellboreID matches the shift wellbore."""
        sample_records = {"sample-0": self._make_nested_sample(self._SHIFT_WELLBORE)}
        base_df = pd.DataFrame({"SampleID": ["sample-0"]})
        _, all_warnings = augment_dataframe(
            base_df,
            resolver=None,
            shift_set=self._SHIFT_SET,
            shift_wellbore=self._SHIFT_WELLBORE,
            sample_records=sample_records,
        )
        assert not any("mismatch" in w.lower() for w in all_warnings)


class TestCrossIntervalGuard:
    """Augmenter must use SampleTop's interval for SampleBase when the sample
    spans across a DepthShiftSet interval boundary (TR-DS-05).

    Without the guard, SampleBase would be shifted using a different interval
    than SampleTop, producing an inconsistent shift and an incorrect sample size.
    This class validates that the guard holds end-to-end through augment_dataframe.
    """

    def test_base_beyond_interval_uses_top_interval(self, volve_data):
        """SampleBase > OriginalBaseDepth of SampleTop's interval still uses that interval."""
        rows, shift_set = volve_data
        # rows[13]: DEPTH=4328.85 → shift_set[13] (OriginalTop=4328.85, OriginalBase=4329.0)
        # rows[15]: DEPTH=4329.25 → would fall in shift_set[14] if looked up independently
        sample_top_depth = rows[13]["DEPTH"]
        sample_base_depth = rows[15]["DEPTH"]

        sample_records = {
            "sample-0": {
                "data": {
                    "WellboreID": _WELLBORE_SAMPLE,
                    "DepthMeasurements": [
                        {
                            "VerticalMeasurementTypeID": "SampleTop",
                            "VerticalMeasurementSourceID": "DRL",
                            "VerticalMeasurement": sample_top_depth,
                        },
                        {
                            "VerticalMeasurementTypeID": "SampleBase",
                            "VerticalMeasurementSourceID": "DRL",
                            "VerticalMeasurement": sample_base_depth,
                        },
                    ],
                }
            }
        }
        base_df = pd.DataFrame({"SampleID": ["sample-0"]})
        result_df, _ = augment_dataframe(
            base_df,
            resolver=None,
            shift_set=shift_set,
            shift_wellbore=_WELLBORE_SHIFT,
            sample_records=sample_records,
        )

        interval_13 = shift_set[13]
        expected_shifted_top = compute_shifted_depth(sample_top_depth, interval_13)
        expected_shifted_base = compute_shifted_depth(sample_base_depth, interval_13)

        assert result_df.iloc[0]["ShiftedSampleTop"] == pytest.approx(expected_shifted_top, abs=1e-6)
        assert result_df.iloc[0]["ShiftedSampleBase"] == pytest.approx(expected_shifted_base, abs=1e-6)

        # Confirm result would differ had we incorrectly used shift_set[14] for the base
        wrong_shifted_base = compute_shifted_depth(sample_base_depth, shift_set[14])
        assert (
            abs(result_df.iloc[0]["ShiftedSampleBase"] - wrong_shifted_base) > 1e-4
        ), "Cross-interval guard did not fire — base was computed with the wrong interval"
