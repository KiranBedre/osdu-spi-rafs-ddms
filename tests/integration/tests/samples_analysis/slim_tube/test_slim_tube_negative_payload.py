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

SPECIFIC_INVALID_TYPE_DATA_V2_FIELDS = [
    ("/data/0/5", "Remarks"),
    ("/data/0/4", "TestTemperature"),
    ("/data/0/7", ["InjectedGasID"]),
    (
        "/data/0/11/0/SlimTubeTestVolumeSteps/0/CumulativeVaporCompositionalAnalysis",
        "CumulativeVaporCompositionalAnalysis",
    ),
    (
        "/data/0/11/0/SlimTubeTestVolumeSteps/0/CumulativeLiquidCompositionalAnalysis/0/LiquidComposition",
        "CumulativeLiquidCompositionalAnalysis.LiquidComposition",
    ),
]

SPECIFIC_MISSING_REFERENCE_DATA_V2_FIELDS = [
    ("/data/0/0", f"{DATA_PARTITION_ID}:work-product-component--SamplesAnalysis:Dummy:"),
    ("/data/0/1", f"{DATA_PARTITION_ID}:master-data--Sample:DummySample:"),
    ("/data/0/2/0/unitOfMeasureID", f"{DATA_PARTITION_ID}:reference-data--UnitOfMeasure:DummyUnit:"),
    (
        "/data/0/6/0/ColumnPermeabilityMeasurementMethodID",
        f"{DATA_PARTITION_ID}:reference-data--PermeabilityMeasurementMethod:Dummy:",
    ),
    (
        "/data/0/6/0/ColumnPermeabilityFluidTypeID",
        f"{DATA_PARTITION_ID}:reference-data--SampleInjectionFluidType:DummyFluid:",
    ),
    ("/data/0/7", f"{DATA_PARTITION_ID}:master-data--Sample:DummyGasInjected:"),
    (
        "/data/0/8/0/VaporComposition/0/ComponentNameID",
        f"{DATA_PARTITION_ID}:reference-data--SampleOrganicCompositionComponent:DummyComponent:",
    ),
    (
        "/data/0/10/0/ResidueCalculatedProperties/0/ComponentNameID",
        f"{DATA_PARTITION_ID}:reference-data--SampleOrganicCompositionComponent:DummyComponent:",
    ),
    (
        "/data/0/11/0/SlimTubeTestVolumeSteps/0/CumulativeLiquidCompositionalAnalysis/0/LiquidComposition/0/ComponentNameID",
        f"{DATA_PARTITION_ID}:reference-data--SampleOrganicCompositionComponent:DummyComponent:",
    ),
    (
        "/data/0/11/0/SlimTubeTestVolumeSteps/0/IncrementalLiquidCompositionalAnalysis/0/LiquidComposition/0/ComponentNameID",
        f"{DATA_PARTITION_ID}:reference-data--SampleOrganicCompositionComponent:DummyComponent:",
    ),
    (
        "/data/0/11/0/SlimTubeTestVolumeSteps/0/InstantaneousLiquidCompositionalAnalysis/0/LiquidComposition/0/ComponentNameID",
        f"{DATA_PARTITION_ID}:reference-data--SampleOrganicCompositionComponent:DummyComponent:",
    ),
]

