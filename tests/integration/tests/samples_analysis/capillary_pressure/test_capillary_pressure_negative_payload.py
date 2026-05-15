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

SPECIFIC_MANDATORY_DATA_V1_1_FIELDS = [
    "/data/0/21/Pressure",
    "/data/0/21/Temperature",
]

SPECIFIC_INVALID_TYPE_DATA_V1_1_FIELDS = [
    ("/data/0/3", ["SaturationProcessMethodID"]),
    ("/data/0/4", ["DesaturationMethodID"]),
    ("/data/0/8/0/Value", "ReferencePermeability.Value"),
    ("/data/0/8/0/PermeabilityMeasurementTypeID", ["PermeabilityMeasurementTypeID"]),
    ("/data/0/15", "GasDensity"),
    ("/data/0/22/TestData/0/CalculatedProperties", "ForcedImbibition.TestData.CalculatedProperties"),
    ("/data/0/22/TestData/0/TransientData", "ForcedImbibition.TestData.TransientData"),
]

SPECIFIC_MISSING_REFERENCE_DATA_V1_1_FIELDS = [
    ("/data/0/0", f"{DATA_PARTITION_ID}:work-product-component--SamplesAnalysis:Dummy:"),
    ("/data/0/1", f"{DATA_PARTITION_ID}:master-data--Sample:DummySample:"),
    ("/data/0/2/0/unitOfMeasureID", f"{DATA_PARTITION_ID}:reference-data--UnitOfMeasure:DummyUnit:"),
    ("/data/0/3", f"{DATA_PARTITION_ID}:reference-data--SaturationProcessMethod:Dummy:"),
    ("/data/0/4", f"{DATA_PARTITION_ID}:reference-data--DesaturationMethod:Dummy:"),
    ("/data/0/7", f"{DATA_PARTITION_ID}:reference-data--FluidSystemAnalysisType:Dummy:"),
    (
        "/data/0/8/0/PermeabilityMeasurementTypeID",
        f"{DATA_PARTITION_ID}:reference-data--PermeabilityMeasurementType:Dummy:",
    ),
    ("/data/0/18", f"{DATA_PARTITION_ID}:reference-data--DisplacedFluidType:Dummy:"),
    ("/data/0/19", f"{DATA_PARTITION_ID}:reference-data--SampleInjectionFluidType:Dummy:"),
    ("/data/0/20", f"{DATA_PARTITION_ID}:reference-data--SampleInjectionFluidType:Dummy:"),
    (
        "/data/0/22/InjectionFluidID",
        f"{DATA_PARTITION_ID}:reference-data--SampleInjectionFluidType:Dummy:",
    ),
    (
        "/data/0/22/WOGnCycleNotationID",
        f"{DATA_PARTITION_ID}:reference-data--WOGnCycleNotation:Dummy:",
    ),
    (
        "/data/0/22/TestData/0/Pressure/PressureMeasurementTypeID",
        f"{DATA_PARTITION_ID}:reference-data--PressureMeasurementType:Dummy:",
    ),
    (
        "/data/0/22/TestData/0/CalculatedProperties/EndFaceEstimationMethodID",
        f"{DATA_PARTITION_ID}:reference-data--EndFaceEstimationMethod:Dummy:",
    ),
    (
        "/data/0/23/InjectionFluidID",
        f"{DATA_PARTITION_ID}:reference-data--SampleInjectionFluidType:Dummy:",
    ),
    (
        "/data/0/23/WOGnCycleNotationID",
        f"{DATA_PARTITION_ID}:reference-data--WOGnCycleNotation:DummyDrainage:",
    ),
    (
        "/data/0/23/TestData/0/Porosity/PorosityMeasurementTypeID",
        f"{DATA_PARTITION_ID}:reference-data--PorosityMeasurementType:Dummy:",
    ),
    (
        "/data/0/23/TestData/0/Permeability/PermeabilityMeasurementTypeID",
        f"{DATA_PARTITION_ID}:reference-data--PermeabilityMeasurementType:Dummy:",
    ),
]

