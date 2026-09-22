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
)

DATA_PARTITION_ID = CONFIG["DATA_PARTITION"]

GENERIC_MANDATORY_FIELDS = [
    "/kind",
    "/legal",
    "/acl",
    "/legal/legaltags",
    "/legal/otherRelevantDataCountries",
    "/acl/owners",
    "/acl/viewers",
]

GENERIC_INVALID_TYPE_FIELDS = [
    ("/id", ["id"], "id Input should be a valid string"),
    ("/kind", ["kind"], "kind Input should be a valid string"),
    ("/legal", ["legal"], "legal Input should be a valid dictionary or object to extract fields from"),
    ("/acl", ["acl"], "acl Input should be a valid dictionary or object to extract fields from"),
    ("/legal/legaltags", "legaltags", "legaltags Input should be a valid list"),
    (
        "/legal/otherRelevantDataCountries",
        "otherRelevantDataCountries",
        "otherRelevantDataCountries Input should be a valid list",
    ),
    ("/acl/owners", "owners", "owners Input should be a valid list"),
    ("/acl/viewers", "viewers", "viewers Input should be a valid list"),
    ("/data", "data", "data Input should be a valid dictionary"),
]

SPECIFIC_INVALID_TYPE_FIELDS = [
    ("/data/Name", ["Name"], "['Name'] is not of type 'string'"),
    (
        "/data/CompressibilityModelTypeID",
        ["CompressibilityModelTypeID"],
        "['CompressibilityModelTypeID'] is not of type 'string'",
    ),
    (
        "/data/ThermalModelTypeID",
        ["ThermalModelTypeID"],
        "['ThermalModelTypeID'] is not of type 'string'",
    ),
    (
        "/data/ParentModelID",
        ["ParentModelID"],
        "['ParentModelID'] is not of type 'string'",
    ),
    (
        "/data/Remarks",
        "Remarks",
        "'Remarks' is not of type 'array'",
    ),
    (
        "/data/BasisOfModelling",
        ["BasisOfModelling"],
        "['BasisOfModelling'] is not of type 'object'",
    ),
    (
        "/data/BasisOfModelling/CompressibilityModelInputSampleAnalysisIDs",
        "CompressibilityModelInputSampleAnalysisIDs",
        "'CompressibilityModelInputSampleAnalysisIDs' is not of type 'array'",
    ),
    (
        "/data/BasisOfModelling/CompressibilityModelInputDataCollectionID",
        ["CompressibilityModelInputDataCollectionID"],
        "['CompressibilityModelInputDataCollectionID'] is not of type 'string'",
    ),
    (
        "/data/BasisOfModelling/ThermalModelInputSampleAnalysisIDs",
        "ThermalModelInputSampleAnalysisIDs",
        "'ThermalModelInputSampleAnalysisIDs' is not of type 'array'",
    ),
    (
        "/data/BasisOfModelling/ThermalModelInputDataCollectionID",
        ["ThermalModelInputDataCollectionID"],
        "['ThermalModelInputDataCollectionID'] is not of type 'string'",
    ),
    (
        "/data/BasisOfModelling/ModellingApplicationsUsed",
        "ModellingApplicationsUsed",
        "'ModellingApplicationsUsed' is not of type 'array'",
    ),
    (
        "/data/BasisOfModelling/IntendedWorkflowUsageIDs",
        "IntendedWorkflowUsageIDs",
        "'IntendedWorkflowUsageIDs' is not of type 'array'",
    ),
]

SPECIFIC_MISSING_REFERENCE_FIELDS = [
    ("/data/CompressibilityModelTypeID", f"{DATA_PARTITION_ID}:reference-data--CompressibilityModelType:dummy:"),
    ("/data/ThermalModelTypeID", f"{DATA_PARTITION_ID}:reference-data--ThermalModelType:dummy:"),
    ("/data/ParentModelID", f"{DATA_PARTITION_ID}:work-product-component--ReservoirSimulationRockPhysicsModel:dummy:"),
    (
        "/data/BasisOfModelling/CompressibilityModelInputSampleAnalysisIDs/0",
        f"{DATA_PARTITION_ID}:work-product-component--SamplesAnalysis:dummy:",
    ),
    (
        "/data/BasisOfModelling/CompressibilityModelInputDataCollectionID",
        f"{DATA_PARTITION_ID}:work-product-component--PersistedCollection:dummy:",
    ),
    (
        "/data/BasisOfModelling/ThermalModelInputSampleAnalysisIDs/0",
        f"{DATA_PARTITION_ID}:work-product-component--SamplesAnalysis:dummy:",
    ),
    (
        "/data/BasisOfModelling/ThermalModelInputDataCollectionID",
        f"{DATA_PARTITION_ID}:work-product-component--PersistedCollection:dummy:",
    ),
    (
        "/data/BasisOfModelling/IntendedWorkflowUsageIDs/0",
        f"{DATA_PARTITION_ID}:reference-data--WorkflowUsageType:dummy:",
    ),
]

