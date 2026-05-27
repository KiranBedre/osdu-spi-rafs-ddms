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
import urllib.parse

from starlette import status

from tests.integration.config import (
    DataFiles,
)


def test_fluid_create_record_with_special_characters_in_record_id(api, helper, tests_data, spec_char_record_id):
    """Verify record creation with special characters can be retrieved unchanged via GET."""
    # Record creation
    create_record_payload = copy.deepcopy(tests_data(DataFiles.FLUID_MODEL))
    create_record_payload["id"] = spec_char_record_id
    api.fluid_model.post_record(body=[create_record_payload])

    # Retrieve the record by id
    encoded_record_id = urllib.parse.quote(spec_char_record_id)
    gotten_record = api.fluid_model.get_record(encoded_record_id)

    # Response should contain the same business fields as the original POST body
    helper.compare_responses(gotten_record, create_record_payload, response_type="json")


def test_fluid_versions_with_special_characters_in_record_id(api, helper, spec_char_record_id):
    """Verify record versioning with special characters in record_id"""
    encoded_record_id = urllib.parse.quote(spec_char_record_id)
    version_1 = api.fluid_model.get_record(encoded_record_id)

    # Create a second version by modifying the Name field
    version_2 = copy.deepcopy(version_1)
    version_2["data"]["Name"] = "New version"
    api.fluid_model.post_record([version_2])

    # List versions and ensure two versions exist
    versions_payload = api.fluid_model.get_record_versions(encoded_record_id)
    assert "versions" in versions_payload
    assert len(versions_payload["versions"]) == 2

    v1_version, v2_version = sorted(versions_payload["versions"])

    # Fetch concrete versions and compare with expected payloads
    rec_v1 = api.fluid_model.get_record_version(encoded_record_id, v1_version)
    rec_v2 = api.fluid_model.get_record_version(encoded_record_id, v2_version)

    helper.compare_responses(rec_v1, version_1, response_type="json")
    helper.compare_responses(rec_v2, version_2, response_type="json")
    assert rec_v2["data"]["Name"] == "New version"

    # Plain GET should return the latest version
    latest = api.fluid_model.get_record(encoded_record_id)
    helper.compare_responses(latest, version_2, response_type="json")


def test_fluid_delete_record_special_characters_in_record_id(api, spec_char_record_id):
    """Delete record with special characters in record_id."""
    # Prepare and delete record
    encoded_record_id = urllib.parse.quote(spec_char_record_id)
    kwargs = {
        "allowed_codes": [status.HTTP_204_NO_CONTENT],
        "raw": True,
    }

    api.fluid_model.soft_delete_record(encoded_record_id, **kwargs)
