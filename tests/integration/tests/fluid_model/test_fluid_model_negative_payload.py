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
    ("/id", ["id"], "id str type expected"),
    ("/kind", ["kind"], "kind str type expected"),
    ("/legal", ["legal"], "legal value is not a valid dict"),
    ("/acl", ["acl"], "acl value is not a valid dict"),
    ("/legal/legaltags", "legaltags", "legaltags value is not a valid list"),
    (
        "/legal/otherRelevantDataCountries",
        "otherRelevantDataCountries",
        "otherRelevantDataCountries value is not a valid list",
    ),
    ("/acl/owners", "owners", "owners value is not a valid list"),
    ("/acl/viewers", "viewers", "viewers value is not a valid list"),
    ("/data", "data", "data value is not a valid dict"),
]

SPECIFIC_INVALID_TYPE_FIELDS = [
    ("/data/FluidModelTypeID", ["FluidModelTypeID"], "['FluidModelTypeID'] is not of type 'string'"),
    ("/data/ParentModelID", ["ParentModelID"], "['ParentModelID'] is not of type 'string'"),
    ("/data/ModellingContacts", "ModellingContacts", "'ModellingContacts' is not of type 'array'"),
    ("/data/ModelAreaOfInterestIDs", "ModelAreaOfInterestIDs", "'ModelAreaOfInterestIDs' is not of type 'array'"),
    ("/data/Remarks", "Remarks", "'Remarks' is not of type 'array'"),
    ("/data/BasisOfModelling", ["BasisOfModelling"], "['BasisOfModelling'] is not of type 'object'"),
    (
        "/data/BasisOfModelling/IsOptimizedForEnhancedRecoveryStudies",
        ["IsOptimizedForEnhancedRecoveryStudies"],
        "['IsOptimizedForEnhancedRecoveryStudies'] is not of type 'boolean'",
    ),
    (
        "/data/BasisOfModelling/ComponentCount",
        ["ComponentCount"],
        "['ComponentCount'] is not of type 'number'",
    ),
    (
        "/data/FluidModelSaturationTypeID",
        ["FluidModelSaturationTypeID"],
        "['FluidModelSaturationTypeID'] is not of type 'string'"
    ),
    (
        "/data/IsApplicableForThermalSimulation",
        ["IsApplicableForThermalSimulation"],
        "['IsApplicableForThermalSimulation'] is not of type 'boolean'"
    ),
    (
        "/data/HasVariableDepthFluidProperties",
        ["HasVariableDepthFluidProperties"],
        "['HasVariableDepthFluidProperties'] is not of type 'boolean'"
    ),
]

SPECIFIC_MISSING_REFERENCE_FIELDS = [
    ("/data/FluidModelTypeID", f"{DATA_PARTITION_ID}:reference-data--FluidModelType:dummy:"),
    ("/data/ParentModelID", f"{DATA_PARTITION_ID}:work-product-component--FluidModel:dummy:"),
    ("/data/ModelAreaOfInterestIDs/0", f"{DATA_PARTITION_ID}:master-data--Reservoir:dummy:"),
    ("/data/FluidModelSaturationTypeID", f"{DATA_PARTITION_ID}:reference-data--FluidModelSaturationType:dummy:"),
    (
        "/data/BasisOfModelling/InputDataCollectionID",
        f"{DATA_PARTITION_ID}:work-product-component--PersistedCollection:dummy:",
    ),
    (
        "/data/BasisOfModelling/ModelPropertyFormulationMethods/0/ModelPropertyTypeID",
        f"{DATA_PARTITION_ID}:reference-data--FluidModelPropertyType:dummy:",
    ),
    (
        "/data/BasisOfModelling/ModelPropertyFormulationMethods/0/ModelPropertyFormulationMethodID",
        f"{DATA_PARTITION_ID}:reference-data--FluidModelPropertyFormulationMethod:dummy:",
    ),
    (
        "/data/BasisOfModelling/IntendedWorkflowUsageIDs/0",
        f"{DATA_PARTITION_ID}:reference-data--WorkflowUsageType:dummy:",
    ),
    (
        "/data/BasisOfModelling/BlackOilFlashMechanismAppliedID",
        f"{DATA_PARTITION_ID}:reference-data--BlackOilFlashMechanismApplied:dummy:",
    ),
]