INVALID_REGEX_FIELDS = [
    ("/id", f"{DATA_PARTITION_ID}:work-product-component-ReservoirSimulationRockPhysicsModel:dummy"),
    ("/data/CompressibilityModelTypeID", f"{DATA_PARTITION_ID}:reference-data-CompressibilityModelType:dummy:"),
    ("/data/ThermalModelTypeID", f"{DATA_PARTITION_ID}:reference-data-ThermalModelType:dummy:"),
    ("/data/ParentModelID", f"{DATA_PARTITION_ID}:work-product-component-ReservoirSimulationRockPhysicsModel:dummy:"),
    (
        "/data/BasisOfModelling/CompressibilityModelInputSampleAnalysisIDs/0",
        f"{DATA_PARTITION_ID}:work-product-component-SamplesAnalysis:dummy:",
    ),
    (
        "/data/BasisOfModelling/CompressibilityModelInputDataCollectionID",
        f"{DATA_PARTITION_ID}:work-product-component-PersistedCollection:dummy:",
    ),
    (
        "/data/BasisOfModelling/ThermalModelInputSampleAnalysisIDs/0",
        f"{DATA_PARTITION_ID}:work-product-component-SamplesAnalysis:dummy:",
    ),
    (
        "/data/BasisOfModelling/ThermalModelInputDataCollectionID",
        f"{DATA_PARTITION_ID}:work-product-component-PersistedCollection:dummy:",
    ),
    (
        "/data/BasisOfModelling/IntendedWorkflowUsageIDs/0",
        f"{DATA_PARTITION_ID}:reference-data-WorkflowUsageType:dummy:",
    ),
]

GENERIC_EXTRA_FIELDS = [
    ("/acl/extraAcl", "extraAclValue"),
    ("/legal/extraLegal", "extraLegalValue"),
]

GENERIC_MANDATORY_DATA_FIELDS = [
    "/columns",
    "/index",
    "/data",
]

SPECIFIC_MANDATORY_DATA_MAIN_COLUMNS = [
    ("/columns/0", "/data/0/0"),
    ("/columns/2", "/data/0/2"),
]

SPECIFIC_MANDATORY_DATA1_FIELDS = [
    "/data/0/2/ReferencePressure",
    "/data/0/2/PoreVolumeCompressibilityAtReferencePressure",
    "/data/0/3/ThermalConductivity",
    "/data/0/3/HeatCapacity",
]

SPECIFIC_MANDATORY_DATA3_FIELDS = [
    "/data/0/2/Pressure",
    "/data/0/2/PoreVolumeCompressibility",
    "/data/0/2/TransmissibilityCompressibility",
    "/data/0/2/ReferencePressure",
]


SPECIFIC_INVALID_TYPE_DATA1_FIELDS = [
    ("/data/0/0", ["ReservoirSimulationRockPhysicsID"]),
    ("/data/0/1", "Meta"),
    ("/data/0/1/0/unitOfMeasureID", ["unitOfMeasureID"]),
    ("/data/0/2", "Compressibility"),
    ("/data/0/2/ReferencePressure", "ReferencePressure"),
    ("/data/0/2/PoreVolumeCompressibilityAtReferencePressure", "PoreVolumeCompressibilityAtReferencePressure"),
    ("/data/0/3", "ThermalModelDefinition"),
    ("/data/0/3/ThermalConductivity", "ThermalConductivity"),
    ("/data/0/3/HeatCapacity", "HeatCapacity"),
]

