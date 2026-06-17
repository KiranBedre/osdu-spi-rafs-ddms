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

"""Unit tests for depth shift metadata helper functions."""

from app.depth_shift.metadata import resolve_metadata_warning_state


def test_resolve_metadata_warning_state_treats_trailing_colon_ids_as_equal():
    """No warning when definitive and requested IDs differ only by trailing colon."""
    sample_records = {
        "sample_1": {
            "data": {
                "DefinitiveDepthShift": {
                    "DefinitiveDepthShiftID": "osdu:work-product-component--DepthShift:rafs_depthshift_001:",
                }
            }
        }
    }

    definitive_available, warnings = resolve_metadata_warning_state(
        sample_records=sample_records,
        applied_wpc_id="osdu:work-product-component--DepthShift:rafs_depthshift_001",
        used_definitive=False,
    )

    assert definitive_available is True
    assert warnings == []


def test_resolve_metadata_warning_state_warns_on_true_id_mismatch():
    """Warning is returned when definitive and requested IDs are genuinely different."""
    sample_records = {
        "sample_1": {
            "data": {
                "DefinitiveDepthShift": {
                    "DefinitiveDepthShiftID": "osdu:work-product-component--DepthShift:definitive_001:",
                }
            }
        }
    }

    definitive_available, warnings = resolve_metadata_warning_state(
        sample_records=sample_records,
        applied_wpc_id="osdu:work-product-component--DepthShift:provided_001",
        used_definitive=False,
    )

    assert definitive_available is True
    assert len(warnings) == 1
    assert "definitive_001" in warnings[0]
    assert "provided_001" in warnings[0]
