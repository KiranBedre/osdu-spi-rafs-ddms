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
    ("/data/WellboreID", ["WellboreID"], "['WellboreID'] is not of type 'string'"),
    (
        "/data/VerticalReferenceRecordID",
        ["VerticalReferenceRecordID"],
        "['VerticalReferenceRecordID'] is not of type 'string'"
    ),
    (
        "/data/VerticalReferenceRecordCurveIDs",
        "VerticalReferenceRecordCurveIDs",
        "'VerticalReferenceRecordCurveIDs' is not of type 'array'"
    ),
    ("/data/DepthShiftTypeID", ["DepthShiftTypeID"], "['DepthShiftTypeID'] is not of type 'string'"),
    (
        "/data/ShiftedSamplingDomainTypeID",
        ["ShiftedSamplingDomainTypeID"],
        "['ShiftedSamplingDomainTypeID'] is not of type 'string'"
    ),
    ("/data/DepthShiftedSamples", "DepthShiftedSamples", "'DepthShiftedSamples' is not of type 'array'"),
    (
        "/data/DepthShiftedSamples/0/SampleID", ["SampleID"], "['SampleID'] is not of type 'string'"),
    (
        "/data/DepthShiftedSamples/0/CanDepthShiftBeAppliedToChildSamples",
        ["CanDepthShiftBeAppliedToChildSamples"],
        "['CanDepthShiftBeAppliedToChildSamples'] is not of type 'boolean'",
    ),
    (
        "/data/DepthShiftedSamples/0/CanDepthShiftBeAppliedToSiblingSamples",
        ["CanDepthShiftBeAppliedToSiblingSamples"],
        "['CanDepthShiftBeAppliedToSiblingSamples'] is not of type 'boolean'",
    ),
    ("/data/AuthorID", ["AuthorID"], "['AuthorID'] is not of type 'object'"),
    ("/data/AuthorID/Name", ["Name"], "['Name'] is not of type 'string'"),
    ("/data/AuthorID/RoleTypeID", ["RoleTypeID"], "['RoleTypeID'] is not of type 'string'"),
    ("/data/AuthorID/OrganisationID", ["OrganisationID"], "['OrganisationID'] is not of type 'string'"),
    ("/data/Remarks", "Remarks", "'Remarks' is not of type 'array'"),
]

SPECIFIC_MISSING_REFERENCE_FIELDS = [
    ("/data/WellboreID", f"{DATA_PARTITION_ID}:master-data--Wellbore:dummy:"),
    ("/data/VerticalReferenceRecordID", f"{DATA_PARTITION_ID}:work-product-component--WellboreMarkerSet:dummy:"),
    ("/data/DepthShiftTypeID", f"{DATA_PARTITION_ID}:reference-data--DepthShiftType:dummy:"),
    ("/data/ShiftedSamplingDomainTypeID", f"{DATA_PARTITION_ID}:reference-data--WellLogSamplingDomainType:dummy:"),
    ("/data/DepthShiftedSamples/0/SampleID", f"{DATA_PARTITION_ID}:master-data--Sample:dummy:"),
    (
        "/data/AuthorID/RoleTypeID",
        f"{DATA_PARTITION_ID}:reference-data--ContactRoleType:dummy:",
    ),
    (
        "/data/AuthorID/OrganisationID",
        f"{DATA_PARTITION_ID}:master-data--Organisation:dummy:",
    ),
]

INVALID_REGEX_FIELDS = [
    ("/data/WellboreID", f"{DATA_PARTITION_ID}:master-data-Wellbore:dummy:"),
    ("/data/VerticalReferenceRecordID", f"{DATA_PARTITION_ID}:work-product-component-WellboreMarkerSet:dummy:"),
    ("/data/DepthShiftTypeID", f"{DATA_PARTITION_ID}:reference-data-DepthShiftType:dummy:"),
    ("/data/ShiftedSamplingDomainTypeID", f"{DATA_PARTITION_ID}:reference-data-WellLogSamplingDomainType:dummy:"),
    ("/data/DepthShiftedSamples/0/SampleID", f"{DATA_PARTITION_ID}:master-data-Sample:dummy:"),
    (
        "/data/AuthorID/RoleTypeID",
        f"{DATA_PARTITION_ID}:reference-data-ContactRoleType:dummy:",
    ),
    (
        "/data/AuthorID/OrganisationID",
        f"{DATA_PARTITION_ID}:master-data-Organisation:dummy:",
    ),
]

