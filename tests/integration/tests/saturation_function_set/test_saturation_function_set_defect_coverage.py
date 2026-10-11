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

import pytest
from starlette import status

from app.resources.common_headers import CACHE_CONTROL
from tests.integration.config import (
    CONFIG,
    SCHEMA_AUTHORITY,
    DataFiles,
    Endpoints,
)

DATA_PARTITION_ID = CONFIG["DATA_PARTITION"]


@pytest.mark.parametrize("endpoint,args", Endpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_sfs_max_age_cache_header(api, endpoint, args, fresh_record_id, fresh_dataset_id):
    """Verify that endpoint returns expected status codes for max-age Cache Control header"""
    record_id = fresh_record_id
    dataset_id = fresh_dataset_id
    method = getattr(api.saturation_function_set, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "headers": {CACHE_CONTROL: "max-age=120"},
        "raw": True,
    }

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 200


@pytest.mark.parametrize("endpoint,args", Endpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_sfs_max_stale_cache_header(api, endpoint, args, fresh_record_id, fresh_dataset_id):
    """Verify that endpoint returns expected status codes for max-stale Cache Control header"""
    record_id = fresh_record_id
    dataset_id = fresh_dataset_id
    method = getattr(api.saturation_function_set, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "headers": {CACHE_CONTROL: "max-stale"},
        "raw": True,
    }

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 200


@pytest.mark.parametrize("endpoint,args", Endpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_sfs_private_cache_header(api, endpoint, args, fresh_record_id, fresh_dataset_id):
    """Verify that endpoint returns expected status codes for private Cache Control header"""
    record_id = fresh_record_id
    dataset_id = fresh_dataset_id
    method = getattr(api.saturation_function_set, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "headers": {CACHE_CONTROL: "private"},
        "raw": True,
    }

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 200


@pytest.mark.parametrize("endpoint,args", Endpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_sfs_public_cache_header(api, endpoint, args, fresh_record_id, fresh_dataset_id):
    """Verify that endpoint returns expected status codes for public Cache Control header"""
    record_id = fresh_record_id
    dataset_id = fresh_dataset_id
    method = getattr(api.saturation_function_set, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "headers": {CACHE_CONTROL: "public"},
        "raw": True,
    }

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 200


@pytest.mark.parametrize("endpoint,args", Endpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_sfs_immutable_cache_header(api, endpoint, args, fresh_record_id, fresh_dataset_id):
    """Verify that endpoint returns expected status codes for immutable Cache Control header"""
    record_id = fresh_record_id
    dataset_id = fresh_dataset_id
    method = getattr(api.saturation_function_set, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "headers": {CACHE_CONTROL: "immutable"},
        "raw": True,
    }

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 200


def test_sfs_create_record_with_special_characters_in_record_id(api, helper, tests_data, spec_char_record_id):
    """Verify record creation with special characters can be retrieved unchanged via GET."""
    # Record creation
    create_record_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET))
    create_record_payload["id"] = spec_char_record_id
    api.saturation_function_set.post_record(body=[create_record_payload])

    # Retrieve the record by id
    encoded_record_id = urllib.parse.quote(spec_char_record_id)
    gotten_record = api.saturation_function_set.get_record(encoded_record_id)

    # Response should contain the same business fields as the original POST body
    helper.compare_responses(gotten_record, create_record_payload, response_type="json")


def test_sfs_versions_with_special_characters_in_record_id(api, helper, spec_char_record_id):
    """Verify record versioning with special characters in record_id"""
    encoded_record_id = urllib.parse.quote(spec_char_record_id)
    version_1 = api.saturation_function_set.get_record(encoded_record_id)

    # Create a second version by modifying the Name field
    version_2 = copy.deepcopy(version_1)
    version_2["data"]["Name"] = version_2["data"]["Name"] + " - new version"
    api.saturation_function_set.post_record([version_2])

    # List versions and ensure two versions exist
    versions_payload = api.saturation_function_set.get_record_versions(encoded_record_id)
    assert "versions" in versions_payload
    assert len(versions_payload["versions"]) == 2

    v1_version, v2_version = sorted(versions_payload["versions"])

    # Fetch concrete versions and compare with expected payloads
    rec_v1 = api.saturation_function_set.get_record_version(encoded_record_id, v1_version)
    rec_v2 = api.saturation_function_set.get_record_version(encoded_record_id, v2_version)

    helper.compare_responses(rec_v1, version_1, response_type="json")
    helper.compare_responses(rec_v2, version_2, response_type="json")
    assert rec_v2["data"]["Name"].endswith(" - new version")

    # Plain GET should return the latest version
    latest = api.saturation_function_set.get_record(encoded_record_id)
    helper.compare_responses(latest, version_2, response_type="json")


def test_sfs_add_data_with_special_characters_in_record_id(api, helper, tests_data, spec_char_record_id):
    """Upload bulk data and verify retrieval in JSON for record_id with special characters."""
    # Prepare and upload dataset payload
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET_DATA_V1))
    data_payload["data"][0][0] = f"{spec_char_record_id}:"
    encoded_record_id = urllib.parse.quote(spec_char_record_id)
    post_response = api.saturation_function_set.post_data(encoded_record_id, data_payload)
    dataset_id = helper.get_content_id_from_ddms_urn(post_response["ddms_urn"])

    # GET data as JSON and compare with original payload
    gotten_data = api.saturation_function_set.get_data(encoded_record_id, dataset_id)
    helper.compare_responses(gotten_data, data_payload, response_type="json")


def test_sfs_delete_record_special_characters_in_record_id(api, spec_char_record_id):
    """Delete record with special characters in record_id."""
    # Prepare and delete record
    encoded_record_id = urllib.parse.quote(spec_char_record_id)
    kwargs = {
        "allowed_codes": [status.HTTP_204_NO_CONTENT],
        "raw": True,
    }

    api.saturation_function_set.soft_delete_record(encoded_record_id, **kwargs)


def test_sfs_create_record_with_kind_matching_semantic_version(api, helper, tests_data, delete_record):
    """Verify record creation with kind matching only semantic version can be retrieved unchanged via GET."""
    # Record creation
    data_payload = copy.deepcopy(tests_data(DataFiles.SATURATION_FUNCTION_SET))
    data_payload["kind"] = f"{SCHEMA_AUTHORITY}:wks:work-product-component--SaturationFunctionSet:5.23.72"
    response = api.saturation_function_set.post_record(body=[data_payload])
    record_id = response["recordIdVersions"][0].rsplit(":", 1)[0]

    # Register record for cleanup
    delete_record(record_id)

    # Retrieve the record by id and prepare baseline
    data_payload["id"] = record_id
    gotten_record = api.saturation_function_set.get_record(record_id)

    # Response should contain the same business fields as the original POST body
    helper.compare_responses(gotten_record, data_payload, response_type="json")