SPECIFIC_INVALID_TYPE_DATA2_FIELDS = [
    ("/data/0/2/Pressure", "Pressure"),
    ("/data/0/2/Pressure/0", "Pressure"),
    ("/data/0/2/PoreVolumeMultiplier", "PoreVolumeMultiplier"),
    ("/data/0/2/PoreVolumeMultiplier/0", "PoreVolumeMultiplier"),
    ("/data/0/2/TransmissibilityMultiplier", "TransmissibilityMultiplier"),
    ("/data/0/2/TransmissibilityMultiplier/0", "TransmissibilityMultiplier"),
]

SPECIFIC_INVALID_TYPE_DATA3_FIELDS = [
    ("/data/0/2/ReferencePressure", ["ReferencePressure"]),
    ("/data/0/2/Y-DirectionTransmissibilityCompressibility", "Y-DirectionTransmissibilityCompressibility"),
    ("/data/0/2/Y-DirectionTransmissibilityCompressibility/0", "Y-DirectionTransmissibilityCompressibility"),
    ("/data/0/2/Z-DirectionTransmissibilityCompressibility", "Z-DirectionTransmissibilityCompressibility"),
    ("/data/0/2/Z-DirectionTransmissibilityCompressibility/0", "Z-DirectionTransmissibilityCompressibility"),
]

SPECIFIC_MISSING_REFERENCE_DATA_FIELDS = [
    ("/data/0/0", f"{DATA_PARTITION_ID}:work-product-component--ReservoirSimulationRockPhysicsModel:Dummy:"),
    ("/data/0/1/0/unitOfMeasureID", f"{DATA_PARTITION_ID}:reference-data--UnitOfMeasure:Dummy:"),
]

SPECIFIC_INVALID_REGEX_DATA_FIELDS = [
    ("/data/0/0", f"{DATA_PARTITION_ID}:work-product-component-ReservoirSimulationRockPhysicsModel:Dummy:"),
    ("/data/0/1/0/unitOfMeasureID", f"{DATA_PARTITION_ID}:reference-data-UnitOfMeasure:Dummy:"),
]

EXTRA_DATA_FIELDS = [
    ("/data/0/1/0/ExtraMetaField", "ExtraMetaValue"),
    ("/data/0/2/ExtraCompressibilityField", "ExtraCompressibilityValue"),
    ("/data/0/3/ExtraThermalField", "ExtraThermalValue"),
]

SPECIFIC_MANDATORY_DATA1_FIELDS_RECORDS_FORMAT = [
    "/Compressibility/ReferencePressure",
    "/Compressibility/PoreVolumeCompressibilityAtReferencePressure",
    "/ThermalModelDefinition/ThermalConductivity",
    "/ThermalModelDefinition/HeatCapacity",
]

SPECIFIC_INVALID_TYPE_DATA_FIELDS_RECORDS_FORMAT = [
    ("/Compressibility", "Compressibility"),
    ("/Compressibility/ReferencePressure", "ReferencePressure"),
    ("/ThermalModelDefinition", "ThermalModelDefinition"),
    ("/ThermalModelDefinition/ThermalConductivity", "ThermalConductivity"),
]

SPECIFIC_MISSING_REFERENCE_DATA_FIELDS_RECORDS_FORMAT = [
    (
        "/ReservoirSimulationRockPhysicsID",
        f"{DATA_PARTITION_ID}:work-product-component--ReservoirSimulationRockPhysicsModel:Dummy:",
    ),
    ("/Meta/0/unitOfMeasureID", f"{DATA_PARTITION_ID}:reference-data--UnitOfMeasure:Dummy:"),
]

SPECIFIC_INVALID_REGEX_DATA_FIELDS_RECORDS_FORMAT = [
    (
        "/ReservoirSimulationRockPhysicsID",
        f"{DATA_PARTITION_ID}:work-product-component-ReservoirSimulationRockPhysicsModel:Dummy:",
    ),
    ("/Meta/0/unitOfMeasureID", f"{DATA_PARTITION_ID}:reference-data-UnitOfMeasure:Dummy:"),
]

EXTRA_DATA_FIELDS_RECORDS_FORMAT = [
    ("/Meta/0/ExtraMetaField", "ExtraMetaValue"),
    ("/Compressibility/ExtraCompressibilityField", "ExtraCompressibilityValue"),
    ("/ThermalModelDefinition/ExtraThermalField", "ExtraThermalValue"),
]


