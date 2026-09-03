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

from starlette import status

from tests.integration.config import DataFiles

# Required fields in OsduStorageRecord with no default value.
_REQUIRED_RECORD_FIELDS = ("kind", "acl", "legal", "data")


def test_post_record_missing_required_fields_returns_422_with_string_errors(api):
    """Missing required OSDU record fields produce a 422 with human-readable string errors.

    Sending an empty dict as the record body triggers FastAPI/pydantic validation
    for each required field in OsduStorageRecord (kind, acl, legal, data), which
    reaches http422_error_handler via RequestValidationError.

    The regression guard is that 'errors' is a list of strings, not raw pydantic
    validation dicts. This test passes on both ci/integration (pydantic v1) and
    feature/pydantic-v2-migration (pydantic v2), documenting the behavioral contract
    that format_errors() must normalise validation errors into human-readable strings
    regardless of which pydantic version produces them.

    Note: the formatted error text changes between branches —
      pydantic v1: "kind field required"
      pydantic v2: "kind Field required"
    The assertion uses a case-insensitive check to document this known difference
    without making the test branch-specific.
    """
    response = api.sample_analysis.post_record(
        body=[{}],
        raw=True,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_ENTITY],
    )

    assert response.status_code == 422
    body = response.json()
    assert body.get("reason") == "Unprocessable entity."

    errors = body.get("errors")
    assert isinstance(errors, list), f"'errors' must be a list, got {type(errors)}"
    assert len(errors) > 0, "Expected at least one validation error"
    assert all(
        isinstance(e, str) for e in errors
    ), f"Each error must be a human-readable string, not a dict. Got: {errors}"

    # Each missing required field should appear by name in the errors list.
    for field in _REQUIRED_RECORD_FIELDS:
        assert any(field in e for e in errors), f"Expected field '{field}' to appear in errors. Got: {errors}"

    # "required" must appear in every error (case-insensitive).
    # pydantic v1 produces "field required"; pydantic v2 produces "Field required".
    assert all(
        "required" in e.lower() for e in errors
    ), f"Expected 'required' (case-insensitive) in every error. Got: {errors}"


def test_post_record_missing_kind_field_returns_422_mentioning_field(api, tests_data):
    """A record with only the 'kind' field missing produces a focused 422 error.

    This narrows the assertion to a single missing field so the test is easier
    to read as documentation. The same case-insensitive 'required' check applies.
    """
    record = copy.deepcopy(tests_data(DataFiles.SAMPLE_ANALYSIS))
    record.pop("kind", None)

    response = api.sample_analysis.post_record(
        body=[record],
        raw=True,
        allowed_codes=[status.HTTP_422_UNPROCESSABLE_ENTITY],
    )

    assert response.status_code == 422
    body = response.json()
    assert body.get("reason") == "Unprocessable entity."

    errors = body.get("errors")
    assert isinstance(errors, list)
    assert all(isinstance(e, str) for e in errors), f"Each error must be a human-readable string. Got: {errors}"
    assert any("kind" in e for e in errors), f"Expected 'kind' to appear in errors. Got: {errors}"
    assert all("required" in e.lower() for e in errors)
