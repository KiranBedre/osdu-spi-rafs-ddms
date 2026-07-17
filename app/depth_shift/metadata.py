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

"""Shared helpers for depth-shift response metadata."""

from typing import Dict, List, Optional, Tuple

from app.api.routes.utils.records import get_id


def get_definitive_wpc_id(sample_record: dict) -> Optional[str]:
    """Read DefinitiveDepthShiftID from a Sample record."""
    record_data = sample_record.get("data", {})
    nested = record_data.get("DefinitiveDepthShift") or {}
    wpc_id = nested.get("DefinitiveDepthShiftID") or record_data.get("DefinitiveDepthShiftID")
    if not wpc_id:
        return None
    return get_id(wpc_id)


def resolve_metadata_warning_state(
    sample_records: Dict[str, dict],
    applied_wpc_id: str,
    used_definitive: bool,
) -> Tuple[bool, List[str]]:
    """Return definitive-availability and metadata warnings for a response."""
    definitive_ids: List[str] = []
    for record in sample_records.values():
        definitive_id = get_definitive_wpc_id(record)
        if definitive_id:
            definitive_ids.append(definitive_id)
    definitive_available = bool(definitive_ids)
    if used_definitive or not definitive_available:
        return (definitive_available, [])

    first_definitive_id = definitive_ids[0]
    if first_definitive_id == get_id(applied_wpc_id):
        return (definitive_available, [])

    warning = (
        "Sample references a definitive depth shift ({0}) that differs from "
        + "the requested depth_shift_id ({1}). RAFS applied the requested depth_shift_id "
        + "because depth_shift_policy=id_provided."
    ).format(first_definitive_id, applied_wpc_id)
    return (definitive_available, [warning])
