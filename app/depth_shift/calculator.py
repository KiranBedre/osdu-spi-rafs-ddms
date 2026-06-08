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

    # Issue-752 AC3: explicit method "None" forces bulk shift.
    force_bulk = _interpolation_method(interval) == "none"

    if force_bulk or abs(orig_span - shifted_span) < _FLOAT_TOLERANCE:  # noqa: WPS459
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