SPECIFIC_INVALID_REGEX_DATA_V1_1_FIELDS = [
    ("/data/0/0", f"{DATA_PARTITION_ID}:work-product-component-SamplesAnalysis:Dummy:"),
    ("/data/0/1", f"{DATA_PARTITION_ID}:master-data-Sample:DummySample:"),
    ("/data/0/2/0/unitOfMeasureID", f"{DATA_PARTITION_ID}:reference-data-UnitOfMeasure:DummyUnit:"),
    ("/data/0/3", f"{DATA_PARTITION_ID}:reference-data-SaturationProcessMethod:Dummy:"),
    ("/data/0/4", f"{DATA_PARTITION_ID}:reference-data-DesaturationMethod:Dummy:"),
    ("/data/0/7", f"{DATA_PARTITION_ID}:reference-data-FluidSystemAnalysisType:Dummy:"),
    (
        "/data/0/8/0/PermeabilityMeasurementTypeID",
        f"{DATA_PARTITION_ID}:reference-data-PermeabilityMeasurementType:Dummy:",
    ),
    ("/data/0/18", f"{DATA_PARTITION_ID}:reference-data-DisplacedFluidType:Dummy:"),
    ("/data/0/19", f"{DATA_PARTITION_ID}:reference-data-SampleInjectionFluidType:Dummy:"),
    ("/data/0/20", f"{DATA_PARTITION_ID}:reference-data-SampleInjectionFluidType:Dummy:"),
    (
        "/data/0/22/InjectionFluidID",
        f"{DATA_PARTITION_ID}:reference-data-SampleInjectionFluidType:Dummy:",
    ),
    (
        "/data/0/22/WOGnCycleNotationID",
        f"{DATA_PARTITION_ID}:reference-data-WOGnCycleNotation:Dummy:",
    ),
    (
        "/data/0/22/TestData/0/Pressure/PressureMeasurementTypeID",
        f"{DATA_PARTITION_ID}:reference-data-PressureMeasurementType:Dummy:",
    ),
    (
        "/data/0/22/TestData/0/CalculatedProperties/EndFaceEstimationMethodID",
        f"{DATA_PARTITION_ID}:reference-data-EndFaceEstimationMethod:Dummy:",
    ),
    (
        "/data/0/23/InjectionFluidID",
        f"{DATA_PARTITION_ID}:reference-data-SampleInjectionFluidType:Dummy:",
    ),
    (
        "/data/0/23/WOGnCycleNotationID",
        f"{DATA_PARTITION_ID}:reference-data-WOGnCycleNotation:DummyDrainage:",
    ),
    (
        "/data/0/23/TestData/0/Porosity/PorosityMeasurementTypeID",
        f"{DATA_PARTITION_ID}:reference-data-PorosityMeasurementType:Dummy:",
    ),
    (
        "/data/0/23/TestData/0/Permeability/PermeabilityMeasurementTypeID",
        f"{DATA_PARTITION_ID}:reference-data-PermeabilityMeasurementType:Dummy:",
    ),
]

EXTRA_DATA_V1_1_FIELDS = [
    ("/data/0/2/0/ExtraMetaField", "ExtraMetaValue"),
    ("/data/0/8/0/ExtraReferencePermField", "ExtraReferencePermValue"),
    ("/data/0/22/ExtraForcedImbibitionField", "ExtraForcedImbibitionValue"),
    ("/data/0/22/Endpoints/ExtraImbibitionEndpointField", "ExtraImbibitionEndpointValue"),
    ("/data/0/22/TestData/0/ExtraForcedImbibitionTestField", "ExtraForcedImbibitionTestValue"),
    ("/data/0/22/TestData/0/Pressure/ExtraPressureField", "ExtraPressureValue"),
    ("/data/0/22/TestData/0/CalculatedProperties/ExtraCalcPropField", "ExtraCalcPropValue"),
    ("/data/0/22/TestData/0/TransientData/0/ExtraTransientField", "ExtraTransientValue"),
    ("/data/0/22/TestData/0/Remarks/ExtraRemarkField", "ExtraRemarkValue"),
    ("/data/0/23/ExtraForcedDrainageField", "ExtraForcedDrainageValue"),
    ("/data/0/23/Endpoints/ExtraDrainageEndpointField", "ExtraDrainageEndpointValue"),
    ("/data/0/23/TestData/0/ExtraForcedDrainageTestField", "ExtraForcedDrainageTestValue"),
    ("/data/0/23/TestData/0/Porosity/ExtraPorosityField", "ExtraPorosityValue"),
    ("/data/0/23/TestData/0/Permeability/ExtraPermeabilityField", "ExtraPermeabilityValue"),
    ("/data/0/23/TestData/0/CalculatedProperties/ExtraCalcPropField", "ExtraDrainageCalcPropValue"),
    ("/data/0/23/TestData/0/TransientData/0/ExtraTransientField", "ExtraDrainageTransientValue"),
]