@pytest.mark.parametrize("field_path", GENERIC_MANDATORY_FIELDS)
def test_rsrp_negative_create_record_missing_mandatory_generic_field(api, tests_data, helper, field_path):
    """Reject record creation with missing mandatory generic field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS))
    helper.delete_by_path(data_payload, field_path)
    field_name = field_path.split("/")[-1]

    response = api.simulation_rock_physics.post_record(
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert f"{field_name} Field required" in body["errors"]
    assert len(body["errors"]) == 1, f"Expected errors list length 1, got {len(body['errors'])}"


@pytest.mark.parametrize("field_path,value,error_message", GENERIC_INVALID_TYPE_FIELDS)
def test_rsrp_negative_create_record_invalid_type_generic_field(
    api, tests_data, helper, field_path, value, error_message
):
    """Reject record creation with wrong type for generic field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS))
    helper.set_by_path(data_payload, field_path, value)

    response = api.simulation_rock_physics.post_record(
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert error_message in body["errors"]
    assert len(body["errors"]) == 1


@pytest.mark.parametrize("field_path,value,error_message", SPECIFIC_INVALID_TYPE_FIELDS)
def test_rsrp_negative_create_record_invalid_type_specific_field(
    api, tests_data, helper, field_path, value, error_message
):
    """Reject record creation with wrong type for specific field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS))
    helper.set_by_path(data_payload, field_path, value)

    response = api.simulation_rock_physics.post_record(
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert error_message in body["reason"][0]["errors"]
    assert len(body["reason"][0]["errors"]) == 1


@pytest.mark.parametrize("field_path,value", SPECIFIC_MISSING_REFERENCE_FIELDS)
def test_rsrp_negative_create_record_missing_reference_specific_field(api, tests_data, helper, field_path, value):
    """Reject record creation when referenced record doesn't exist with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS))
    helper.set_by_path(data_payload, field_path, value)
    record_value = value.rsplit(":", 1)[0]

    response = api.simulation_rock_physics.post_record(
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert (
        f"Request can't be processed due to missing referenced records. Records not found: ['{record_value}']"
        in body["reason"]
    )


@pytest.mark.parametrize("field_path,value", INVALID_REGEX_FIELDS)
def test_rsrp_negative_create_record_invalid_regex_specific_field(api, tests_data, helper, field_path, value):
    """Reject record creation when field doesn't match OSDU naming convention with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS))
    helper.set_by_path(data_payload, field_path, value)

    response = api.simulation_rock_physics.post_record(
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert any(f"'{value}' does not match " in error for error in body["reason"][0]["errors"])
    assert len(body["reason"][0]["errors"]) == 1


@pytest.mark.parametrize("field_path,value", GENERIC_EXTRA_FIELDS)
def test_rsrp_negative_create_record_extra_field_generic(api, tests_data, helper, field_path, value):
    """Reject record creation with unexpected/extra fields with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS))
    helper.set_by_path(data_payload, field_path, value)
    field_name = field_path.split("/")[-1]

    response = api.simulation_rock_physics.post_record(
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert f"{field_name} Extra inputs are not permitted" in body["errors"]
    assert len(body["errors"]) == 1


def test_rsrp_negative_create_unsupported_kind(api, tests_data, helper):
    """Reject record creation with unsupported kind value with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS))
    unsupported_kind = f"{DATA_PARTITION_ID}:wks:work-product-component--ReservoirSimulationRockPhysics:1.0.0"
    helper.set_by_path(data_payload, "/kind", unsupported_kind)

    response = api.simulation_rock_physics.post_record(
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert (
        f"Kind `{unsupported_kind}` not supported in RAFS-DDMS. Supported kinds for this endpoint: "
        f"['{DATA_PARTITION_ID}:wks:work-product-component--ReservoirSimulationRockPhysicsModel']"
    ) in body["reason"]


def test_rsrp_negative_create_unsupported_kind_version(api, tests_data, helper):
    """Reject record creation with unsupported kind version with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS))
    unsupported_version = "1.7"
    unsupported_kind = (
        f"{DATA_PARTITION_ID}:wks:work-product-component--ReservoirSimulationRockPhysicsModel:{unsupported_version}"
    )
    helper.set_by_path(data_payload, "/kind", unsupported_kind)

    response = api.simulation_rock_physics.post_record(
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert (
        f"Kind `{unsupported_kind}` has an invalid version `{unsupported_version}`. Version must be in "
        f"major.minor.patch format with non-negative integers."
    ) in body["reason"]


def test_rsrp_negative_create_invalid_record_id(api, tests_data, helper):
    """Reject record creation with invalid record ID format with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS))
    invalid_record_id = "WrongID:work-product-component--ReservoirSimulationRockPhysicsModel:WrongID"
    helper.set_by_path(data_payload, "/id", invalid_record_id)

    response = api.simulation_rock_physics.post_record(
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Invalid record id" in body["reason"]
    assert (
        f"The record '{invalid_record_id}' does not follow the naming convention: "
        f"The record id must be in the format of <tenantId>:<kindSubType>:<uniqueId>. "
        f"Example: {DATA_PARTITION_ID}:work-product-component--ReservoirSimulationRockPhysicsModel:<uuid>"
    ) in body["message"]


@pytest.mark.parametrize("field_path", GENERIC_MANDATORY_DATA_FIELDS)
def test_rsrp_negative_add_data_missing_mandatory_generic_field(api, tests_data, helper, field_path, record_id):
    """Reject data upload with missing mandatory structure field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
    helper.delete_by_path(data_payload, field_path)
    field_name = field_path.split("/")[-1]

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert f"Data error: missing required fields: '{field_name}'." in body["reason"]


@pytest.mark.parametrize("main_column,main_column_value", SPECIFIC_MANDATORY_DATA_MAIN_COLUMNS)
def test_rsrp_negative_add_data_missing_main_mandatory_column(
    api, tests_data, helper, main_column, main_column_value, record_id
):
    """Reject data upload with missing main column with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
    data_payload["data"][0][0] = f"{record_id}:"
    helper.delete_by_path(data_payload, main_column)
    helper.delete_by_path(data_payload, main_column_value)

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


@pytest.mark.parametrize("field_path", SPECIFIC_MANDATORY_DATA1_FIELDS)
def test_rsrp_negative_add_data_correlation_compressibility_missing_specific_mandatory_field(
    api, tests_data, helper, field_path, record_id
):
    """Reject data upload with missing main column with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
    helper.delete_by_path(data_payload, field_path)

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


@pytest.mark.parametrize("field_path", SPECIFIC_MANDATORY_DATA3_FIELDS)
def test_rsrp_negative_add_data_vtp_missing_specific_mandatory_field(api, tests_data, helper, field_path, record_id):
    """Reject data upload with missing main column with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA3_V1))
    helper.delete_by_path(data_payload, field_path)

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


@pytest.mark.parametrize("field_path,value", SPECIFIC_INVALID_TYPE_DATA1_FIELDS)
def test_rsrp_negative_add_data_correlation_compressibility_invalid_type_specific_field(
    api, tests_data, helper, field_path, value, record_id
):
    """Reject data upload with wrong type for specific field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
    helper.set_by_path(data_payload, field_path, value)

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


@pytest.mark.parametrize("field_path,value", SPECIFIC_INVALID_TYPE_DATA2_FIELDS)
def test_rsrp_negative_add_data_volume_multiplier_invalid_type_specific_field(
    api, tests_data, helper, field_path, value, record_id
):
    """Reject data upload with wrong type for specific field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA2_V1))
    helper.set_by_path(data_payload, field_path, value)

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


@pytest.mark.parametrize("field_path,value", SPECIFIC_INVALID_TYPE_DATA3_FIELDS)
def test_rsrp_negative_add_data_volume_vtp_type_specific_field(api, tests_data, helper, field_path, value, record_id):
    """Reject data upload with wrong type for specific field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA3_V1))
    helper.set_by_path(data_payload, field_path, value)

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


