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
    SamplesAnalysisEndpoints,
    SamplesAnalysisTypes,
)

DATA_PARTITION_ID = CONFIG["DATA_PARTITION"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_depth_shift_negative_invalid_depth_shift_policy(
    api, tests_data, endpoint, args, sample_analysis_record_id, sample_analysis_dataset_id, analysis_type
):
    """Reject invalid value for depth_shift_policy parameter with 400 Bad Request."""
    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    params = {
        "depth_shift_policy": "dummy",
    }

    kwargs = {
        "allowed_codes": [status.HTTP_400_BAD_REQUEST],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert "Invalid 'depth_shift_policy' value 'dummy'. Must be one of: ['definitive', 'id_provided']" in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_depth_shift_negative_invalid_depth_shift_id(
    api, tests_data, endpoint, args, sample_analysis_record_id, sample_analysis_dataset_id, analysis_type
):
    """Reject invalid value for depth_shift_id parameter with 400 Bad Request."""
    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    params = {
        "depth_shift_policy": "id_provided",
        "depth_shift_id": "dummy",
    }

    kwargs = {
        "allowed_codes": [status.HTTP_400_BAD_REQUEST],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert (
        "Invalid 'depth_shift_id' format. Expected pattern: "
        "^[\\w\\-\\.]+:work-product-component--DepthShift:[\\w\\-\\.\\:\\%]+$."
    ) in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_depth_shift_negative_missing_depth_shift_id(
    api, tests_data, endpoint, args, sample_analysis_record_id, sample_analysis_dataset_id, analysis_type
):
    """Reject missing depth_shift_id if depth_shift_policy is id_provided with 400 Bad Request."""
    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    params = {
        "depth_shift_policy": "id_provided",
    }

    kwargs = {
        "allowed_codes": [status.HTTP_400_BAD_REQUEST],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert "'depth_shift_policy=id_provided' requires 'depth_shift_id'." in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_depth_shift_negative_missing_depth_shift_policy(
    api, tests_data, endpoint, args, sample_analysis_record_id, sample_analysis_dataset_id, analysis_type
):
    """Reject missing depth_shift_policy if depth_shift_id is provided with 400 Bad Request."""
    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    params = {
        "depth_shift_id": "dummy",
    }

    kwargs = {
        "allowed_codes": [status.HTTP_400_BAD_REQUEST],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert "'depth_shift_id' requires 'depth_shift_policy=id_provided' to be explicit." in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_depth_shift_negative_definitive_depth_shift_policy_with_depth_shift_id(
    api, tests_data, endpoint, args, sample_analysis_record_id, sample_analysis_dataset_id, analysis_type
):
    """Reject definitive depth_shift_policy if depth_shift_id is also provided with 400 Bad Request."""
    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    params = {
        "depth_shift_policy": "definitive",
        "depth_shift_id": "dummy",
    }

    kwargs = {
        "allowed_codes": [status.HTTP_400_BAD_REQUEST],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert "'depth_shift_id' must not be supplied when 'depth_shift_policy=definitive'." in body["reason"]


def test_apply_depth_shift_negative_definitive_depth_shift_policy_without_definitive_shift_assigned(
    api, tests_data, sample_analysis_record_id, sample_analysis_dataset_id
):
    """Reject definitive depth_shift_policy if no definitive shift assigned to Sample with 422 Unprocessable Content."""

    params = {
        "depth_shift_policy": "definitive",
    }

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = api.sample_analysis.get_data(
        record_id=sample_analysis_record_id,
        dataset_id=sample_analysis_dataset_id,
        analysis_type=SamplesAnalysisTypes.NMR,
        params=params,
        **kwargs,
    )

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "No DefinitiveDepthShift found in any sample record." in body["reason"]


def test_apply_depth_shift_negative_search_without_wellbore_id(
    api, tests_data, sample_analysis_record_id, sample_analysis_dataset_id
):
    """Reject search request if depth shift requested but no wellbore_id provided with 422 Unprocessable Content."""

    params = {
        "depth_shift_policy": "definitive",
    }

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = api.sample_analysis.search_data(analysis_type=SamplesAnalysisTypes.NMR, params=params, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Depth shift requires a wellbore-scoped search. Please provide wellbore_id parameter." in body["reason"]


def test_apply_depth_shift_negative_search_with_invalid_wellbore_id(
    api, tests_data, sample_analysis_record_id, sample_analysis_dataset_id
):
    """Reject search request if depth shift requested but invalid wellbore_id provided with 422 Bad Request."""

    params = {
        "depth_shift_policy": "definitive",
        "wellbore_id": "dummy"
    }

    kwargs = {
        "allowed_codes": [status.HTTP_400_BAD_REQUEST],
        "raw": True,
    }

    response = api.sample_analysis.search_data(analysis_type=SamplesAnalysisTypes.NMR, params=params, **kwargs)

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert (
        "Invalid 'wellbore_id' format. Expected OSDU record ID matching "
        "^[\\w\\-\\.]+:master-data--Wellbore:[\\w\\-\\.\\:\\%]+$. Got: dummy"
    ) in body["reason"]