SPECIFIC_INVALID_REGEX_DATA_V2_FIELDS = [
    ("/data/0/0", f"{DATA_PARTITION_ID}:work-product-component-SamplesAnalysis:Dummy:"),
    ("/data/0/1", f"{DATA_PARTITION_ID}:master-data-Sample:DummySample:"),
    ("/data/0/2/0/unitOfMeasureID", f"{DATA_PARTITION_ID}:reference-data-UnitOfMeasure:DummyUnit:"),
    (
        "/data/0/6/0/ColumnPermeabilityMeasurementMethodID",
        f"{DATA_PARTITION_ID}:reference-data-PermeabilityMeasurementMethod:Dummy:",
    ),
    (
        "/data/0/6/0/ColumnPermeabilityFluidTypeID",
        f"{DATA_PARTITION_ID}:reference-data-SampleInjectionFluidType:DummyFluid:",
    ),
    ("/data/0/7", f"{DATA_PARTITION_ID}:master-data-Sample:DummyGasInjected:"),
    (
        "/data/0/8/0/VaporComposition/0/ComponentNameID",
        f"{DATA_PARTITION_ID}:reference-data-SampleOrganicCompositionComponent:DummyComponent:",
    ),
    (
        "/data/0/10/0/ResidueCalculatedProperties/0/ComponentNameID",
        f"{DATA_PARTITION_ID}:reference-data-SampleOrganicCompositionComponent:DummyComponent:",
    ),
    (
        "/data/0/11/0/SlimTubeTestVolumeSteps/0/CumulativeLiquidCompositionalAnalysis/0/LiquidComposition/0/ComponentNameID",
        f"{DATA_PARTITION_ID}:reference-data-SampleOrganicCompositionComponent:DummyComponent:",
    ),
    (
        "/data/0/11/0/SlimTubeTestVolumeSteps/0/IncrementalLiquidCompositionalAnalysis/0/LiquidComposition/0/ComponentNameID",
        f"{DATA_PARTITION_ID}:reference-data-SampleOrganicCompositionComponent:DummyComponent:",
    ),
    (
        "/data/0/11/0/SlimTubeTestVolumeSteps/0/InstantaneousLiquidCompositionalAnalysis/0/LiquidComposition/0/ComponentNameID",
        f"{DATA_PARTITION_ID}:reference-data-SampleOrganicCompositionComponent:DummyComponent:",
    ),
]

EXTRA_DATA_V2_FIELDS = [
    ("/data/0/2/0/ExtraMetaField", "ExtraMetaValue"),
    ("/data/0/5/ExtraRemarkField", "ExtraRemarkValue"),
    ("/data/0/6/0/ExtraSlimTubeSpecField", "ExtraSlimTubeSpecValue"),
    ("/data/0/8/0/ExtraInjectedGasField", "ExtraInjectedGasValue"),
    ("/data/0/10/0/ExtraCalculatedPropertyField", "ExtraCalculatedPropertyValue"),
    ("/data/0/10/0/ResidueCalculatedProperties/0/ExtraResidueField", "ExtraResidueValue"),
    ("/data/0/11/0/ExtraSlimTubeTestStepField", "ExtraSlimTubeTestStepValue"),
    ("/data/0/11/0/SlimTubeTestVolumeSteps/0/ExtraVolumeStepField", "ExtraVolumeStepValue"),
    (
        "/data/0/11/0/SlimTubeTestVolumeSteps/0/CumulativeVaporCompositionalAnalysis/0/ExtraCumulativeVaporField",
        "ExtraCumulativeVaporValue",
    ),
    (
        "/data/0/11/0/SlimTubeTestVolumeSteps/0/CumulativeVaporCompositionalAnalysis/0/VaporComposition/0/ExtraVaporCompositionField",
        "ExtraVaporCompositionValue",
    ),
    (
        "/data/0/11/0/SlimTubeTestVolumeSteps/0/CumulativeLiquidCompositionalAnalysis/0/ExtraCumulativeLiquidField",
        "ExtraCumulativeLiquidValue",
    ),
    (
        "/data/0/11/0/SlimTubeTestVolumeSteps/0/CumulativeLiquidCompositionalAnalysis/0/LiquidComposition/0/ExtraLiquidCompositionField",
        "ExtraLiquidCompositionValue",
    ),
    ("/data/0/11/0/MaterialBalanceData/0/ExtraMaterialBalanceField", "ExtraMaterialBalanceValue"),
]


