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
    SCHEMA_AUTHORITY,
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

SPECIFIC_MANDATORY_FIELDS = [
    "/data/SaturationFunctions",
    "/data/SaturationFunctions/0/FunctionUsageTypeID",
    "/data/SaturationFunctions/0/HasRelativePermeability",
    "/data/SaturationFunctions/0/HasCapillaryPressure",
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
    ("/data/Description", ["Description"], "['Description'] is not of type 'string'"),
    ("/data/Source", ["Source"], "['Source'] is not of type 'string'"),
    ("/data/Remarks", "Remarks", "'Remarks' is not of type 'array'"),
    (
        "/data/Remarks/0/RemarkSequenceNumber",
        "RemarkSequenceNumber",
        "'RemarkSequenceNumber' is not of type 'integer'",
    ),
    ("/data/Remarks/0/Remark", ["Remark"], "['Remark'] is not of type 'string'"),
    ("/data/Remarks/0/RemarkSource", ["RemarkSource"], "['RemarkSource'] is not of type 'string'"),
    ("/data/Remarks/0/RemarkDate", ["RemarkDate"], "['RemarkDate'] is not of type 'string'"),
    ("/data/SaturationFunctions", "SaturationFunctions", "'SaturationFunctions' is not of type 'array'"),
    (
        "/data/SaturationFunctions/0/FunctionUsageTypeID",
        ["FunctionUsageTypeID"],
        "['FunctionUsageTypeID'] is not of type 'string'",
    ),
    ("/data/SaturationFunctions/0/FunctionName", ["FunctionName"], "['FunctionName'] is not of type 'string'"),
    ("/data/SaturationFunctions/0/DatePublished", "DatePublished", "'DatePublished' is not a 'date-time'"),
    (
        "/data/SaturationFunctions/0/HasRelativePermeability",
        ["HasRelativePermeability"],
        "['HasRelativePermeability'] is not of type 'boolean'",
    ),
    (
        "/data/SaturationFunctions/0/HasCapillaryPressure",
        ["HasCapillaryPressure"],
        "['HasCapillaryPressure'] is not of type 'boolean'",
    ),
    (
        "/data/SaturationFunctions/0/ModellingContacts",
        "ModellingContacts",
        "'ModellingContacts' is not of type 'array'",
    ),
    (
        "/data/SaturationFunctions/0/ModelAreaOfInterestIDs",
        "ModelAreaOfInterestIDs",
        "'ModelAreaOfInterestIDs' is not of type 'array'",
    ),
    (
        "/data/SaturationFunctions/0/BasisOfModelling",
        ["BasisOfModelling"],
        "['BasisOfModelling'] is not of type 'object'",
    ),
    (
        "/data/SaturationFunctions/0/BasisOfModelling/CapillaryPressureInputDataCollectionID",
        ["CapillaryPressureInputDataCollectionID"],
        "['CapillaryPressureInputDataCollectionID'] is not of type 'string'",
    ),
    (
        "/data/SaturationFunctions/0/BasisOfModelling/CapillaryPressureInputSampleAnalysisIDs",
        "CapillaryPressureInputSampleAnalysisIDs",
        "'CapillaryPressureInputSampleAnalysisIDs' is not of type 'array'",
    ),
    (
        "/data/SaturationFunctions/0/BasisOfModelling/RelativePermeabilityInputDataCollectionID",
        ["RelativePermeabilityInputDataCollectionID"],
        "['RelativePermeabilityInputDataCollectionID'] is not of type 'string'",
    ),
    (
        "/data/SaturationFunctions/0/BasisOfModelling/RelativePermeabilityInputSampleAnalysisIDs",
        "RelativePermeabilityInputSampleAnalysisIDs",
        "'RelativePermeabilityInputSampleAnalysisIDs' is not of type 'array'",
    ),
    (
        "/data/SaturationFunctions/0/BasisOfModelling/ModellingApplicationsUsed",
        "ModellingApplicationsUsed",
        "'ModellingApplicationsUsed' is not of type 'array'",
    ),
    (
        "/data/SaturationFunctions/0/BasisOfModelling/IntendedWorkflowUsageIDs",
        "IntendedWorkflowUsageIDs",
        "'IntendedWorkflowUsageIDs' is not of type 'array'",
    ),
]

