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

"""Pure-function depth-shift calculator.

No I/O, no service calls.  All domain rules TR-DS-01 through TR-DS-05
are implemented here and are fully exercisable with plain pytest.

Interval dict keys (matching the CoreToLog parquet schema):
OriginalTopDepth, OriginalBaseDepth, ShiftedTopDepth, ShiftedBaseDepth.
"""

import bisect
from typing import List, Optional

_FLOAT_TOLERANCE = 1e-9
_REQUIRED_INTERVAL_FIELDS = (
    "OriginalTopDepth",
    "OriginalBaseDepth",
    "ShiftedTopDepth",
    "ShiftedBaseDepth",
)


def _validate_no_inversion(shift_set: List[dict]) -> None:
    """Raise ValueError when any interval has OriginalBaseDepth <= OriginalTopDepth.

    :param shift_set: list of shift-set interval dicts (boundaries already non-null)
    :type shift_set: List[dict]
    :raises ValueError: when any interval is inverted or zero-width
    """
    for idx, row in enumerate(shift_set):
        orig_top = row["OriginalTopDepth"]
        orig_base = row["OriginalBaseDepth"]
        if orig_base <= orig_top:
            raise ValueError(
                "DepthShiftSet row at index {0}: OriginalBaseDepth ({1}) must be greater than "
                "OriginalTopDepth ({2}). Inverted or zero-width intervals are not allowed.".format(
                    idx,
                    orig_base,
                    orig_top,
                )
            )


def _validate_no_overlap(shift_set: List[dict]) -> None:
    """Raise ValueError when any two consecutive intervals overlap.

    Touching boundaries (interval_i base == interval_{i+1} top) are valid.
    Overlap means strict: interval_i base > interval_{i+1} top.

    :param shift_set: list of shift-set interval dicts sorted by OriginalTopDepth
    :type shift_set: List[dict]
    :raises ValueError: when consecutive intervals overlap
    """
    for interval_idx in range(len(shift_set) - 1):
        current_base = shift_set[interval_idx]["OriginalBaseDepth"]
        next_top = shift_set[interval_idx + 1]["OriginalTopDepth"]
        if current_base > next_top:
            raise ValueError(
                "DepthShiftSet has overlapping intervals: interval at index {0} "
                "(OriginalBaseDepth={1}) overlaps interval at index {2} "
                "(OriginalTopDepth={3}). Intervals must not overlap.".format(
                    interval_idx,
                    current_base,
                    interval_idx + 1,
                    next_top,
                )
            )


def _validate_no_bilinear(shift_set: List[dict]) -> None:
    """Raise ValueError when any interval specifies Bilinear interpolation.

    Bilinear interpolation is a 2-D method and is not applicable to 1-D
    depth-shift calculations.  Clients must use Linear or leave the field absent.

    :param shift_set: list of shift-set interval dicts
    :type shift_set: List[dict]
    :raises ValueError: when any interval has a Bilinear interpolation method
    """
    for idx, row in enumerate(shift_set):
        method_token = _interpolation_method(row)
        if method_token == "bilinear":  # noqa: S105
            raise ValueError(
                "DepthShiftSet row at index {0}: DepthShiftInterpolationMethodID "
                "resolves to 'bilinear', which is not supported for 1-D depth-shift "
                "calculations. Use 'linear' or leave the field absent for auto-detect.".format(idx)
            )


def validate_shift_values(shift_set: List[dict]) -> None:
    """Raise ValueError if any required depth boundary in shift_set is null or missing.

    Also validates that intervals are non-inverted, non-overlapping, and do not
    specify an unsupported interpolation method (bilinear).

    Called both at write time (POST CoreToLog data) and at read time (GET with
    depth shift) so that invalid intervals are rejected regardless of ingestion path.

    :param shift_set: list of shift-set interval dicts
    :type shift_set: List[dict]
    :raises ValueError: when any interval boundary is null/absent, inverted,
        overlapping with its neighbour, or specifies bilinear interpolation
    """
    for idx, row in enumerate(shift_set):
        for field in _REQUIRED_INTERVAL_FIELDS:
            if row.get(field) is None:
                raise ValueError(
                    "DepthShiftSet row at index {0} has null or missing '{1}'. "
                    "Cannot apply a depth shift with null interval boundaries.".format(idx, field)
                )
    _validate_no_inversion(shift_set)
    _validate_no_overlap(shift_set)
    _validate_no_bilinear(shift_set)


