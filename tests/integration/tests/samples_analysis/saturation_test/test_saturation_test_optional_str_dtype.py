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

import copy

from tests.integration.config import (
    DataFiles,
    SamplesAnalysisTypes,
    SchemaVersions,
)

_TEST_NUMBER_IDX = 3  # position of TestNumber in the split-format columns array


def test_optional_str_field_with_numeric_value_is_preserved_on_round_trip(
    api, helper, tests_data, record_id, cce_record_id, analysis_type
):
    """Numeric-looking values in Optional[str] columns survive a POST → GET round-trip as strings.

    TestNumber is declared as `str | None` in SaturationTestModel100.
    Without a dtype hint, pd.read_json infers the JSON string "1" as int64,
    which either causes pandera to reject the POST (422) or silently mangles
    the stored value from "1" to 1.

    The pydantic v2 migration fixes this by building a dtype map from the
    model's str-annotated fields and passing it to pd.read_json.

    This test FAILS on ci/integration (int inference, no dtype map).
    This test PASSES on feature/pydantic-v2-migration (dtype map applied).
    """
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_TEST_DATA_V1))
    data_payload["data"][0][0] = f"{record_id}:"
    data_payload["data"][0][7] = f"{cce_record_id}:"
    data_payload["data"][0][_TEST_NUMBER_IDX] = "1"  # numeric-looking str

    post_response = api.sample_analysis.post_data(
        record_id, data_payload, SamplesAnalysisTypes.SATURATION_TEST, SchemaVersions.V1_0_0
    )
    dataset_id = helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])

    gotten_data = api.sample_analysis.get_data(
        record_id, dataset_id, SamplesAnalysisTypes.SATURATION_TEST, SchemaVersions.V1_0_0
    )

    test_number_idx = gotten_data["columns"].index("TestNumber")
    actual = gotten_data["data"][0][test_number_idx]
    assert actual == "1", (
        f"TestNumber must round-trip as string '1', got {actual!r} ({type(actual).__name__}). "
        "This indicates pd.read_json inferred int64 for a str|None column (dtype map missing)."
    )


def test_optional_str_field_accepts_purely_alphabetic_value(
    api, helper, tests_data, record_id, cce_record_id, analysis_type
):
    """Alphabetic values in Optional[str] columns are unaffected by dtype inference.

    This is the baseline: pandas never misidentifies "Test number 1" as numeric,
    so this test should pass on both ci/integration and feature/pydantic-v2-migration.
    It serves as a control to confirm the test infrastructure works correctly.
    """
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_TEST_DATA_V1))
    data_payload["data"][0][0] = f"{record_id}:"
    data_payload["data"][0][7] = f"{cce_record_id}:"
    data_payload["data"][0][_TEST_NUMBER_IDX] = "Test number 99"

    post_response = api.sample_analysis.post_data(
        record_id, data_payload, SamplesAnalysisTypes.SATURATION_TEST, SchemaVersions.V1_0_0
    )
    dataset_id = helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])

    gotten_data = api.sample_analysis.get_data(
        record_id, dataset_id, SamplesAnalysisTypes.SATURATION_TEST, SchemaVersions.V1_0_0
    )

    test_number_idx = gotten_data["columns"].index("TestNumber")
    assert gotten_data["data"][0][test_number_idx] == "Test number 99"
