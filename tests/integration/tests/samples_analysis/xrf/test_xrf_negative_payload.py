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

import pytest
from starlette import status

from tests.integration.config import (
    CONFIG,
    DataFiles,
    SamplesAnalysisTypes,
    SchemaVersions,
)

DATA_PARTITION_ID = CONFIG["DATA_PARTITION"]


GENERIC_MANDATORY_DATA_FIELDS = [
    "/columns",
    "/index",
    "/data",
]

SPECIFIC_MANDATORY_DATA_MAIN_COLUMNS = [
    ("/columns/0", "/data/0/0"),
    ("/columns/1", "/data/0/1"),
    ("/columns/2", "/data/0/2"),
]

SPECIFIC_INVALID_TYPE_DATA_V1_1_FIELDS = [
    ("/data/0/3", "ElementalComposition"),
    ("/data/0/4", "OxideComposition"),
    ("/data/0/4/0/OxideID", ["OxideID"]),
    ("/data/0/4/0/Content", "OxideComposition.Content"),
    ("/data/0/5", ["XRFSourceTypeID"]),
    ("/data/0/7", "IsEnergyDispersiveXRF"),
    ("/data/0/9", "MassBalance"),
]

SPECIFIC_MISSING_REFERENCE_DATA_V1_1_FIELDS = [
    ("/data/0/0", f"{DATA_PARTITION_ID}:work-product-component--SamplesAnalysis:Dummy:"),
    ("/data/0/1", f"{DATA_PARTITION_ID}:master-data--Sample:DummySample:"),
    ("/data/0/2/0/unitOfMeasureID", f"{DATA_PARTITION_ID}:reference-data--UnitOfMeasure:DummyUnit:"),
    ("/data/0/3/0/ElementID", f"{DATA_PARTITION_ID}:reference-data--Elements:DummyElement:"),
    ("/data/0/4/0/OxideID", f"{DATA_PARTITION_ID}:reference-data--Oxides:DummyOxide:"),
    ("/data/0/5", f"{DATA_PARTITION_ID}:reference-data--XRFSourceType:DummySource:"),
    ("/data/0/6", f"{DATA_PARTITION_ID}:reference-data--XRFTubeType:DummyTube:"),
    ("/data/0/8", f"{DATA_PARTITION_ID}:reference-data--XRFInstrumentType:DummyInstrument:"),
]

SPECIFIC_INVALID_REGEX_DATA_V1_1_FIELDS = [
    ("/data/0/0", f"{DATA_PARTITION_ID}:work-product-component-SamplesAnalysis:Dummy:"),
    ("/data/0/1", f"{DATA_PARTITION_ID}:master-data-Sample:DummySample:"),
    ("/data/0/2/0/unitOfMeasureID", f"{DATA_PARTITION_ID}:reference-data-UnitOfMeasure:DummyUnit:"),
    ("/data/0/3/0/ElementID", f"{DATA_PARTITION_ID}:reference-data-Elements:DummyElement:"),
    ("/data/0/4/0/OxideID", f"{DATA_PARTITION_ID}:reference-data-Oxides:DummyOxide:"),
    ("/data/0/5", f"{DATA_PARTITION_ID}:reference-data-XRFSourceType:DummySource:"),
    ("/data/0/6", f"{DATA_PARTITION_ID}:reference-data-XRFTubeType:DummyTube:"),
    ("/data/0/8", f"{DATA_PARTITION_ID}:reference-data-XRFInstrumentType:DummyInstrument:"),
]

EXTRA_DATA_V1_1_FIELDS = [
    ("/data/0/2/0/ExtraMetaField", "ExtraMetaValue"),
    ("/data/0/3/0/ExtraElementalField", "ExtraElementalValue"),
    ("/data/0/4/0/ExtraOxideField", "ExtraOxideValue"),
]