def _validate_intervals(shift_set: List[dict]) -> None:
    """Raise ValueError if OriginalTopDepth values are not strictly increasing.

    :param shift_set: list of shift-set interval dicts
    :type shift_set: List[dict]
    :raises ValueError: when the sequence is not monotonically increasing
    """
    tops = [row["OriginalTopDepth"] for row in shift_set]
    for idx, current_top in enumerate(tops[1:], start=1):
        previous_top = tops[idx - 1]
        if current_top <= previous_top:
            raise ValueError(
                f"OriginalTopDepth must be strictly increasing. "
                f"Found {current_top} at index {idx} after {previous_top}.",
            )


def find_interval(shift_set: List[dict], sample_top: float) -> Optional[dict]:
    """Return the shift interval that *contains* *sample_top*, or None.

    The candidate interval is the one whose OriginalTopDepth is the largest
    value that is still <= sample_top (a right-open bin search). Containment
    is then enforced: the candidate is only returned when *sample_top* lies
    within it (OriginalTopDepth <= sample_top <= OriginalBaseDepth).

    Returns None when *sample_top* is shallower than the first interval, falls
    in a gap between intervals, or is deeper than the last interval's
    OriginalBaseDepth. This prevents fabricating shifted values for samples
    that no interval actually covers.

    :param shift_set: list of shift-set interval dicts, sorted ascending
        by OriginalTopDepth; must have been validated with _validate_intervals
    :type shift_set: List[dict]
    :param sample_top: sample depth to locate
    :type sample_top: float
    :return: matching interval dict, or None
    :rtype: Optional[dict]
    """
    tops = [row["OriginalTopDepth"] for row in shift_set]
    pos = bisect.bisect_right(tops, sample_top) - 1
    if pos < 0:
        return None
    interval = shift_set[pos]
    if sample_top > interval["OriginalBaseDepth"]:
        return None
    return interval


def _interpolation_method(interval: dict) -> str:
    """Return the normalised trailing token of InterpolationMethodID, or ''.

    Handles bare strings ("None", "Linear") and full OSDU reference IDs
    ("osdu:reference-data--DepthShiftInterpolationMethod:None:").
    Returns empty string when the key is absent or empty.

    :param interval: shift-set interval dict
    :type interval: dict
    :return: lower-case trailing token, e.g. 'none', 'linear', or ''
    :rtype: str
    """
    raw = interval.get("DepthShiftInterpolationMethodID", "")
    if not raw:
        return ""
    return raw.rstrip(":").rsplit(":", 1)[-1].lower()


def compute_shifted_depth(depth: float, interval: dict) -> float:
    """Shift *depth* using the given CoreToLog interval.

    If the interval is equal-size (ShiftedBase-ShiftedTop == OrigBase-OrigTop)
    a constant bulk shift is applied.  Otherwise linear interpolation
    within the interval is used (TR-DS-02).

    :param depth: original measured depth to shift
    :type depth: float
    :param interval: shift-set interval dict
    :type interval: dict
    :return: shifted depth value
    :rtype: float
    """
    orig_top = interval["OriginalTopDepth"]
    orig_base = interval["OriginalBaseDepth"]
    shifted_top = interval["ShiftedTopDepth"]
    shifted_base = interval["ShiftedBaseDepth"]

    orig_span = orig_base - orig_top
    shifted_span = shifted_base - shifted_top

    # Auto-detect: absent, empty, or explicit "None" token all fall through to span
    # comparison.  "None" means "method not specified" — it does not force bulk shift.
    if abs(orig_span - shifted_span) < _FLOAT_TOLERANCE:  # noqa: WPS459
        return depth + (shifted_top - orig_top)

    if orig_span == 0:
        return shifted_top

    relative_pos = (depth - orig_top) / orig_span
    return shifted_top + relative_pos * shifted_span


def shift_sample(
    sample_top: float,
    sample_base: Optional[float],
    shift_set: List[dict],
) -> tuple:
    """Compute shifted top and base for a single sample.

    SampleBase uses *SampleTop*'s interval (cross-interval guard, TR-DS-04).
    If sample_top has no enclosing interval, both outputs are None.
    If sample_base is None (point measurement), ShiftedSampleBase is also None.

    :param sample_top: original top depth
    :type sample_top: float
    :param sample_base: original base depth, or None for a point measurement
    :type sample_base: Optional[float]
    :param shift_set: sorted list of shift-set interval dicts
    :type shift_set: List[dict]
    :return: (shifted_top, shifted_base); either may be None
    :rtype: tuple
    :raises ValueError: when shift_set is non-monotonic (propagated from
        _validate_intervals)
    """
    interval = find_interval(shift_set, sample_top)
    if interval is None:
        return (None, None)

    shifted_top = compute_shifted_depth(sample_top, interval)
    shifted_base = None
    if sample_base is not None:
        shifted_base = compute_shifted_depth(sample_base, interval)

    return (shifted_top, shifted_base)
