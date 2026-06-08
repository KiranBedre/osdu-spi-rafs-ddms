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

"""Unit tests for app.depth_shift.extractor (no mocks, pure dict manipulation)."""

from app.depth_shift.extractor import (
    extract_depths,
    validate_measurement_source,
    validate_wellbore_match,
)


def _make_sample(top=1872.0, base=1900.0, source="Driller", wellbore="ns:master-data--Wellbore:wb-001:"):
    return {
        "data": {
            "WellboreID": wellbore,
            "DepthMeasurement": {
                "VerticalMeasurements": [
                    {
                        "VerticalMeasurementTypeID": "osdu:reference-data--VerticalMeasurementType:SampleTop:",
                        "VerticalMeasurementValue": top,
                        "VerticalMeasurementSourceID": f"osdu:reference-data--VerticalMeasurementSource:{source}:",
                    },
                    {
                        "VerticalMeasurementTypeID": "osdu:reference-data--VerticalMeasurementType:SampleBase:",
                        "VerticalMeasurementValue": base,
                        "VerticalMeasurementSourceID": f"osdu:reference-data--VerticalMeasurementSource:{source}:",
                    },
                ],
            },
        },
    }


class TestExtractDepths:
    def test_happy_path_returns_top_base_wellbore(self):
        record = _make_sample(top=1872.0, base=1900.0)
        top, base, wellbore = extract_depths(record)
        assert abs(top - 1872.0) < 1e-9
        assert abs(base - 1900.0) < 1e-9
        assert wellbore == "ns:master-data--Wellbore:wb-001:"

    def test_missing_sample_top_returns_none(self):
        record = {
            "data": {
                "WellboreID": "wb-x",
                "DepthMeasurement": {
                    "VerticalMeasurements": [
                        {
                            "VerticalMeasurementTypeID": "SampleBase",
                            "VerticalMeasurementValue": 1900.0,
                            "VerticalMeasurementSourceID": "Driller",
                        },
                    ],
                },
            },
        }
        top, base, _ = extract_depths(record)
        assert top is None
        assert abs(base - 1900.0) < 1e-9

    def test_bare_string_type_ids_accepted(self):
        record = {
            "data": {
                "DepthMeasurement": {
                    "VerticalMeasurements": [
                        {
                            "VerticalMeasurementTypeID": "SampleTop",
                            "VerticalMeasurementValue": 100.0,
                            "VerticalMeasurementSourceID": "Driller",
                        },
                    ],
                },
            },
        }
        top, base, wellbore = extract_depths(record)
        assert abs(top - 100.0) < 1e-9
        assert base is None
        assert wellbore is None

    def test_no_depth_measurement_returns_none_tuple(self):
        record = {"data": {"WellboreID": "wb-x"}}
        top, base, wellbore = extract_depths(record)
        assert top is None
        assert base is None
        assert wellbore == "wb-x"

    def test_empty_record_returns_none_tuple(self):
        top, base, wellbore = extract_depths({})
        assert top is None
        assert base is None
        assert wellbore is None

    def test_point_measurement_no_base(self):
        record = {
            "data": {
                "DepthMeasurement": {
                    "VerticalMeasurements": [
                        {
                            "VerticalMeasurementTypeID": "SampleTop",
                            "VerticalMeasurementValue": 555.0,
                        },
                    ],
                },
            },
        }
        top, base, _ = extract_depths(record)
        assert abs(top - 555.0) < 1e-9
        assert base is None


class TestValidateMeasurementSource:
    def test_driller_returns_none(self):
        entry = {
            "VerticalMeasurementSourceID": "osdu:reference-data--VerticalMeasurementSource:Driller:",
        }
        assert validate_measurement_source(entry) is None

    def test_wireline_returns_warning(self):
        entry = {
            "VerticalMeasurementSourceID": "osdu:reference-data--VerticalMeasurementSource:Wireline:",
        }
        result = validate_measurement_source(entry)
        assert result is not None
        assert "Wireline" in result

    def test_missing_source_returns_warning(self):
        entry = {}
        result = validate_measurement_source(entry)
        assert result is not None

    def test_bare_driller_string_returns_none(self):
        entry = {"VerticalMeasurementSourceID": "Driller"}
        assert validate_measurement_source(entry) is None


class TestValidateWellboreMatch:
    def test_matching_wellbores_returns_none(self):
        result = validate_wellbore_match("ns:wb:001:", "ns:wb:001:")
        assert result is None

    def test_mismatched_wellbores_returns_warning(self):
        result = validate_wellbore_match("ns:wb:001:", "ns:wb:002:")
        assert result is not None
        assert "ns:wb:001:" in result
        assert "ns:wb:002:" in result

    def test_none_sample_wellbore_returns_none(self):
        result = validate_wellbore_match(None, "ns:wb:001:")
        assert result is None

    def test_none_shift_wellbore_returns_none(self):
        result = validate_wellbore_match("ns:wb:001:", None)
        assert result is None

    def test_both_none_returns_none(self):
        result = validate_wellbore_match(None, None)
        assert result is None


class TestValidateDepthShiftUom:
    def test_placeholder_always_returns_none(self):
        """UoM validation placeholder must return None regardless of inputs."""
        from app.depth_shift.extractor import validate_depth_shift_uom

        result = validate_depth_shift_uom(  # pylint: disable=assignment-from-none
            shift_meta=[{"DepthUnit": "ft"}],
            sample_record={"data": {"WellboreID": "wb-x"}},
        )
        assert result is None

    def test_placeholder_returns_none_with_empty_meta(self):
        from app.depth_shift.extractor import validate_depth_shift_uom

        result = validate_depth_shift_uom(shift_meta=[], sample_record={})  # pylint: disable=assignment-from-none
        assert result is None
