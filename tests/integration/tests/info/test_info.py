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

INFO_FIELDS = (
    "name",
    "app_version",
    "build_time",
    "branch",
    "commit_id",
    "commit_message",
    "release_version",
)


def test_info_endpoint_returns_all_fields(api):
    """Verify /info returns a response with all required fields present and non-empty."""
    info = api.app_info.get_info()

    # Assert
    for field in INFO_FIELDS:
        assert field in info, f"Missing field {field!r} in /info response"
        assert info[field], f"Expected non-empty value for {field!r} in /info response"


def test_info_endpoint_name_mentions_service(api):
    """Verify /info returns the correct service name.

    The configured app_name is "Rock and Fluid Sample DDMS" (app/core/settings/app.py),
    not a literal "RAFS" acronym, so check for the words it's actually built from.
    """
    info = api.app_info.get_info()

    # Assert
    name = info["name"].lower()
    assert "rock" in name
    assert "fluid" in name
    assert "sample" in name


def test_info_endpoint_commit_id_is_hex(api):
    """Verify commit_id looks like a git SHA (hex characters, at least 7 chars)."""
    info = api.app_info.get_info()
    commit_id = info["commit_id"]

    # Assert
    assert len(commit_id) >= 7
    assert all(
        c in "0123456789abcdefABCDEF" for c in commit_id
    ), f"commit_id {commit_id!r} does not look like a git SHA"