GENERIC_EXTRA_FIELDS = [
    ("/acl/extraAcl", "extraAclValue"),
    ("/legal/extraLegal", "extraLegalValue"),
]


@pytest.mark.parametrize("field_path", GENERIC_MANDATORY_FIELDS)
def test_depth_shift_negative_create_record_missing_mandatory_generic_field(api, tests_data, helper, field_path):
    """Reject record creation with missing mandatory generic field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.DEPTH_SHIFT))
    helper.delete_by_path(data_payload, field_path)
    field_name = field_path.split("/")[-1]

    response = api.depth_shift.post_record(
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
def test_depth_shift_negative_create_record_invalid_type_generic_field(
    api, tests_data, helper, field_path, value, error_message
):
    """Reject record creation with wrong type for generic field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.DEPTH_SHIFT))
    helper.set_by_path(data_payload, field_path, value)

    response = api.depth_shift.post_record(
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
def test_depth_shift_negative_create_record_invalid_type_specific_field(
    api, tests_data, helper, field_path, value, error_message
):
    """Reject record creation with wrong type for specific field with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.DEPTH_SHIFT))
    helper.set_by_path(data_payload, field_path, value)

    response = api.depth_shift.post_record(
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
def test_depth_shift_negative_create_record_missing_reference_specific_field(api, tests_data, helper, field_path, value):
    """Reject record creation when referenced record doesn't exist with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.DEPTH_SHIFT))
    helper.set_by_path(data_payload, field_path, value)
    record_value = value.rsplit(":", 1)[0]

    response = api.depth_shift.post_record(
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
def test_depth_shift_negative_create_record_invalid_regex_specific_field(api, tests_data, helper, field_path, value):
    """Reject record creation when field doesn't match OSDU naming convention with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.DEPTH_SHIFT))
    helper.set_by_path(data_payload, field_path, value)

    response = api.depth_shift.post_record(
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
def test_depth_shift_negative_create_record_extra_field_generic(api, tests_data, helper, field_path, value):
    """Reject record creation with unexpected/extra fields with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.DEPTH_SHIFT))
    helper.set_by_path(data_payload, field_path, value)
    field_name = field_path.split("/")[-1]

    response = api.depth_shift.post_record(
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


def test_depth_shift_negative_create_unsupported_kind(api, tests_data, helper):
    """Reject record creation with unsupported kind value with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.DEPTH_SHIFT))
    unsupported_kind = f"{DATA_PARTITION_ID}:wks:work-product-component--DepthShiftModel:1.0.0"
    helper.set_by_path(data_payload, "/kind", unsupported_kind)

    response = api.depth_shift.post_record(
        body=[data_payload],
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert (
        f"Kind `{unsupported_kind}` not supported in RAFS-DDMS. Supported kinds for this endpoint: "
        f"['{DATA_PARTITION_ID}:wks:work-product-component--DepthShift:1.0.0']"
    ) in body["reason"]


def test_depth_shift_negative_create_invalid_record_id(api, tests_data, helper):
    """Reject record creation with invalid record ID format with 400 Bad Request."""
    data_payload = copy.deepcopy(tests_data(DataFiles.DEPTH_SHIFT))
    invalid_record_id = "WrongID:work-product-component--DepthShift:WrongID"
    helper.set_by_path(data_payload, "/id", invalid_record_id)

    response = api.depth_shift.post_record(
        body=[data_payload],
        allowed_codes=[status.HTTP_400_BAD_REQUEST],
        raw=True,
    )

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert "Invalid record id" in body["reason"]
    assert (
        f"The record '{invalid_record_id}' does not follow the naming convention: "
        f"The record id must be in the format of <tenantId>:<kindSubType>:<uniqueId>. "
        f"Example: {DATA_PARTITION_ID}:work-product-component--DepthShift:<uuid>"
    ) in body["message"]


def test_depth_shift_negative_create_record_invalid_payload_format(api, tests_data):
    """Reject record creation when payload is not a list with 422 Unprocessable Content."""
    data_payload = copy.deepcopy(tests_data(DataFiles.DEPTH_SHIFT))

    response = api.depth_shift.post_record(
        body=data_payload,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_CONTENT],
        raw=True,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert "body value is not a valid list" in body["errors"]