@pytest.mark.parametrize("field_path,value", SPECIFIC_MISSING_REFERENCE_DATA_FIELDS)
def test_rsrp_negative_add_data_missing_reference_specific_field(api, tests_data, helper, field_path, value, record_id):
    """Reject data upload when referenced record doesn't exist with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
    helper.set_by_path(data_payload, field_path, value)
    record_value = value.rsplit(":", 1)[0]

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert record_value in body["errors"]["Missing records in storage"]


@pytest.mark.parametrize("field_path,value", SPECIFIC_INVALID_REGEX_DATA_FIELDS)
def test_rsrp_negative_add_data_invalid_regex_specific_field(api, tests_data, helper, field_path, value, record_id):
    """Reject data upload when field doesn't match OSDU naming convention with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
    helper.set_by_path(data_payload, field_path, value)

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


def test_rsrp_negative_add_data_extra_main_field(api, tests_data, record_id):
    """Reject data upload with unexpected/extra fields with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
    data_payload["columns"].append("ExtraColumn")
    data_payload["data"][0].append("ExtraColumnValue")

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


def test_rsrp_negative_add_data_extra_main_nullable_field(api, tests_data, record_id):
    """Reject data upload with unexpected/extra main field with null value with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
    data_payload["columns"].append("ExtraColumn")
    data_payload["data"][0].append(None)

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


