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


def test_fluid_create_record(api, fluid_create_record, helper):
    """Verify created record can be retrieved unchanged via GET."""
    posted_record = fluid_create_record

    # Retrieve the record by id
    gotten_record = api.fluid_model.get_record(posted_record["id"])

    # Response should contain the same business fields as the original POST body
    helper.compare_responses(gotten_record, posted_record, response_type="json")


def test_fluid_versions(api, record_id, helper):
    """Verify record versioning: create v2, list versions, compare v1 and v2, confirm latest version."""
    version_1 = api.fluid_model.get_record(record_id)

    # Create a second version by modifying the Name field
    version_2 = copy.deepcopy(version_1)
    version_2["data"]["Name"] = "New version"
    api.fluid_model.post_record([version_2])

    # List versions and ensure two versions exist
    versions_payload = api.fluid_model.get_record_versions(record_id)
    assert "versions" in versions_payload
    assert len(versions_payload["versions"]) == 2

    v1_version, v2_version = sorted(versions_payload["versions"])

    # Fetch concrete versions and compare with expected payloads
    rec_v1 = api.fluid_model.get_record_version(record_id, v1_version)
    rec_v2 = api.fluid_model.get_record_version(record_id, v2_version)

    helper.compare_responses(rec_v1, version_1, response_type="json")
    helper.compare_responses(rec_v2, version_2, response_type="json")
    assert rec_v2["data"]["Name"] == "New version"

    # Plain GET should return the latest version
    latest = api.fluid_model.get_record(record_id)
    helper.compare_responses(latest, version_2, response_type="json")