SPECIFIC_MISSING_REFERENCE_FIELDS = [
    (
        "/data/SaturationFunctions/0/FunctionUsageTypeID",
        f"{DATA_PARTITION_ID}:reference-data--SaturationFunctionUsageType:dummy:",
    ),
    (
        "/data/SaturationFunctions/0/BasisOfModelling/CapillaryPressureInputDataCollectionID",
        f"{DATA_PARTITION_ID}:work-product-component--PersistedCollection:dummy:",
    ),
    (
        "/data/SaturationFunctions/0/BasisOfModelling/RelativePermeabilityInputDataCollectionID",
        f"{DATA_PARTITION_ID}:work-product-component--PersistedCollection:dummy:",
    ),
]

INVALID_REGEX_FIELDS = [
    ("/id", f"{DATA_PARTITION_ID}:work-product-component-SaturationFunctionSet:"),
    (
        "/data/SaturationFunctions/0/FunctionUsageTypeID",
        f"{DATA_PARTITION_ID}:reference-data-SaturationFunctionUsageType:Drainage:",
    ),
    (
        "/data/SaturationFunctions/0/BasisOfModelling/CapillaryPressureInputDataCollectionID",
        f"{DATA_PARTITION_ID}:work-product-component-PersistedCollection:dummy:",
    ),
    (
        "/data/SaturationFunctions/0/BasisOfModelling/RelativePermeabilityInputDataCollectionID",
        f"{DATA_PARTITION_ID}:work-product-component-PersistedCollection:dummy:",
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

SPECIFIC_MANDATORY_DATA_FIELDS = [
    "/data/0/2/0/FunctionUsageTypeID",
    "/data/0/3/0/FunctionUsageTypeID",
    "/data/0/2/0/PhaseRelativePermeabilityFunctions",
    "/data/0/3/0/PhaseCapillaryPressureFunctions",
    "/data/0/2/0/PhaseRelativePermeabilityFunctions/0/PhaseSaturationFluidID",
    "/data/0/3/0/PhaseCapillaryPressureFunctions/0/PhaseSaturationFluidID",
    "/data/0/2/0/PhaseRelativePermeabilityFunctions/0/PhaseRelativePermeabilityFluidID",
    "/data/0/3/0/PhaseCapillaryPressureFunctions/0/PhaseCapillaryPressureFluidID",
]

SPECIFIC_INVALID_TYPE_DATA_FIELDS = [
    ("/data/0/2/0/FunctionUsageTypeID", ["FunctionUsageTypeID"]),
    ("/data/0/2/0/PhaseRelativePermeabilityFunctions", "PhaseRelativePermeabilityFunctions"),
    ("/data/0/2/0/PhaseRelativePermeabilityFunctions/0/Saturation", "Saturation"),
    ("/data/0/2/0/PhaseRelativePermeabilityFunctions/0/RelativePermeability", "RelativePermeability"),
    (
        "/data/0/2/0/PhaseRelativePermeabilityFunctions/0/PhaseRelativePermeabilityFluidID",
        ["PhaseRelativePermeabilityFluidID"],
    ),
    ("/data/0/2/0/PhaseRelativePermeabilityFunctions/0/PhaseSaturationFluidID", ["PhaseSaturationFluidID"]),
    ("/data/0/3/0/FunctionUsageTypeID", ["FunctionUsageTypeID"]),
    ("/data/0/3/0/PhaseCapillaryPressureFunctions", "PhaseRelativePermeabilityFunctions"),
    ("/data/0/3/0/PhaseCapillaryPressureFunctions/0/Saturation", "Saturation"),
    ("/data/0/3/0/PhaseCapillaryPressureFunctions/0/CapillaryPressure", "CapillaryPressure"),
    ("/data/0/3/0/PhaseCapillaryPressureFunctions/0/PhaseCapillaryPressureFluidID", ["PhaseCapillaryPressureFluidID"]),
    ("/data/0/3/0/PhaseCapillaryPressureFunctions/0/PhaseSaturationFluidID", ["PhaseSaturationFluidID"]),
]

SPECIFIC_MISSING_REFERENCE_DATA_FIELDS = [
    ("/data/0/1/0/unitOfMeasureID", f"{DATA_PARTITION_ID}:reference-data--UnitOfMeasure:Dummy:"),
    ("/data/0/2/0/FunctionUsageTypeID", f"{DATA_PARTITION_ID}:reference-data--SaturationFunctionUsageType:Dummy:"),
    (
        "/data/0/2/0/PhaseRelativePermeabilityFunctions/0/PhaseRelativePermeabilityFluidID",
        f"{DATA_PARTITION_ID}:reference-data--RockModelRelativePermeabilityPhase:Dummy:",
    ),
    (
        "/data/0/2/0/PhaseRelativePermeabilityFunctions/0/PhaseSaturationFluidID",
        f"{DATA_PARTITION_ID}:reference-data--FluidModelPropertyPhase:Dummy:",
    ),
    (
        "/data/0/3/0/FunctionUsageTypeID",
        f"{DATA_PARTITION_ID}:reference-data--SaturationFunctionUsageType:Dummy:",
    ),
    (
        "/data/0/3/0/PhaseCapillaryPressureFunctions/0/PhaseCapillaryPressureFluidID",
        f"{DATA_PARTITION_ID}:reference-data--RockModelCapillaryPressurePhase:Dummy:",
    ),
    (
        "/data/0/3/0/PhaseCapillaryPressureFunctions/0/PhaseSaturationFluidID",
        f"{DATA_PARTITION_ID}:reference-data--FluidModelPropertyPhase:Dummy:",
    ),
]

SPECIFIC_INVALID_REGEX_DATA_FIELDS = [
    ("/data/0/1/0/unitOfMeasureID", f"{DATA_PARTITION_ID}:reference-data-UnitOfMeasure:Dummy:"),
    ("/data/0/2/0/FunctionUsageTypeID", f"{DATA_PARTITION_ID}:reference-data-SaturationFunctionUsageType:Dummy:"),
    (
        "/data/0/2/0/PhaseRelativePermeabilityFunctions/0/PhaseRelativePermeabilityFluidID",
        f"{DATA_PARTITION_ID}:reference-data-RockModelRelativePermeabilityPhase:Dummy:",
    ),
    (
        "/data/0/2/0/PhaseRelativePermeabilityFunctions/0/PhaseSaturationFluidID",
        f"{DATA_PARTITION_ID}:reference-data-FluidModelPropertyPhase:Dummy:",
    ),
    ("/data/0/3/0/FunctionUsageTypeID", f"{DATA_PARTITION_ID}:reference-data-SaturationFunctionUsageType:Dummy:"),
    (
        "/data/0/3/0/PhaseCapillaryPressureFunctions/0/PhaseCapillaryPressureFluidID",
        f"{DATA_PARTITION_ID}:reference-data-RockModelCapillaryPressurePhase:Dummy:",
    ),
    (
        "/data/0/3/0/PhaseCapillaryPressureFunctions/0/PhaseSaturationFluidID",
        f"{DATA_PARTITION_ID}:reference-data-FluidModelPropertyPhase:Dummy:",
    ),
]

EXTRA_DATA_FIELDS = [
    ("/data/0/1/0/ExtraMeta", "ExtraMetaValue"),
    ("/data/0/2/0/ExtraRelativePermeabilityFunction", "ExtraRelativePermeabilityFunctionValue"),
    (
        "/data/0/2/0/PhaseRelativePermeabilityFunctions/0/ExtraPhaseRelativePermeabilityFunctions",
        "ExtraPhaseRelativePermeabilityFunctionsValue",
    ),
    ("/data/0/3/0/ExtraCapillaryPressureFunction", "ExtraCapillaryPressureFunctionValue"),
    (
        "/data/0/3/0/PhaseCapillaryPressureFunctions/0/ExtraPhaseCapillaryPressureFunctions",
        "ExtraPhaseCapillaryPressureFunctionsValue",
    ),
]

SPECIFIC_MANDATORY_DATA_FIELDS_RECORDS_FORMAT = [
    "/SaturationFunctionSetID",
    "/RelativePermeabilityFunctions/0/FunctionUsageTypeID",
    "/CapillaryPressureFunctions/0/FunctionUsageTypeID",
    "/RelativePermeabilityFunctions/0/PhaseRelativePermeabilityFunctions",
    "/CapillaryPressureFunctions/0/PhaseCapillaryPressureFunctions",
    "/RelativePermeabilityFunctions/0/PhaseRelativePermeabilityFunctions/0/PhaseSaturationFluidID",
    "/CapillaryPressureFunctions/0/PhaseCapillaryPressureFunctions/0/PhaseSaturationFluidID",
    "/RelativePermeabilityFunctions/0/PhaseRelativePermeabilityFunctions/0/PhaseRelativePermeabilityFluidID",
    "/CapillaryPressureFunctions/0/PhaseCapillaryPressureFunctions/0/PhaseCapillaryPressureFluidID",
]

SPECIFIC_INVALID_TYPE_DATA_FIELDS_RECORDS_FORMAT = [
    ("/SaturationFunctionSetID", ["SaturationFunctionSetID"]),
    ("/RelativePermeabilityFunctions/0/FunctionUsageTypeID", ["FunctionUsageTypeID"]),
    ("/RelativePermeabilityFunctions/0/PhaseRelativePermeabilityFunctions", "PhaseRelativePermeabilityFunctions"),
    ("/RelativePermeabilityFunctions/0/PhaseRelativePermeabilityFunctions/0/Saturation", "Saturation"),
    (
        "/RelativePermeabilityFunctions/0/PhaseRelativePermeabilityFunctions/0/RelativePermeability",
        "RelativePermeability",
    ),
    (
        "/RelativePermeabilityFunctions/0/PhaseRelativePermeabilityFunctions/0/PhaseRelativePermeabilityFluidID",
        ["PhaseRelativePermeabilityFluidID"],
    ),
    (
        "/RelativePermeabilityFunctions/0/PhaseRelativePermeabilityFunctions/0/PhaseSaturationFluidID",
        ["PhaseSaturationFluidID"],
    ),
    ("/CapillaryPressureFunctions/0/FunctionUsageTypeID", ["FunctionUsageTypeID"]),
    ("/CapillaryPressureFunctions/0/PhaseCapillaryPressureFunctions", "PhaseRelativePermeabilityFunctions"),
    ("/CapillaryPressureFunctions/0/PhaseCapillaryPressureFunctions/0/Saturation", "Saturation"),
    ("/CapillaryPressureFunctions/0/PhaseCapillaryPressureFunctions/0/CapillaryPressure", "CapillaryPressure"),
    (
        "/CapillaryPressureFunctions/0/PhaseCapillaryPressureFunctions/0/PhaseCapillaryPressureFluidID",
        ["PhaseCapillaryPressureFluidID"],
    ),
    (
        "/CapillaryPressureFunctions/0/PhaseCapillaryPressureFunctions/0/PhaseSaturationFluidID",
        ["PhaseSaturationFluidID"],
    ),
]

SPECIFIC_MISSING_REFERENCE_DATA_FIELDS_RECORDS_FORMAT = [
    ("/SaturationFunctionSetID", f"{DATA_PARTITION_ID}:work-product-component--SaturationFunctionSet:Dummy:"),
    ("/Meta/0/unitOfMeasureID", f"{DATA_PARTITION_ID}:reference-data--UnitOfMeasure:Dummy:"),
    (
        "/RelativePermeabilityFunctions/0/FunctionUsageTypeID",
        f"{DATA_PARTITION_ID}:reference-data--SaturationFunctionUsageType:Dummy:",
    ),
    (
        "/RelativePermeabilityFunctions/0/PhaseRelativePermeabilityFunctions/0/PhaseRelativePermeabilityFluidID",
        f"{DATA_PARTITION_ID}:reference-data--RockModelRelativePermeabilityPhase:Dummy:",
    ),
    (
        "/RelativePermeabilityFunctions/0/PhaseRelativePermeabilityFunctions/0/PhaseSaturationFluidID",
        f"{DATA_PARTITION_ID}:reference-data--FluidModelPropertyPhase:Dummy:",
    ),
    (
        "/CapillaryPressureFunctions/0/FunctionUsageTypeID",
        f"{DATA_PARTITION_ID}:reference-data--SaturationFunctionUsageType:Dummy:",
    ),
    (
        "/CapillaryPressureFunctions/0/PhaseCapillaryPressureFunctions/0/PhaseCapillaryPressureFluidID",
        f"{DATA_PARTITION_ID}:reference-data--RockModelCapillaryPressurePhase:Dummy:",
    ),
    (
        "/CapillaryPressureFunctions/0/PhaseCapillaryPressureFunctions/0/PhaseSaturationFluidID",
        f"{DATA_PARTITION_ID}:reference-data--FluidModelPropertyPhase:Dummy:",
    ),
]

SPECIFIC_INVALID_REGEX_DATA_FIELDS_RECORDS_FORMAT = [
    ("/SaturationFunctionSetID", f"{DATA_PARTITION_ID}:work-product-component-SaturationFunctionSet:Dummy:"),
    ("/Meta/0/unitOfMeasureID", f"{DATA_PARTITION_ID}:reference-data-UnitOfMeasure:Dummy:"),
    (
        "/RelativePermeabilityFunctions/0/FunctionUsageTypeID",
        f"{DATA_PARTITION_ID}:reference-data-SaturationFunctionUsageType:Dummy:",
    ),
    (
        "/RelativePermeabilityFunctions/0/PhaseRelativePermeabilityFunctions/0/PhaseRelativePermeabilityFluidID",
        f"{DATA_PARTITION_ID}:reference-data-RockModelRelativePermeabilityPhase:Dummy:",
    ),
    (
        "/RelativePermeabilityFunctions/0/PhaseRelativePermeabilityFunctions/0/PhaseSaturationFluidID",
        f"{DATA_PARTITION_ID}:reference-data-FluidModelPropertyPhase:Dummy:",
    ),
    (
        "/CapillaryPressureFunctions/0/FunctionUsageTypeID",
        f"{DATA_PARTITION_ID}:reference-data-SaturationFunctionUsageType:Dummy:",
    ),
    (
        "/CapillaryPressureFunctions/0/PhaseCapillaryPressureFunctions/0/PhaseCapillaryPressureFluidID",
        f"{DATA_PARTITION_ID}:reference-data-RockModelCapillaryPressurePhase:Dummy:",
    ),
    (
        "/CapillaryPressureFunctions/0/PhaseCapillaryPressureFunctions/0/PhaseSaturationFluidID",
        f"{DATA_PARTITION_ID}:reference-data-FluidModelPropertyPhase:Dummy:",
    ),
]

EXTRA_DATA_FIELDS_RECORDS_FORMAT = [
    ("/ExtraMainColumn", "ExtraMainColumnValue"),
    ("/Meta/0/ExtraMeta", "ExtraMetaValue"),
    ("/RelativePermeabilityFunctions/0/ExtraRelativePermeabilityFunction", "ExtraRelativePermeabilityFunctionValue"),
    (
        "/RelativePermeabilityFunctions/0/PhaseRelativePermeabilityFunctions/0/ExtraPhaseRelativePermeabilityFunctions",
        "ExtraPhaseRelativePermeabilityFunctionsValue",
    ),
    ("/CapillaryPressureFunctions/0/ExtraCapillaryPressureFunction", "ExtraCapillaryPressureFunctionValue"),
    (
        "/CapillaryPressureFunctions/0/PhaseCapillaryPressureFunctions/0/ExtraPhaseCapillaryPressureFunctions",
        "ExtraPhaseCapillaryPressureFunctionsValue",
    ),
]


@pytest.mark.parametrize("field_path", GENERIC_MANDATORY_FIELDS)
def test_sfs_negative_create_record_missing_mandatory_generic_field(api, tests_data, helper, field_path):
    """Reject record creation with missing mandatory generic field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET))
    helper.delete_by_path(data_payload, field_path)
    field_name = field_path.split("/")[-1]

    response = api.saturation_function_set.post_record(
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


@pytest.mark.parametrize("field_path", SPECIFIC_MANDATORY_FIELDS)
def test_sfs_negative_create_record_missing_mandatory_specific_field(api, tests_data, helper, field_path):
    """Reject record creation with missing mandatory specific field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET))
    helper.delete_by_path(data_payload, field_path)
    field_name = field_path.split("/")[-1]

    response = api.saturation_function_set.post_record(
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert (
        f"Missing {field_name} in index 0" in body["reason"]
        or f"'{field_name}' is a required property" in body["reason"][0]["errors"]
    )
    assert len(body["reason"]) == 1 or len(body["reason"][0]["errors"]) == 1


@pytest.mark.parametrize("field_path,value,error_message", GENERIC_INVALID_TYPE_FIELDS)
def test_sfs_negative_create_record_invalid_type_generic_field(
    api, tests_data, helper, field_path, value, error_message
):
    """Reject record creation with wrong type for generic field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET))
    helper.set_by_path(data_payload, field_path, value)

    response = api.saturation_function_set.post_record(
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
def test_sfs_negative_create_record_invalid_type_specific_field(
    api, tests_data, helper, field_path, value, error_message
):
    """Reject record creation with wrong type for specific field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET))
    helper.set_by_path(data_payload, field_path, value)

    response = api.saturation_function_set.post_record(
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
def test_sfs_negative_create_record_missing_reference_specific_field(api, tests_data, helper, field_path, value):
    """Reject record creation when referenced record doesn't exist with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET))
    helper.set_by_path(data_payload, field_path, value)
    record_value = value.rsplit(":", 1)[0]

    response = api.saturation_function_set.post_record(
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
def test_sfs_negative_create_record_invalid_regex_specific_field(api, tests_data, helper, field_path, value):
    """Reject record creation when field doesn't match OSDU naming convention with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET))
    helper.set_by_path(data_payload, field_path, value)

    response = api.saturation_function_set.post_record(
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
def test_sfs_negative_create_record_extra_field_generic(api, tests_data, helper, field_path, value):
    """Reject record creation with unexpected/extra fields with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET))
    helper.set_by_path(data_payload, field_path, value)
    field_name = field_path.split("/")[-1]

    response = api.saturation_function_set.post_record(
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


def test_sfs_negative_create_unsupported_kind(api, tests_data, helper):
    """Reject record creation with unsupported kind value with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET))
    unsupported_kind = f"{SCHEMA_AUTHORITY}:wks:work-product-component--SaturationFunctionSetModel:1.0.0"
    helper.set_by_path(data_payload, "/kind", unsupported_kind)

    response = api.saturation_function_set.post_record(
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert (
        f"Kind `{unsupported_kind}` not supported in RAFS-DDMS. Supported kinds for this endpoint: "
        f"['{SCHEMA_AUTHORITY}:wks:work-product-component--SaturationFunctionSet']"
    ) in body["reason"]


def test_sfs_negative_create_unsupported_kind_version(api, tests_data, helper):
    """Reject record creation with unsupported kind version with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET))
    unsupported_version = "1.7"
    unsupported_kind = f"{SCHEMA_AUTHORITY}:wks:work-product-component--SaturationFunctionSet:{unsupported_version}"
    helper.set_by_path(data_payload, "/kind", unsupported_kind)

    response = api.saturation_function_set.post_record(
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


def test_sfs_negative_create_invalid_record_id(api, tests_data, helper):
    """Reject record creation with invalid record ID format with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET))
    invalid_record_id = "WrongID:work-product-component--SaturationFunctionSet:WrongID"
    helper.set_by_path(data_payload, "/id", invalid_record_id)

    response = api.saturation_function_set.post_record(
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
        f"Example: {DATA_PARTITION_ID}:work-product-component--SaturationFunctionSet:<uuid>"
    ) in body["message"]