@pytest.mark.parametrize("field_path,value", EXTRA_DATA_FIELDS)
def test_rsrp_negative_add_data_extra_field(api, tests_data, helper, field_path, value, record_id):
    """Reject data upload with unexpected/extra fields with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
    helper.set_by_path(data_payload, field_path, value)

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


def test_rsrp_negative_create_record_invalid_payload_format(api, tests_data):
    """Reject record creation when payload is not a list with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS))

    response = api.simulation_rock_physics.post_record(
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert "body Input should be a valid list" in body["errors"]


def test_rsrp_negative_add_data_invalid_payload_format(api, tests_data, record_id):
    """Reject data upload when payload is wrapped in array with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=[data_payload],
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


def test_rsrp_negative_add_data_records_format_invalid_payload_format(api, tests_data, record_id):
    """Reject data upload when payload is not wrapped in array if records format with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1_RECORDS_FORMAT))

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert (
        "Data error: missing required fields: 'columns', 'index', 'data'. "
        "For records format, wrap the data in an array [{...}, ...]." in body["reason"]
    )


@pytest.mark.parametrize("field_path", SPECIFIC_MANDATORY_DATA1_FIELDS_RECORDS_FORMAT)
def test_rsrp_negative_add_data_records_format_missing_specific_field(api, tests_data, helper, field_path, record_id):
    """Reject data upload in records format with missing main column with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1_RECORDS_FORMAT))
    helper.delete_by_path(data_payload, field_path)

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


@pytest.mark.parametrize("field_path,value", SPECIFIC_INVALID_TYPE_DATA_FIELDS_RECORDS_FORMAT)
def test_rsrp_negative_add_data_records_format_invalid_type_specific_field(
    api, tests_data, helper, field_path, value, record_id
):
    """Reject data upload in records format with wrong type for specific field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1_RECORDS_FORMAT))
    helper.set_by_path(data_payload, field_path, value)

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


@pytest.mark.parametrize("field_path,value", SPECIFIC_MISSING_REFERENCE_DATA_FIELDS_RECORDS_FORMAT)
def test_rsrp_negative_add_data_records_format_missing_reference_specific_field(
    api, tests_data, helper, field_path, value, record_id
):
    """Reject data upload in records format when referenced record doesn't exist with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1_RECORDS_FORMAT))
    helper.set_by_path(data_payload, field_path, value)
    record_value = value.rsplit(":", 1)[0]

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert record_value in body["errors"]["Missing records in storage"]


@pytest.mark.parametrize("field_path,value", SPECIFIC_INVALID_REGEX_DATA_FIELDS_RECORDS_FORMAT)
def test_rsrp_negative_add_data_records_format_invalid_regex_specific_field(
    api, tests_data, helper, field_path, value, record_id
):
    """Reject data upload in records format when field doesn't match OSDU naming convention
    with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1_RECORDS_FORMAT))
    helper.set_by_path(data_payload, field_path, value)

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


@pytest.mark.parametrize("field_path,value", EXTRA_DATA_FIELDS_RECORDS_FORMAT)
def test_rsrp_negative_add_data_records_format_extra_field(api, tests_data, helper, field_path, value, record_id):
    """Reject data upload in records format with unexpected/extra fields with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1_RECORDS_FORMAT))
    helper.set_by_path(data_payload, field_path, value)

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert "field" in body["errors"]["Invalid type"][0]


def test_rsrp_negative_add_data_record_id_mismatch_between_payload_and_url(api, tests_data, record_id, fresh_record_id):
    """Reject data upload with record_id different in bulk data and URL with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
    data_payload["data"][0][0] = f"{fresh_record_id}:"

    response = api.simulation_rock_physics.post_data(
        record_id=record_id,
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert body["errors"]["Invalid value"][0]["ReservoirSimulationRockPhysicsID"] == f"{fresh_record_id}:"