@pytest.mark.parametrize("field_path", GENERIC_MANDATORY_DATA_FIELDS)
def test_xrf_negative_add_data_v1_1_missing_mandatory_generic_field(api, tests_data, helper, field_path, record_id):
    """Reject data upload with missing mandatory structure field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.XRF_DATA_V1_1))
    data_payload["data"][0][0] = f"{record_id}:"
    helper.delete_by_path(data_payload, field_path)
    field_name = field_path.split("/")[-1]

    response = api.sample_analysis.post_data(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.XRF,
        schema_version=SchemaVersions.V1_1_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert f"Data error: missing required fields: '{field_name}'." in body["reason"]


@pytest.mark.parametrize("main_column,main_column_value", SPECIFIC_MANDATORY_DATA_MAIN_COLUMNS)
def test_xrf_negative_add_data_v1_1_missing_main_mandatory_column(
    api, tests_data, helper, main_column, main_column_value, record_id
):
    """Reject data upload with missing main column with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.XRF_DATA_V1_1))
    data_payload["data"][0][0] = f"{record_id}:"
    helper.delete_by_path(data_payload, main_column)
    helper.delete_by_path(data_payload, main_column_value)

    response = api.sample_analysis.post_data(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.XRF,
        schema_version=SchemaVersions.V1_1_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


@pytest.mark.parametrize("field_path,value", SPECIFIC_INVALID_TYPE_DATA_V1_1_FIELDS)
def test_xrf_negative_add_data_v1_1_invalid_type_specific_field(api, tests_data, helper, field_path, value, record_id):
    """Reject data upload with wrong type for specific field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.XRF_DATA_V1_1))
    data_payload["data"][0][0] = f"{record_id}:"
    helper.set_by_path(data_payload, field_path, value)

    response = api.sample_analysis.post_data(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.XRF,
        schema_version=SchemaVersions.V1_1_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


@pytest.mark.parametrize("field_path,value", SPECIFIC_MISSING_REFERENCE_DATA_V1_1_FIELDS)
def test_xrf_negative_add_data_v1_1_missing_reference_specific_field(
    api, tests_data, helper, field_path, value, record_id
):
    """Reject data upload when referenced record doesn't exist with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.XRF_DATA_V1_1))
    data_payload["data"][0][0] = f"{record_id}:"
    helper.set_by_path(data_payload, field_path, value)
    record_value = value.rsplit(":", 1)[0]

    response = api.sample_analysis.post_data(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.XRF,
        schema_version=SchemaVersions.V1_1_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert record_value in body["errors"]["Missing records in storage"]


@pytest.mark.parametrize("field_path,value", SPECIFIC_INVALID_REGEX_DATA_V1_1_FIELDS)
def test_xrf_negative_add_data_v1_1_invalid_regex_specific_field(api, tests_data, helper, field_path, value, record_id):
    """Reject data upload when field doesn't match OSDU naming convention with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.XRF_DATA_V1_1))
    data_payload["data"][0][0] = f"{record_id}:"
    helper.set_by_path(data_payload, field_path, value)

    response = api.sample_analysis.post_data(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.XRF,
        schema_version=SchemaVersions.V1_1_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


def test_xrf_negative_add_data_v1_1_extra_main_field(api, tests_data, record_id):
    """Reject data upload with unexpected/extra fields with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.XRF_DATA_V1_1))
    data_payload["columns"].append("ExtraColumn")
    data_payload["data"][0].append("ExtraColumnValue")

    response = api.sample_analysis.post_data(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.XRF,
        schema_version=SchemaVersions.V1_1_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


def test_xrf_negative_add_data_v1_1_extra_main_nullable_field(api, tests_data, record_id):
    """Reject data upload with unexpected/extra main field with null value with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.XRF_DATA_V1_1))
    data_payload["columns"].append("ExtraColumn")
    data_payload["data"][0].append(None)

    response = api.sample_analysis.post_data(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.XRF,
        schema_version=SchemaVersions.V1_1_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


@pytest.mark.parametrize("field_path,value", EXTRA_DATA_V1_1_FIELDS)
def test_xrf_negative_add_data_v1_1_extra_field(api, tests_data, helper, field_path, value, record_id):
    """Reject data upload with unexpected/extra fields with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.XRF_DATA_V1_1))
    data_payload["data"][0][0] = f"{record_id}:"
    helper.set_by_path(data_payload, field_path, value)

    response = api.sample_analysis.post_data(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.XRF,
        schema_version=SchemaVersions.V1_1_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


def test_xrf_negative_add_data_v1_1_invalid_payload_format(api, tests_data, record_id):
    """Reject data upload when payload is wrapped in array with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.XRF_DATA_V1_1))
    data_payload["data"][0][0] = f"{record_id}:"

    response = api.sample_analysis.post_data(
        record_id=record_id,
        body=[data_payload],
        analysis_type=SamplesAnalysisTypes.XRF,
        schema_version=SchemaVersions.V1_1_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert (
        "Data error: split format must be a JSON object, not wrapped in an array. Remove the outer [] brackets."
        in body["reason"]
    )

def test_xrf_negative_add_data_v1_1_record_id_mismatch_between_payload_and_url(
    api, tests_data, record_id, fresh_record_id
):
    """Reject data upload with record_id different in bulk data and URL with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.XRF_DATA_V1_1))
    data_payload["data"][0][0] = f"{fresh_record_id}:"

    response = api.sample_analysis.post_data(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.XRF,
        schema_version=SchemaVersions.V1_1_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert body["errors"]["Invalid value"][0]["SamplesAnalysisID"] == f"{fresh_record_id}:"