@pytest.mark.parametrize("field_path", GENERIC_MANDATORY_DATA_FIELDS)
def test_slim_tube_negative_add_data_v2_missing_mandatory_generic_field(api, tests_data, helper, field_path, record_id):
    """Reject data upload with missing mandatory structure field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SLIM_TUBE_DATA_V2))
    helper.delete_by_path(data_payload, field_path)
    field_name = field_path.split("/")[-1]

    response = api.sample_analysis.post_measurements(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.SLIM_TUBE,
        schema_version=SchemaVersions.V2_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert f"Data error: missing required fields: '{field_name}'." in body["reason"]


@pytest.mark.parametrize("main_column,main_column_value", SPECIFIC_MANDATORY_DATA_MAIN_COLUMNS)
def test_slim_tube_negative_add_data_v2_missing_main_mandatory_column(
    api, tests_data, helper, main_column, main_column_value, record_id
):
    """Reject data upload with missing main column with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SLIM_TUBE_DATA_V2))
    helper.delete_by_path(data_payload, main_column)
    helper.delete_by_path(data_payload, main_column_value)

    response = api.sample_analysis.post_measurements(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.SLIM_TUBE,
        schema_version=SchemaVersions.V2_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


@pytest.mark.parametrize("field_path,value", SPECIFIC_INVALID_TYPE_DATA_V2_FIELDS)
def test_slim_tube_negative_add_data_v2_invalid_type_specific_field(
    api, tests_data, helper, field_path, value, record_id
):
    """Reject data upload with wrong type for specific field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SLIM_TUBE_DATA_V2))
    helper.set_by_path(data_payload, field_path, value)

    response = api.sample_analysis.post_measurements(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.SLIM_TUBE,
        schema_version=SchemaVersions.V2_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


@pytest.mark.parametrize("field_path,value", SPECIFIC_MISSING_REFERENCE_DATA_V2_FIELDS)
def test_slim_tube_negative_add_data_v2_missing_reference_specific_field(
    api, tests_data, helper, field_path, value, record_id
):
    """Reject data upload when referenced record doesn't exist with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SLIM_TUBE_DATA_V2))
    helper.set_by_path(data_payload, field_path, value)
    record_value = value.rsplit(":", 1)[0]

    response = api.sample_analysis.post_measurements(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.SLIM_TUBE,
        schema_version=SchemaVersions.V2_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert record_value in body["errors"]["Missing records in storage"]


@pytest.mark.parametrize("field_path,value", SPECIFIC_INVALID_REGEX_DATA_V2_FIELDS)
def test_slim_tube_negative_add_data_v2_invalid_regex_specific_field(
    api, tests_data, helper, field_path, value, record_id
):
    """Reject data upload when field doesn't match OSDU naming convention with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SLIM_TUBE_DATA_V2))
    helper.set_by_path(data_payload, field_path, value)

    response = api.sample_analysis.post_measurements(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.SLIM_TUBE,
        schema_version=SchemaVersions.V2_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


def test_slim_tube_negative_add_data_v2_extra_main_field(api, tests_data, record_id):
    """Reject data upload with unexpected/extra fields with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SLIM_TUBE_DATA_V2))
    data_payload["columns"].append("ExtraColumn")
    data_payload["data"][0].append("ExtraColumnValue")

    response = api.sample_analysis.post_measurements(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.SLIM_TUBE,
        schema_version=SchemaVersions.V2_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


@pytest.mark.parametrize("field_path,value", EXTRA_DATA_V2_FIELDS)
def test_slim_tube_negative_add_data_v2_extra_field(api, tests_data, helper, field_path, value, record_id):
    """Reject data upload with unexpected/extra fields with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SLIM_TUBE_DATA_V2))
    helper.set_by_path(data_payload, field_path, value)

    response = api.sample_analysis.post_measurements(
        record_id=record_id,
        body=data_payload,
        analysis_type=SamplesAnalysisTypes.SLIM_TUBE,
        schema_version=SchemaVersions.V2_0_0,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


def test_slim_tube_negative_add_data_v2_invalid_payload_format(api, tests_data, record_id):
    """Reject data upload when payload is wrapped in array with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SLIM_TUBE_DATA_V2))

    response = api.sample_analysis.post_measurements(
        record_id=record_id,
        body=[data_payload],
        analysis_type=SamplesAnalysisTypes.SLIM_TUBE,
        schema_version=SchemaVersions.V2_0_0,
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