@pytest.mark.parametrize("field_path", GENERIC_MANDATORY_DATA_FIELDS)
def test_capillary_pressure_negative_add_data_v1_1_missing_mandatory_generic_field(
    api, tests_data, helper, field_path, record_id
):
    """Reject data upload with missing mandatory structure field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.CAPILLARY_PRESSURE_DATA_V1_1))
    data_payload["data"][0][0] = f"{record_id}:"
    helper.delete_by_path(data_payload, field_path)
    field_name = field_path.split("/")[-1]

    response = api.sample_analysis.post_measurements(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.CAPILLARY_PRESSURE,
        schema_version=SchemaVersions.V1_1_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert f"Data error: missing required fields: '{field_name}'." in body["reason"]


@pytest.mark.parametrize("main_column,main_column_value", SPECIFIC_MANDATORY_DATA_MAIN_COLUMNS)
def test_capillary_pressure_negative_add_data_v1_1_missing_main_mandatory_column(
    api, tests_data, helper, main_column, main_column_value, record_id
):
    """Reject data upload with missing main column with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.CAPILLARY_PRESSURE_DATA_V1_1))
    data_payload["data"][0][0] = f"{record_id}:"
    helper.delete_by_path(data_payload, main_column)
    helper.delete_by_path(data_payload, main_column_value)

    response = api.sample_analysis.post_measurements(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.CAPILLARY_PRESSURE,
        schema_version=SchemaVersions.V1_1_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


@pytest.mark.parametrize("field_path", SPECIFIC_MANDATORY_DATA_V1_1_FIELDS)
def test_capillary_pressure_negative_add_data_missing_specific_mandatory_field(
    api, tests_data, helper, field_path, record_id
):
    """Reject data upload with missing nested field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.CAPILLARY_PRESSURE_DATA_V1_1))
    helper.delete_by_path(data_payload, field_path)

    response = api.sample_analysis.post_measurements(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.CAPILLARY_PRESSURE,
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
def test_capillary_pressure_negative_add_data_v1_1_invalid_type_specific_field(
    api, tests_data, helper, field_path, value, record_id
):
    """Reject data upload with wrong type for specific field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.CAPILLARY_PRESSURE_DATA_V1_1))
    data_payload["data"][0][0] = f"{record_id}:"
    helper.set_by_path(data_payload, field_path, value)

    response = api.sample_analysis.post_measurements(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.CAPILLARY_PRESSURE,
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
def test_capillary_pressure_negative_add_data_v1_1_missing_reference_specific_field(
    api, tests_data, helper, field_path, value, record_id
):
    """Reject data upload when referenced record doesn't exist with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.CAPILLARY_PRESSURE_DATA_V1_1))
    data_payload["data"][0][0] = f"{record_id}:"
    helper.set_by_path(data_payload, field_path, value)
    record_value = value.rsplit(":", 1)[0]

    response = api.sample_analysis.post_measurements(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.CAPILLARY_PRESSURE,
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
def test_capillary_pressure_negative_add_data_v1_1_invalid_regex_specific_field(
    api, tests_data, helper, field_path, value, record_id
):
    """Reject data upload when field doesn't match OSDU naming convention with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.CAPILLARY_PRESSURE_DATA_V1_1))
    data_payload["data"][0][0] = f"{record_id}:"
    helper.set_by_path(data_payload, field_path, value)

    response = api.sample_analysis.post_measurements(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.CAPILLARY_PRESSURE,
        schema_version=SchemaVersions.V1_1_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


def test_capillary_pressure_negative_add_data_v1_1_extra_main_field(api, tests_data, record_id):
    """Reject data upload with unexpected/extra fields with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.CAPILLARY_PRESSURE_DATA_V1_1))
    data_payload["columns"].append("ExtraColumn")
    data_payload["data"][0].append("ExtraColumnValue")

    response = api.sample_analysis.post_measurements(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.CAPILLARY_PRESSURE,
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
def test_capillary_pressure_negative_add_data_v1_1_extra_field(api, tests_data, helper, field_path, value, record_id):
    """Reject data upload with unexpected/extra fields with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.CAPILLARY_PRESSURE_DATA_V1_1))
    data_payload["data"][0][0] = f"{record_id}:"
    helper.set_by_path(data_payload, field_path, value)

    response = api.sample_analysis.post_measurements(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.CAPILLARY_PRESSURE,
        schema_version=SchemaVersions.V1_1_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


def test_capillary_pressure_negative_add_data_v1_1_invalid_payload_format(api, tests_data, record_id):
    """Reject data upload when payload is wrapped in array with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.CAPILLARY_PRESSURE_DATA_V1_1))
    data_payload["data"][0][0] = f"{record_id}:"

    response = api.sample_analysis.post_measurements(
        record_id=record_id,
        body=[data_payload],
        analysis_type=SamplesAnalysisTypes.CAPILLARY_PRESSURE,
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
