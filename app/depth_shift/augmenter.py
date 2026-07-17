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
  SampleBase         – original measured base depth (None when not present on the sample)
  SampleMean         – original measured mean/point depth (None when not present on the sample)
  ShiftedSampleTop   – depth-shifted SampleTop
  ShiftedSampleBase  – depth-shifted SampleBase (None when not present on the sample)
  ShiftedSampleMean  – depth-shifted SampleMean (None when not present on the sample)
  DepthShiftWarnings – list of warning strings (non-Driller source, wellbore mismatch…)

A Sample provides a depth range (Top+Base) or a single point depth (Top
alone, Base alone, or Mean alone). The interval used to shift is always
located via the anchor depth, in SampleTop > SampleBase > SampleMean
priority order — see app.depth_shift.calculator.select_anchor_depth.
"""

from typing import Dict, List, NamedTuple, Optional, Tuple

import pandas as pd
from fastapi import HTTPException
from loguru import logger
from starlette import status

from app.depth_shift.calculator import select_anchor_depth, shift_sample
from app.depth_shift.extractor import (
    extract_depths,
    extract_sample_wellbore_id,
    is_sample_depth_entry,
    validate_depth_shift_uom,
    validate_measurement_source,
    validate_wellbore_match,
)


class _RowResult(NamedTuple):
    sample_top: Optional[float]
    sample_base: Optional[float]
    sample_mean: Optional[float]
    shifted_top: Optional[float]
    shifted_base: Optional[float]
    shifted_mean: Optional[float]
    warnings: List[str]


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
    has_depth_entries = any(is_sample_depth_entry(entry) for entry in vertical_measurements)
    if not has_depth_entries:
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
            if synthesized:
                warnings.append(
                    "Sample depths sourced from SampleAcquisitionDetail (TopDepth/BaseDepth)"
                    " because DepthMeasurements is absent or contains no recognizable depth entries."
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


def _depth_source_warning(
    sample_id: str,
    anchor_field: Optional[str],
    sample_mean: Optional[float],
) -> Optional[str]:
    """Return a warning when the shift anchor fell back to SampleBase or SampleMean.

    No warning is needed when SampleTop drove the shift — that is the
    default case for any Sample carrying a single depth.

    :param sample_id: OSDU Sample record ID, used in the warning text
    :type sample_id: str
    :param anchor_field: field returned by select_anchor_depth
        ("SampleTop"/"SampleBase"/"SampleMean"/None)
    :type anchor_field: Optional[str]
    :param sample_mean: SampleMean value; used to detect the Base+Mean
        combination (Mean is ignored, but the warning should say so)
    :type sample_mean: Optional[float]
    :return: warning string, or None when the anchor is SampleTop or absent
    :rtype: Optional[str]
    """
    if anchor_field == "SampleBase":
        mean_note = "" if sample_mean is None else " (SampleMean ignored)"
        return (
            f"No SampleTop provided for {sample_id}. Sample has been shifted based on "
            + f"SampleBase depth{mean_note}."
        )
    if anchor_field == "SampleMean":
        return (
            f"No SampleTop or SampleBase provided for {sample_id}. "
            + "Sample has been shifted based on SampleMean depth."
        )
    return None


def _augment_row(  # noqa: WPS210
    sample_id: str,
    sample_records: Dict[str, dict],
    shift_set: List[dict],
    shift_wellbore: Optional[str],
    shift_meta: Optional[List[dict]] = None,
) -> "_RowResult":
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
    :return: row result with original and shifted depths plus warnings
    :rtype: _RowResult
    """
    sample_record = sample_records.get(sample_id)
    warnings = _collect_row_warnings(sample_record, shift_wellbore, shift_meta)

    if not sample_record:
        logger.warning(f"Sample record not found for ID {sample_id!r}; skipping shift.")
        return _RowResult(None, None, None, None, None, None, warnings)

    sample_top, sample_base, sample_mean, _ = extract_depths(sample_record)
    anchor_depth, anchor_field = select_anchor_depth(sample_top, sample_base, sample_mean)

    if anchor_depth is None:
        logger.warning(f"No SampleTop, SampleBase, or SampleMean found in Sample {sample_id!r}; skipping shift.")
        return _RowResult(sample_top, sample_base, sample_mean, None, None, None, warnings)

    depth_source_warning = _depth_source_warning(sample_id, anchor_field, sample_mean)
    if depth_source_warning:
        warnings.append(depth_source_warning)
        logger.warning(f"[depth-shift audit] {depth_source_warning}")

    shifted_top, shifted_base, shifted_mean = shift_sample(sample_top, sample_base, sample_mean, shift_set)

    if shifted_top is None and shifted_base is None and shifted_mean is None:
        # Anchor depth found but outside all shift intervals — pass through unchanged.
        shifted_top, shifted_base, shifted_mean = sample_top, sample_base, sample_mean
        out_of_range_msg = "Sample not shifted: {0} {1:.3f} falls outside all shift intervals.".format(
            anchor_field,
            anchor_depth,
        )
        warnings.append(out_of_range_msg)
        logger.warning(f"[depth-shift audit] {out_of_range_msg}")

    return _RowResult(sample_top, sample_base, sample_mean, shifted_top, shifted_base, shifted_mean, warnings)


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
    means: List[Optional[float]] = []
    shifted_tops: List[Optional[float]] = []
    shifted_bases: List[Optional[float]] = []
    shifted_means: List[Optional[float]] = []
    row_warnings: List[List[str]] = []
    all_warnings: List[str] = []

    for sample_id in base_df["SampleID"]:
        row = _augment_row(
            "" if sample_id is None else str(sample_id).rstrip(":"),
            sample_records,
            shift_set,
            shift_wellbore,
            shift_meta,
        )
        tops.append(row.sample_top)
        bases.append(row.sample_base)
        means.append(row.sample_mean)
        shifted_tops.append(row.shifted_top)
        shifted_bases.append(row.shifted_base)
        shifted_means.append(row.shifted_mean)
        row_warnings.append(row.warnings)
        all_warnings.extend(row.warnings)

    df = base_df.copy()
    df["SampleTop"] = pd.array(tops, dtype=object)
    df["SampleBase"] = pd.array(bases, dtype=object)
    df["SampleMean"] = pd.array(means, dtype=object)
    df["ShiftedSampleTop"] = pd.array(shifted_tops, dtype=object)
    df["ShiftedSampleBase"] = pd.array(shifted_bases, dtype=object)
    df["ShiftedSampleMean"] = pd.array(shifted_means, dtype=object)
    df["DepthShiftWarnings"] = row_warnings

    return (df, all_warnings)
