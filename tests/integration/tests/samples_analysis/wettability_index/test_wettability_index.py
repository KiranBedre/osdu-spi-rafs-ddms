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

import pandas as pd
from starlette import status

from app.resources.common_headers import CONTENT_TYPE
from client.api.core.v2.sample_analysis import SamplesAnalysisPaths
from tests.integration.config import DataFiles, SamplesAnalysisTypes, SchemaVersions


EXPECTED_V2_COLUMNS = {
    "SamplesAnalysisID",
    "SampleID",
    "Meta",
    "Temperature",
    "WettabilityIndex",
    "ConfiningPressure",
    "DesaturationMethod",
    "FluidSystem",
    "InitialWaterSaturation",
    "Remarks",
    "TestSteps",
}

EXPECTED_TEST_STEP_FIELDS = {
    "SequenceNumber",
    "CapillaryPressureAnalysisID",
    "SaturationProcessMethodID",
    "InjectionFluidID",
    "DisplacedFluidID",
    "EndPoints",
    "TotalProducedVolume",
}


def _prepare_payload(payload, record_id):
    columns = payload["columns"]
    row = payload["data"][0]
    row[columns.index("SamplesAnalysisID")] = f"{record_id}:"

    if "WettabilityIndexData" in columns:
        row[columns.index("WettabilityIndexData")]["CapillaryPressureAnalysisID"] = f"{record_id}:"
    else:
        row[columns.index("TestSteps")][0]["CapillaryPressureAnalysisID"] = f"{record_id}:"

    return payload


def _assert_v2_round_trip(actual, expected):
    assert set(actual["columns"]) == EXPECTED_V2_COLUMNS
    assert len(actual["data"]) == 1

    actual_row = dict(zip(actual["columns"], actual["data"][0]))
    expected_row = dict(zip(expected["columns"], expected["data"][0]))

    for field in (
        "SamplesAnalysisID",
        "SampleID",
        "Temperature",
        "ConfiningPressure",
        "DesaturationMethod",
        "FluidSystem",
        "InitialWaterSaturation",
    ):
        assert actual_row[field] == expected_row[field]

    assert actual_row["Meta"][0]["propertyNames"] == ["Temperature"]
    assert actual_row["WettabilityIndex"][0] == expected_row["WettabilityIndex"][0]
    assert actual_row["Remarks"][0]["Remark"] == expected_row["Remarks"][0]["Remark"]

    actual_step = actual_row["TestSteps"][0]
    expected_step = expected_row["TestSteps"][0]
    assert set(actual_step) == EXPECTED_TEST_STEP_FIELDS
    for field in EXPECTED_TEST_STEP_FIELDS - {"EndPoints"}:
        assert actual_step[field] == expected_step[field]

    for field, expected_value in expected_step["EndPoints"].items():
        assert actual_step["EndPoints"][field] == expected_value


def test_wettability_index_schema_v2(api):
    """Return the Wettability Index 2.0.0 root and TestSteps schema."""
    response = api.sample_analysis.get_schema(
        SamplesAnalysisTypes.WETTABILITY_INDEX,
        SchemaVersions.V2_0_0,
        raw=True,
    )

    assert response.status_code == status.HTTP_200_OK
    schema = response.json()
    assert set(schema["properties"]) == EXPECTED_V2_COLUMNS

    test_steps_array = next(
        option for option in schema["properties"]["TestSteps"]["anyOf"] if option.get("type") == "array"
    )
    test_step_name = test_steps_array["items"]["$ref"].rsplit("/", 1)[-1]
    test_step_properties = schema["$defs"][test_step_name]["properties"]
    assert set(test_step_properties) == EXPECTED_TEST_STEP_FIELDS

    for field in ("InjectionFluidID", "DisplacedFluidID"):
        string_schema = next(
            option for option in test_step_properties[field]["anyOf"] if option.get("type") == "string"
        )
        assert "CoreAnalysisFluidType" in string_schema["pattern"]