INVALID_REGEX_FIELDS = [
    ("/data/FluidModelTypeID", f"{DATA_PARTITION_ID}:reference-data-FluidModelType:dummy:"),
    ("/data/ParentModelID", f"{DATA_PARTITION_ID}:work-product-component-FluidModel:dummy:"),
    ("/data/ModelAreaOfInterestIDs/0", f"{DATA_PARTITION_ID}:master-data-Reservoir:dummy:"),
    ("/data/FluidModelSaturationTypeID", f"{DATA_PARTITION_ID}:reference-data-FluidModelSaturationType:dummy:"),
    (
        "/data/BasisOfModelling/InputDataCollectionID",
        f"{DATA_PARTITION_ID}:work-product-component-PersistedCollection:dummy:",
    ),
    (
        "/data/BasisOfModelling/ModelPropertyFormulationMethods/0/ModelPropertyTypeID",
        f"{DATA_PARTITION_ID}:reference-data-FluidModelPropertyType:dummy:",
    ),
    (
        "/data/BasisOfModelling/ModelPropertyFormulationMethods/0/ModelPropertyFormulationMethodID",
        f"{DATA_PARTITION_ID}:reference-data-FluidModelPropertyFormulationMethod:dummy:",
    ),
    (
        "/data/BasisOfModelling/IntendedWorkflowUsageIDs/0",
        f"{DATA_PARTITION_ID}:reference-data-WorkflowUsageType:dummy:",
    ),
    (
        "/data/BasisOfModelling/BlackOilFlashMechanismAppliedID",
        f"{DATA_PARTITION_ID}:reference-data-BlackOilFlashMechanismApplied:dummy:",
    ),
]

GENERIC_EXTRA_FIELDS = [
    ("/acl/extraAcl", "extraAclValue"),
    ("/legal/extraLegal", "extraLegalValue"),
]


@pytest.mark.parametrize("field_path", GENERIC_MANDATORY_FIELDS)
def test_fluid_negative_create_record_missing_mandatory_generic_field(api, tests_data, helper, field_path):
    """Reject record creation with missing mandatory generic field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))
    helper.delete_by_path(data_payload, field_path)
    field_name = field_path.split("/")[-1]

    response = api.fluid_model.post_record(
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert f"{field_name} field required" in body["errors"]
    assert len(body["errors"]) == 1, f"Expected errors list length 1, got {len(body['errors'])}"


@pytest.mark.parametrize("field_path,value,error_message", GENERIC_INVALID_TYPE_FIELDS)
def test_fluid_negative_create_record_invalid_type_generic_field(
    api, tests_data, helper, field_path, value, error_message
):
    """Reject record creation with wrong type for generic field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))
    helper.set_by_path(data_payload, field_path, value)

    response = api.fluid_model.post_record(
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
def test_fluid_negative_create_record_invalid_type_specific_field(
    api, tests_data, helper, field_path, value, error_message
):
    """Reject record creation with wrong type for specific field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))
    helper.set_by_path(data_payload, field_path, value)

    response = api.fluid_model.post_record(
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
def test_fluid_negative_create_record_missing_reference_specific_field(api, tests_data, helper, field_path, value):
    """Reject record creation when referenced record doesn't exist with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))
    helper.set_by_path(data_payload, field_path, value)
    record_value = value.rsplit(":", 1)[0]

    response = api.fluid_model.post_record(
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
def test_fluid_negative_create_record_invalid_regex_specific_field(api, tests_data, helper, field_path, value):
    """Reject record creation when field doesn't match OSDU naming convention with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))
    helper.set_by_path(data_payload, field_path, value)

    response = api.fluid_model.post_record(
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
def test_fluid_negative_create_record_extra_field_generic(api, tests_data, helper, field_path, value):
    """Reject record creation with unexpected/extra fields with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))
    helper.set_by_path(data_payload, field_path, value)
    field_name = field_path.split("/")[-1]

    response = api.fluid_model.post_record(
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert f"{field_name} extra fields not permitted" in body["errors"]
    assert len(body["errors"]) == 1


def test_fluid_negative_create_unsupported_kind(api, tests_data, helper):
    """Reject record creation with unsupported kind value with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))
    unsupported_kind = f"{DATA_PARTITION_ID}:wks:work-product-component--Fluid:1.0.0"
    helper.set_by_path(data_payload, "/kind", unsupported_kind)

    response = api.fluid_model.post_record(
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert (
        f"Kind `{unsupported_kind}` not supported in RAFS-DDMS. Supported kinds for this endpoint: "
        f"['{DATA_PARTITION_ID}:wks:work-product-component--FluidModel']"
    ) in body["reason"]


def test_fluid_negative_create_unsupported_kind_version(api, tests_data, helper):
    """Reject record creation with unsupported kind version with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))
    unsupported_version = "1.7"
    unsupported_kind = f"{DATA_PARTITION_ID}:wks:work-product-component--FluidModel:{unsupported_version}"
    helper.set_by_path(data_payload, "/kind", unsupported_kind)

    response = api.fluid_model.post_record(
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


def test_fluid_negative_create_invalid_record_id(api, tests_data, helper):
    """Reject record creation with invalid record ID format with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))
    invalid_record_id = "WrongID:work-product-component--FluidModel:WrongID"
    helper.set_by_path(data_payload, "/id", invalid_record_id)

    response = api.fluid_model.post_record(
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
        f"Example: {DATA_PARTITION_ID}:work-product-component--FluidModel:<uuid>"
    ) in body["message"]


def test_fluid_negative_create_record_invalid_payload_format(api, tests_data):
    """Reject record creation when payload is not a list with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))

    response = api.fluid_model.post_record(
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert "body value is not a valid list" in body["errors"]
