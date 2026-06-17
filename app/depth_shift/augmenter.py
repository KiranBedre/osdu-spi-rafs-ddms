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

"""Augmenter: merge depth-shift columns onto a SA bulk-data DataFrame.

Output shape is documented by DepthShiftRowData in
app.models.schemas.depth_shift_query.  The extra columns added are:

  SampleTop          – original measured top depth (from Sample VerticalMeasurements)
  SampleBase         – original measured base depth (None for point samples)
  ShiftedSampleTop   – depth-shifted SampleTop
  ShiftedSampleBase  – depth-shifted SampleBase (None for point samples)
  DepthShiftWarnings – list of warning strings (non-Driller source, wellbore mismatch…)
"""

from typing import Dict, List, Optional, Tuple

import pandas as pd
from fastapi import HTTPException
from loguru import logger
from starlette import status

from app.depth_shift.calculator import shift_sample
from app.depth_shift.extractor import (
    extract_depths,
    extract_sample_wellbore_id,
    is_sample_depth_entry,
    validate_depth_shift_uom,
    validate_measurement_source,
    validate_wellbore_match,
)


def _source_quality_warning(vertical_measurements: List[dict]) -> Optional[str]:
    """Return the first non-Driller warning among SampleTop/SampleBase entries.

    Only the SampleTop/SampleBase measurements drive the shift, so unrelated
    measurement entries (e.g. KB elevation) are ignored.

    :param vertical_measurements: VerticalMeasurements entries from the Sample
    :type vertical_measurements: List[dict]
    :return: warning string for the first non-Driller sample-depth entry, or None
    :rtype: Optional[str]
    """
    for entry in vertical_measurements:
        if not is_sample_depth_entry(entry):
            continue
        source_warning = validate_measurement_source(entry)
        if source_warning:
            return source_warning
    return None


def _collect_row_warnings(  # noqa: CCR001,WPS210,WPS231
    sample_record: Optional[dict],
    shift_wellbore: Optional[str],
    shift_meta: Optional[List[dict]] = None,
) -> List[str]:
    """Collect non-blocking warnings for a single row.

    :param sample_record: full Sample OSDU record (may be None if missing)
    :type sample_record: Optional[dict]
    :param shift_wellbore: WellboreID from DepthShift WPC record
    :type shift_wellbore: Optional[str]
    :param shift_meta: Meta dicts from CoreToLog parquet (may be None)
    :type shift_meta: Optional[List[dict]]
    :return: list of warning strings (may be empty)
    :rtype: List[str]
    """
    if shift_meta is None:
        shift_meta = []

    if not sample_record:
        return []

    warnings: List[str] = []
    record_data = sample_record.get("data", {})
    vertical_measurements = record_data.get("DepthMeasurements", [])
    if not vertical_measurements:
        acquisition = record_data.get("SampleAcquisition", {}) if isinstance(record_data, dict) else {}
        detail = acquisition.get("SampleAcquisitionDetail", {}) if isinstance(acquisition, dict) else {}
        if isinstance(detail, dict):
            vm = detail.get("VerticalMeasurement", {})
            source_id = vm.get("VerticalMeasurementSourceID") if isinstance(vm, dict) else None
            synthesized: List[dict] = []
            if detail.get("TopDepth") is not None:
                synthesized.append(
                    {
                        "VerticalMeasurementTypeID": "SampleTop",
                        "VerticalMeasurement": detail.get("TopDepth"),
                        "VerticalMeasurementSourceID": source_id,
                    },
                )
            if detail.get("BaseDepth") is not None:
                synthesized.append(
                    {
                        "VerticalMeasurementTypeID": "SampleBase",
                        "VerticalMeasurement": detail.get("BaseDepth"),
                        "VerticalMeasurementSourceID": source_id,
                    },
                )
            vertical_measurements = synthesized

    source_warning = _source_quality_warning(vertical_measurements)
    if source_warning:
        warnings.append(source_warning)
        logger.warning(f"[depth-shift audit] {source_warning}")

    wellbore_id = extract_sample_wellbore_id(sample_record)
    wellbore_warning = validate_wellbore_match(wellbore_id, shift_wellbore)
    if wellbore_warning:
        warnings.append(wellbore_warning)
        logger.warning(f"[depth-shift audit] {wellbore_warning}")

    uom_error = validate_depth_shift_uom(shift_meta, sample_record)  # pylint: disable=assignment-from-none
    if uom_error:
        warnings.append(uom_error)

    return warnings