def test_wettability_index_v1_remains_readable(api, helper, tests_data, record_id):
    """Keep the legacy 1.0.0 schema and WettabilityIndexData payload readable."""
    schema_response = api.sample_analysis.get_schema(
        SamplesAnalysisTypes.WETTABILITY_INDEX,
        SchemaVersions.V1_0_0,
        raw=True,
    )
    assert schema_response.status_code == status.HTTP_200_OK

    payload = _prepare_payload(
        copy.deepcopy(tests_data(DataFiles.WETTABILITY_INDEX_DATA_V1)),
        record_id,
    )
    post_response = api.sample_analysis.post_data(
        record_id=record_id,
        body=payload,
        analysis_type=SamplesAnalysisTypes.WETTABILITY_INDEX,
        schema_version=SchemaVersions.V1_0_0,
    )
    assert post_response.get("ddms_urn")

    dataset_id = helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])
    gotten_data = api.sample_analysis.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        analysis_type=SamplesAnalysisTypes.WETTABILITY_INDEX,
        schema_version=SchemaVersions.V1_0_0,
    )

    assert set(gotten_data["columns"]) == {
        "SamplesAnalysisID",
        "SampleID",
        "Meta",
        "WettabilityIndexData",
    }
    gotten_row = dict(zip(gotten_data["columns"], gotten_data["data"][0]))
    expected_row = dict(zip(payload["columns"], payload["data"][0]))
    assert gotten_row["SamplesAnalysisID"] == expected_row["SamplesAnalysisID"]
    assert gotten_row["SampleID"] == expected_row["SampleID"]
    assert gotten_row["WettabilityIndexData"]["Temperature"] == 185.0
    assert gotten_row["WettabilityIndexData"]["WettabilityIndex"][0]["Value"] == 0.45


def test_wettability_index_json_v2_round_trip(api, helper, tests_data, record_id):
    """Store and retrieve the relevant Wettability Index 2.0.0 JSON data."""
    payload = _prepare_payload(
        copy.deepcopy(tests_data(DataFiles.WETTABILITY_INDEX_DATA_V2)),
        record_id,
    )
    post_response = api.sample_analysis.post_data(
        record_id=record_id,
        body=payload,
        analysis_type=SamplesAnalysisTypes.WETTABILITY_INDEX,
        schema_version=SchemaVersions.V2_0_0,
    )
    assert post_response.get("ddms_urn")

    dataset_id = helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])
    gotten_data = api.sample_analysis.get_data(
        record_id=record_id,
        dataset_id=dataset_id,
        analysis_type=SamplesAnalysisTypes.WETTABILITY_INDEX,
        schema_version=SchemaVersions.V2_0_0,
    )
    _assert_v2_round_trip(gotten_data, payload)


def test_wettability_index_v2_rejects_missing_test_step_sequence_number(api, tests_data, record_id):
    """Reject Wettability Index 2.0.0 data when TestSteps SequenceNumber is missing."""
    payload = _prepare_payload(
        copy.deepcopy(tests_data(DataFiles.WETTABILITY_INDEX_DATA_V2)),
        record_id,
    )
    test_steps = payload["data"][0][payload["columns"].index("TestSteps")]
    test_steps[0].pop("SequenceNumber")

    response = api.sample_analysis.post_data(
        record_id=record_id,
        body=payload,
        analysis_type=SamplesAnalysisTypes.WETTABILITY_INDEX,
        schema_version=SchemaVersions.V2_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["reason"] == "Data validation failed."


def test_wettability_index_v2_rejects_null_test_step_sequence_number(api, tests_data, record_id):
    """Reject Wettability Index 2.0.0 data when TestSteps SequenceNumber is null."""
    payload = _prepare_payload(
        copy.deepcopy(tests_data(DataFiles.WETTABILITY_INDEX_DATA_V2)),
        record_id,
    )
    test_steps = payload["data"][0][payload["columns"].index("TestSteps")]
    test_steps[0]["SequenceNumber"] = None

    response = api.sample_analysis.post_data(
        record_id=record_id,
        body=payload,
        analysis_type=SamplesAnalysisTypes.WETTABILITY_INDEX,
        schema_version=SchemaVersions.V2_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["reason"] == "Data validation failed."


def test_wettability_index_parquet_v2_round_trip(api, helper, tests_data, fresh_record_id):
    """Store valid Wettability Index 2.0.0 Parquet and retrieve its data."""
    payload = _prepare_payload(
        copy.deepcopy(tests_data(DataFiles.WETTABILITY_INDEX_DATA_V2)),
        fresh_record_id,
    )
    dataframe = pd.DataFrame(
        payload["data"],
        columns=payload["columns"],
        index=payload["index"],
    )
    response = api.sample_analysis.post(
        path=SamplesAnalysisPaths.POST_DATA.format(
            record_id=fresh_record_id,
            analysis_type=SamplesAnalysisTypes.WETTABILITY_INDEX,
        ),
        data=dataframe.to_parquet(),
        params={"content_schema_version": SchemaVersions.V2_0_0},
        headers={CONTENT_TYPE: "application/x-parquet"},
    )
    post_response = response.json()
    assert post_response.get("ddms_urn")

    dataset_id = helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])
    gotten_data = api.sample_analysis.get_data(
        record_id=fresh_record_id,
        dataset_id=dataset_id,
        analysis_type=SamplesAnalysisTypes.WETTABILITY_INDEX,
        schema_version=SchemaVersions.V2_0_0,
    )
    _assert_v2_round_trip(gotten_data, payload)