@pytest.mark.parametrize("field_path", GENERIC_MANDATORY_DATA_FIELDS)
def test_sfs_negative_add_data_missing_mandatory_generic_field(api, tests_data, helper, field_path, record_id):
    """Reject data upload with missing mandatory structure field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1))
    helper.delete_by_path(data_payload, field_path)
    field_name = field_path.split("/")[-1]

    response = api.saturation_function_set.post_data(
        record_id=record_id,
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert f"Data error: missing required fields: '{field_name}'." in body["reason"]


def test_sfs_negative_add_data_missing_main_mandatory_column(api, tests_data, helper, record_id):
    """Reject data upload with missing main column with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1))
    helper.delete_by_path(data_payload, "/columns/0")
    helper.delete_by_path(data_payload, "/data/0/0")

    response = api.saturation_function_set.post_data(
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


@pytest.mark.parametrize("field_path", SPECIFIC_MANDATORY_DATA_FIELDS)
def test_sfs_negative_add_data_missing_specific_mandatory_field(api, tests_data, helper, field_path, record_id):
    """Reject data upload with missing main column with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1))
    helper.delete_by_path(data_payload, field_path)

    response = api.saturation_function_set.post_data(
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


@pytest.mark.parametrize("field_path,value", SPECIFIC_INVALID_TYPE_DATA_FIELDS)
def test_sfs_negative_add_data_invalid_type_specific_field(api, tests_data, helper, field_path, value, record_id):
    """Reject data upload with wrong type for specific field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1))
    helper.set_by_path(data_payload, field_path, value)

    response = api.saturation_function_set.post_data(
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
def test_sfs_negative_add_data_missing_reference_specific_field(api, tests_data, helper, field_path, value, record_id):
    """Reject data upload when referenced record doesn't exist with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1))
    helper.set_by_path(data_payload, field_path, value)
    record_value = value.rsplit(":", 1)[0]

    response = api.saturation_function_set.post_data(
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
def test_sfs_negative_add_data_invalid_regex_specific_field(api, tests_data, helper, field_path, value, record_id):
    """Reject data upload when field doesn't match OSDU naming convention with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1))
    helper.set_by_path(data_payload, field_path, value)

    response = api.saturation_function_set.post_data(
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


def test_sfs_negative_add_data_extra_main_field(api, tests_data, record_id):
    """Reject data upload with unexpected/extra fields with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1))
    data_payload["columns"].append("ExtraColumn")
    data_payload["data"][0].append("ExtraColumnValue")

    response = api.saturation_function_set.post_data(
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


def test_sfs_negative_add_data_extra_main_nullable_field(api, tests_data, record_id):
    """Reject data upload with unexpected/extra main field with null value with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1))
    data_payload["columns"].append("ExtraColumn")
    data_payload["data"][0].append(None)

    response = api.saturation_function_set.post_data(
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
def test_sfs_negative_add_data_extra_field(api, tests_data, helper, field_path, value, record_id):
    """Reject data upload with unexpected/extra fields with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1))
    helper.set_by_path(data_payload, field_path, value)

    response = api.saturation_function_set.post_data(
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


def test_sfs_negative_create_record_invalid_payload_format(api, tests_data):
    """Reject record creation when payload is not a list with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET))

    response = api.saturation_function_set.post_record(
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert "body Input should be a valid list" in body["errors"]


def test_sfs_negative_add_data_invalid_payload_format(api, tests_data, record_id):
    """Reject data upload when payload is wrapped in array with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1))

    response = api.saturation_function_set.post_data(
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


def test_sfs_negative_add_data_records_format_invalid_payload_format(api, tests_data, record_id):
    """Reject data upload when payload is not wrapped in array if records format with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1_RECORDS_FORMAT))

    response = api.saturation_function_set.post_data(
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


@pytest.mark.parametrize("field_path", SPECIFIC_MANDATORY_DATA_FIELDS_RECORDS_FORMAT)
def test_sfs_negative_add_data_records_format_missing_specific_field(api, tests_data, helper, field_path, record_id):
    """Reject data upload in records format with missing main column with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1_RECORDS_FORMAT))
    helper.delete_by_path(data_payload, field_path)

    response = api.saturation_function_set.post_data(
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
def test_sfs_negative_add_data_records_format_invalid_type_specific_field(
    api, tests_data, helper, field_path, value, record_id
):
    """Reject data upload in records format with wrong type for specific field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1_RECORDS_FORMAT))
    helper.set_by_path(data_payload, field_path, value)

    response = api.saturation_function_set.post_data(
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
def test_sfs_negative_add_data_records_format_missing_reference_specific_field(
    api, tests_data, helper, field_path, value, record_id
):
    """Reject data upload in records format when referenced record doesn't exist with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1_RECORDS_FORMAT))
    helper.set_by_path(data_payload, field_path, value)
    record_value = value.rsplit(":", 1)[0]

    response = api.saturation_function_set.post_data(
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
def test_sfs_negative_add_data_records_format_invalid_regex_specific_field(
    api, tests_data, helper, field_path, value, record_id
):
    """Reject data upload in records format when field doesn't match OSDU naming convention
    with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1_RECORDS_FORMAT))
    helper.set_by_path(data_payload, field_path, value)

    response = api.saturation_function_set.post_data(
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
def test_sfs_negative_add_data_records_format_extra_field(api, tests_data, helper, field_path, value, record_id):
    """Reject data upload in records format with unexpected/extra fields with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1_RECORDS_FORMAT))
    helper.set_by_path(data_payload, field_path, value)

    response = api.saturation_function_set.post_data(
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


def test_sfs_negative_add_data_record_id_mismatch_between_payload_and_url(api, tests_data, record_id, fresh_record_id):
    """Reject data upload with record_id different in bulk data and URL with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1))
    data_payload["data"][0][0] = f"{fresh_record_id}:"

    response = api.saturation_function_set.post_data(
        record_id=record_id,
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Data validation failed." in body["reason"]
    assert body["errors"]["Invalid value"][0]["SaturationFunctionSetID"] == f"{fresh_record_id}:"