def _augment_row(
    sample_id: str,
    sample_records: Dict[str, dict],
    shift_set: List[dict],
    shift_wellbore: Optional[str],
    shift_meta: Optional[List[dict]] = None,
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], List[str]]:
    """Compute augmented columns for a single DataFrame row.

    :param sample_id: OSDU Sample record ID from the bulk-data row
    :type sample_id: str
    :param sample_records: dict mapping sample ID → full record
    :type sample_records: Dict[str, dict]
    :param shift_set: list of CoreToLog shift intervals
    :type shift_set: List[dict]
    :param shift_wellbore: WellboreID from DepthShift WPC record
    :type shift_wellbore: Optional[str]
    :param shift_meta: Meta dicts from CoreToLog parquet (may be None)
    :type shift_meta: Optional[List[dict]]
    :return: (sample_top, sample_base, shifted_top, shifted_base, warnings)
    :rtype: Tuple[...]
    """
    sample_record = sample_records.get(sample_id)
    warnings = _collect_row_warnings(sample_record, shift_wellbore, shift_meta)

    if not sample_record:
        logger.warning(f"Sample record not found for ID {sample_id!r}; skipping shift.")
        return (None, None, None, None, warnings)

    sample_top, sample_base, _ = extract_depths(sample_record)

    if sample_top is None:
        logger.warning(f"SampleTop not found in Sample {sample_id!r}; skipping shift.")
        return (sample_top, sample_base, None, None, warnings)

    shifted_top, shifted_base = shift_sample(sample_top, sample_base, shift_set)

    if shifted_top is None:
        # Sample depth found but outside all shift intervals — pass through unchanged.
        shifted_top = sample_top
        shifted_base = sample_base
        out_of_range_msg = "Sample not shifted: SampleTop {0:.3f} falls outside all shift intervals.".format(
            sample_top,
        )
        warnings.append(out_of_range_msg)
        logger.warning(f"[depth-shift audit] {out_of_range_msg}")

    return (sample_top, sample_base, shifted_top, shifted_base, warnings)


def augment_dataframe(  # noqa: WPS210,CCR001,WPS231
    base_df: pd.DataFrame,
    resolver,
    shift_set: List[dict],
    shift_wellbore: Optional[str],
    sample_records: Dict[str, dict],
    shift_meta: Optional[List[dict]] = None,
) -> Tuple[pd.DataFrame, List[str]]:
    """Add depth-shift columns to *base_df* and return (augmented_df, all_warnings).

    The input *base_df* must have a 'SampleID' column; a 400 is raised if
    it is absent.

    :param base_df: original SA bulk-data DataFrame
    :type base_df: pd.DataFrame
    :param resolver: DepthShiftResolver (unused here; kept for DI symmetry)
    :type resolver: DepthShiftResolver
    :param shift_set: list of CoreToLog shift interval dicts
    :type shift_set: List[dict]
    :param shift_wellbore: WellboreID from DepthShift WPC record
    :type shift_wellbore: Optional[str]
    :param sample_records: pre-fetched dict of sample ID → record
    :type sample_records: Dict[str, dict]
    :return: (augmented DataFrame, flat list of all warning strings)
    :rtype: Tuple[pd.DataFrame, List[str]]
    :raises HTTPException: 400 if 'SampleID' column is absent from base_df

    .. note:: *shift_set* is assumed to have been validated by the resolver
        (via ``validate_shift_values``) before this function is called.
        Interval ordering and boundary checks are not repeated here.
    """
    if "SampleID" not in base_df.columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Depth-shift augmentation requires a 'SampleID' column in the bulk data, but it was not found."
                + " Only analysis types that carry per-row SampleID are supported for depth-shift retrieval."
            ),
        )

    tops: List[Optional[float]] = []
    bases: List[Optional[float]] = []
    shifted_tops: List[Optional[float]] = []
    shifted_bases: List[Optional[float]] = []
    row_warnings: List[List[str]] = []
    all_warnings: List[str] = []

    for sample_id in base_df["SampleID"]:
        top, base, s_top, s_base, warnings = _augment_row(  # noqa: WPS236
            "" if sample_id is None else str(sample_id).rstrip(":"),
            sample_records,
            shift_set,
            shift_wellbore,
            shift_meta,
        )
        tops.append(top)
        bases.append(base)
        shifted_tops.append(s_top)
        shifted_bases.append(s_base)
        row_warnings.append(warnings)
        all_warnings.extend(warnings)

    df = base_df.copy()
    df["SampleTop"] = tops
    df["SampleBase"] = bases
    df["ShiftedSampleTop"] = shifted_tops
    df["ShiftedSampleBase"] = shifted_bases
    df["DepthShiftWarnings"] = row_warnings

    return (df, all_warnings)
