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

"""SampleDepthExtractor: navigate Sample OSDU record to extract depths.

All logic is pure dict manipulation — no I/O, no service calls.

Navigates data.DepthMeasurements[] and matches
VerticalMeasurementTypeID by trailing suffix ("SampleTop" / "SampleBase")
to handle both bare strings and full OSDU reference-data IDs.
"""

from typing import List, Optional, Tuple

from app.api.routes.utils.records import get_id


def extract_sample_wellbore_id(sample_record: dict) -> Optional[str]:
    """Resolve the WellboreID from a Sample OSDU record.

    Checks nested path ``data.SampleAcquisition.SampleAcquisitionDetail.WellboreID``
    first, then falls back to the top-level ``data.WellboreID``.

    :param sample_record: full Sample OSDU record dict
    :type sample_record: dict
    :return: WellboreID string, or None if absent
    :rtype: Optional[str]
    """
    record_data = sample_record.get("data", {}) if isinstance(sample_record, dict) else {}
    acquisition = record_data.get("SampleAcquisition", {}) if isinstance(record_data, dict) else {}
    detail = acquisition.get("SampleAcquisitionDetail", {}) if isinstance(acquisition, dict) else {}
    nested_wellbore_id = detail.get("WellboreID") if isinstance(detail, dict) else None
    if nested_wellbore_id:
        return nested_wellbore_id
    return record_data.get("WellboreID") if isinstance(record_data, dict) else None


def _matches_type(type_id: str, suffix: str) -> bool:
    """Return True if *type_id* ends with *suffix* (case-insensitive).

    Handles both bare strings ("SampleTop") and full OSDU IDs
    ("osdu:reference-data--VerticalMeasurementType:SampleTop:").
    """
    return type_id.rstrip(":").lower().endswith(suffix.lower())


def extract_depths(  # noqa: WPS231,CCR001,WPS210
    sample_record: dict,
) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """Extract (top, base, wellbore_id) from a Sample OSDU record.

    :param sample_record: full Sample OSDU record dict (must contain a
        'data' key)
    :type sample_record: dict
    :return: (sample_top, sample_base, wellbore_id); any element may be
        None if the record does not carry it
    :rtype: Tuple[Optional[float], Optional[float], Optional[str]]
    """
    record_data = sample_record.get("data", {})
    wellbore_id: Optional[str] = record_data.get("WellboreID")

    vertical_measurements: List[dict] = record_data.get("DepthMeasurements", [])

    sample_top: Optional[float] = None
    sample_base: Optional[float] = None

    for entry in vertical_measurements:
        type_id = entry.get("VerticalMeasurementTypeID", "")
        raw_value = entry.get("VerticalMeasurement")
        if raw_value is None:
            continue
        try:
            depth_value = float(raw_value)
        except (TypeError, ValueError):
            continue

        if _matches_type(type_id, "SampleTop"):
            sample_top = depth_value
        elif _matches_type(type_id, "SampleBase"):
            sample_base = depth_value

    if sample_top is None and sample_base is None:
        acquisition = record_data.get("SampleAcquisition", {}) if isinstance(record_data, dict) else {}
        detail = acquisition.get("SampleAcquisitionDetail", {}) if isinstance(acquisition, dict) else {}
        if isinstance(detail, dict):
            raw_top = detail.get("TopDepth")
            raw_base = detail.get("BaseDepth")
            try:
                sample_top = float(raw_top) if raw_top is not None else None  # noqa: WPS504
            except (TypeError, ValueError):
                sample_top = None
            try:
                sample_base = float(raw_base) if raw_base is not None else None  # noqa: WPS504
            except (TypeError, ValueError):
                sample_base = None
            if not wellbore_id:
                nested_wellbore = detail.get("WellboreID")
                if isinstance(nested_wellbore, str):
                    wellbore_id = nested_wellbore

    return (sample_top, sample_base, wellbore_id)


def is_sample_depth_entry(vm_entry: dict) -> bool:
    """Return True when the entry measures SampleTop or SampleBase.

    Used to restrict source-quality warnings to the depth measurements that
    actually drive the shift, ignoring unrelated entries (e.g. KB elevation).

    :param vm_entry: a single VerticalMeasurements entry
    :type vm_entry: dict
    :return: True if VerticalMeasurementTypeID is SampleTop or SampleBase
    :rtype: bool
    """
    type_id = vm_entry.get("VerticalMeasurementTypeID", "")
    return _matches_type(type_id, "SampleTop") or _matches_type(type_id, "SampleBase")


def validate_measurement_source(vm_entry: dict) -> Optional[str]:
    """Return a warning string when VerticalMeasurementSourceID does not end with 'DRL'.

    :param vm_entry: a single VerticalMeasurements entry
    :type vm_entry: dict
    :return: warning string, or None if source ends with 'DRL'
    :rtype: Optional[str]
    """
    source_id = vm_entry.get("VerticalMeasurementSourceID", "")
    if not source_id or not _matches_type(source_id, "DRL"):
        source_display = source_id.rstrip(":").rsplit(":", 1)[-1] if source_id else "(not set)"
        return (
            "Warning: Sample depths (SampleTop and SampleBase) are reported as"
            + " '{0}' depth and may not need to be shifted.".format(source_display)
            + " Expected source is Driller (DRL). Shifted depths may need to be validated."
        )
    return None


def validate_wellbore_match(
    sample_wellbore: Optional[str],
    shift_wellbore: Optional[str],
) -> Optional[str]:
    """Return a warning string when wellbore IDs do not match.

    :param sample_wellbore: WellboreID from the Sample record
    :type sample_wellbore: Optional[str]
    :param shift_wellbore: WellboreID from the DepthShift WPC record
    :type shift_wellbore: Optional[str]
    :return: warning string, or None if they match (or both are None)
    :rtype: Optional[str]
    """
    if sample_wellbore is None or shift_wellbore is None:
        return None
    if get_id(sample_wellbore) != get_id(shift_wellbore):
        return (
            f"Wellbore mismatch: sample wellbore '{sample_wellbore}'"
            + f" differs from depth-shift wellbore '{shift_wellbore}'."
        )
    return None


def validate_depth_shift_uom(  # noqa: WPS324
    shift_meta: List[dict],
    sample_record: dict,
) -> Optional[str]:
    """Placeholder: validate that sample and depth-shift units of measure match.

    Unit normalisation is not yet implemented (see Issue-752 AC). This
    function always returns None (no error) until that logic is added.

    :param shift_meta: list of Meta dicts from the CoreToLog parquet
    :type shift_meta: List[dict]
    :param sample_record: full Sample OSDU record dict
    :type sample_record: dict
    :return: error string if units mismatch, None otherwise
    :rtype: Optional[str]
    """
    return None  # noqa: WPS324
