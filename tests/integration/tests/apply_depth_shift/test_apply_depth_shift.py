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

from tests.integration.config import (
    CONFIG,
    DataFiles,
    SamplesAnalysisEndpoints,
)

DATA_PARTITION_ID = CONFIG["DATA_PARTITION"]


def _prepare_return_data_call(
    api,
    endpoint,
    args,
    create_apply_depth_shift_case,
    sample_definition=None,
):
    """Create an isolated case and prepare the parametrized endpoint call."""
    case = create_apply_depth_shift_case(
        sample_definition=sample_definition,
        wait_for_search=endpoint == "search_data",
    )
    call_values = {
        "record_id": case["sample_analysis_record_id"],
        "dataset_id": case["sample_analysis_dataset_id"],
        "analysis_type": case["analysis_type"],
    }
    method = getattr(api.sample_analysis, endpoint)
    return case, method, [call_values[name] for name in args]


def _expected_nmr_data(tests_data, case):
    expected_data = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1_RECORDS_FORMAT))
    expected_data["SamplesAnalysisID"] = f"{case['sample_analysis_record_id']}:"
    expected_data["SampleID"] = case["sample_value"]
    return expected_data


def _first_response_row(
    response,
    endpoint,
    params,
    case,
    requested_depth_shift_id=None,
):
    """Return the first row only after a contextual non-empty assertion."""
    response_key = "data" if endpoint == "get_data" else "result"
    assert response.get(response_key), (
        f"Expected {endpoint} to return the SamplesAnalysis row.\n"
        f"Rows filter: {params.get('rows_filter')}\n"
        f"Wellbore ID: {params.get('wellbore_id')}\n"
        f"Sample ID: {case['sample_id']}\n"
        f"Expected Sample version: {case['sample_version']}\n"
        f"Sample analysis ID: {case['sample_analysis_record_id']}\n"
        f"Requested depth-shift ID: {requested_depth_shift_id}\n"
        "Definitive depth-shift ID: "
        f"{case['definitive_depth_shift_id']}\n"
        f"Response: {response}"
    )
    assert response.get("DepthShiftData"), (
        "Expected the response to contain depth-shift data.\n"
        f"Endpoint: {endpoint}\n"
        f"Response: {response}"
    )
    assert response.get("DepthShiftMetadata") is not None, (
        "Expected the response to contain depth-shift metadata.\n"
        f"Endpoint: {endpoint}\n"
        f"Response: {response}"
    )
    return response[response_key][0]


@pytest.mark.parametrize(
    "endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS
)
def test_apply_id_provided_depth_shift_with_constant_offset(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    create_apply_depth_shift_case,
    add_search_scope,
):
    """Verify constant-offset depth shift when requested via user-provided depth_shift_id."""
    case, method, call_args = _prepare_return_data_call(
        api,
        endpoint,
        args,
        create_apply_depth_shift_case,
    )

    params = add_search_scope(
        {
            "orient": "records",
            "depth_shift_policy": "id_provided",
            "depth_shift_id": depth_shift_record_id,
        },
        endpoint,
        case,
    )

    response = method(*call_args, params=params)
    expected_data = _expected_nmr_data(tests_data, case)

    expected_depth_shift_data = {
        "SampleTop": 1002.0,
        "SampleBase": 1005.0,
        "ShiftedSampleTop": 1003.5,
        "ShiftedSampleBase": 1006.5,
        "DepthShiftWarnings": [],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "user-provided",
        "definitiveDepthShiftAvailable": False,
        "usedDefinitive": False,
        "warnings": [],
    }

    actual_data = _first_response_row(
        response,
        endpoint,
        params,
        case,
        requested_depth_shift_id=depth_shift_record_id,
    )
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(
        response["DepthShiftData"][0], expected_depth_shift_data
    )
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize(
    "endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS
)
def test_apply_definitive_depth_shift_with_constant_offset(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    create_apply_depth_shift_case,
    add_search_scope
):
    """Verify constant-offset depth shift when requested via definitive depth shift policy."""

    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    sample_definition["data"]["DefinitiveDepthShift"]["DefinitiveDepthShiftID"] = f"{depth_shift_record_id}:"

    case, method, call_args = _prepare_return_data_call(
        api,
        endpoint,
        args,
        create_apply_depth_shift_case,
        sample_definition,
    )

    params = add_search_scope(
        {
            "orient": "records",
            "depth_shift_policy": "definitive",
        },
        endpoint,
        case,
    )

    response = method(*call_args, params=params)
    expected_data = _expected_nmr_data(tests_data, case)

    expected_depth_shift_data = {
        "SampleTop": 1002.0,
        "SampleBase": 1005.0,
        "ShiftedSampleTop": 1003.5,
        "ShiftedSampleBase": 1006.5,
        "DepthShiftWarnings": [],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "definitive",
        "definitiveDepthShiftAvailable": True,
        "usedDefinitive": True,
        "warnings": [],
    }

    actual_data = _first_response_row(response, endpoint, params, case)
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(
        response["DepthShiftData"][0], expected_depth_shift_data
    )
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize(
    "endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS
)
def test_apply_id_provided_depth_shift_with_interpolation(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    create_depth_shift_dataset,
    create_apply_depth_shift_case,
    add_search_scope
):
    """Verify interpolated depth shift when requested via user-provided depth_shift_id."""

    # Update Depth Shift Set under Core To Log content data
    depth_shift_payload = copy.deepcopy(
        tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA_RECORDS_FORMAT)
    )
    depth_shift_payload["DepthShiftWPCID"] = f"{depth_shift_record_id}:"
    depth_shift_payload["DepthShiftSet"][0]["ShiftedBaseDepth"] = 1013.5
    create_depth_shift_dataset(depth_shift_record_id, [depth_shift_payload])

    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    sample_definition["data"]["DefinitiveDepthShift"]["DefinitiveDepthShiftID"] = f"{depth_shift_record_id}:"

    case, method, call_args = _prepare_return_data_call(
        api,
        endpoint,
        args,
        create_apply_depth_shift_case,
        sample_definition,
    )

    params = add_search_scope(
        {
            "orient": "records",
            "depth_shift_policy": "id_provided",
            "depth_shift_id": depth_shift_record_id,
        },
        endpoint,
        case,
    )

    response = method(*call_args, params=params)
    expected_data = _expected_nmr_data(tests_data, case)

    expected_depth_shift_data = {
        "SampleTop": 1002.0,
        "SampleBase": 1005.0,
        "ShiftedSampleTop": 1003.9,
        "ShiftedSampleBase": 1007.5,
        "DepthShiftWarnings": [],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "user-provided",
        "definitiveDepthShiftAvailable": True,
        "usedDefinitive": False,
        "warnings": [],
    }

    actual_data = _first_response_row(
        response,
        endpoint,
        params,
        case,
        requested_depth_shift_id=depth_shift_record_id,
    )
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(
        response["DepthShiftData"][0], expected_depth_shift_data
    )
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize(
    "endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS
)
def test_apply_definitive_depth_shift_with_interpolation(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    create_depth_shift_dataset,
    create_apply_depth_shift_case,
    add_search_scope
):
    """Verify interpolated depth shift when requested via definitive depth shift policy."""
    depth_shift_payload = copy.deepcopy(
        tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA_RECORDS_FORMAT)
    )
    depth_shift_payload["DepthShiftWPCID"] = f"{depth_shift_record_id}:"
    depth_shift_payload["DepthShiftSet"][0]["ShiftedBaseDepth"] = 1013.5
    create_depth_shift_dataset(depth_shift_record_id, [depth_shift_payload])

    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    sample_definition["data"]["DefinitiveDepthShift"]["DefinitiveDepthShiftID"] = f"{depth_shift_record_id}:"

    case, method, call_args = _prepare_return_data_call(
        api,
        endpoint,
        args,
        create_apply_depth_shift_case,
        sample_definition,
    )

    params = add_search_scope(
        {
            "orient": "records",
            "depth_shift_policy": "definitive",
        },
        endpoint,
        case,
    )

    response = method(*call_args, params=params)
    expected_data = _expected_nmr_data(tests_data, case)

    expected_depth_shift_data = {
        "SampleTop": 1002.0,
        "SampleBase": 1005.0,
        "ShiftedSampleTop": 1003.9,
        "ShiftedSampleBase": 1007.5,
        "DepthShiftWarnings": [],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "definitive",
        "definitiveDepthShiftAvailable": True,
        "usedDefinitive": True,
        "warnings": [],
    }

    actual_data = _first_response_row(response, endpoint, params, case)
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(
        response["DepthShiftData"][0], expected_depth_shift_data
    )
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize(
    "endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS
)
def test_apply_depth_shift_with_none_interpolation_method(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    create_depth_shift_dataset,
    create_apply_depth_shift_case,
    add_search_scope
):
    """Verify interpolated depth shift when interpolation method is None."""

    # Update Depth Shift Set under Core To Log content data
    depth_shift_payload = copy.deepcopy(
        tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA_RECORDS_FORMAT)
    )
    depth_shift_payload["DepthShiftWPCID"] = f"{depth_shift_record_id}:"
    interpolation_method = (
        f"{DATA_PARTITION_ID}:reference-data--DepthShiftInterpolationMethod:None:"
    )
    depth_shift_payload["DepthShiftSet"][0][
        "DepthShiftInterpolationMethodID"
    ] = interpolation_method
    depth_shift_payload["DepthShiftSet"][0]["ShiftedBaseDepth"] = 1013.5
    create_depth_shift_dataset(depth_shift_record_id, [depth_shift_payload])

    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    sample_definition["data"]["DefinitiveDepthShift"]["DefinitiveDepthShiftID"] = f"{depth_shift_record_id}:"

    case, method, call_args = _prepare_return_data_call(
        api,
        endpoint,
        args,
        create_apply_depth_shift_case,
        sample_definition,
    )

    params = add_search_scope(
        {
            "orient": "records",
            "depth_shift_policy": "id_provided",
            "depth_shift_id": depth_shift_record_id,
        },
        endpoint,
        case,
    )

    response = method(*call_args, params=params)
    expected_data = _expected_nmr_data(tests_data, case)

    expected_depth_shift_data = {
        "SampleTop": 1002.0,
        "SampleBase": 1005.0,
        "ShiftedSampleTop": 1003.9,
        "ShiftedSampleBase": 1007.5,
        "DepthShiftWarnings": [],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "user-provided",
        "definitiveDepthShiftAvailable": True,
        "usedDefinitive": False,
        "warnings": [],
    }

    actual_data = _first_response_row(
        response,
        endpoint,
        params,
        case,
        requested_depth_shift_id=depth_shift_record_id,
    )
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(
        response["DepthShiftData"][0], expected_depth_shift_data
    )
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize(
    "endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS
)
def test_apply_depth_shift_with_sample_top_below_all_intervals(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    create_apply_depth_shift_case,
    add_search_scope
):
    """Verify depth shift when Sample Top below all Depth Shift intervals."""

    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    sample_definition["data"]["DepthMeasurements"][0]["VerticalMeasurement"] = 998.0
    case, method, call_args = _prepare_return_data_call(
        api,
        endpoint,
        args,
        create_apply_depth_shift_case,
        sample_definition,
    )

    params = add_search_scope(
        {
            "orient": "records",
            "depth_shift_policy": "id_provided",
            "depth_shift_id": depth_shift_record_id,
        },
        endpoint,
        case,
    )

    response = method(*call_args, params=params)
    expected_data = _expected_nmr_data(tests_data, case)

    expected_depth_shift_data = {
        "SampleTop": 998.0,
        "SampleBase": 1005.0,
        "ShiftedSampleTop": 998.0,
        "ShiftedSampleBase": 1005.0,
        "DepthShiftWarnings": [
            "Sample not shifted: SampleTop 998.000 falls outside all shift intervals."
        ],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "user-provided",
        "definitiveDepthShiftAvailable": False,
        "usedDefinitive": False,
        "warnings": [],
    }

    actual_data = _first_response_row(
        response,
        endpoint,
        params,
        case,
        requested_depth_shift_id=depth_shift_record_id,
    )
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(
        response["DepthShiftData"][0], expected_depth_shift_data
    )
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize(
    "endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS
)
def test_apply_depth_shift_with_sample_top_interval_boundary(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    create_apply_depth_shift_case,
    add_search_scope
):
    """Verify depth shift when Sample Top falls exactly on the boundary between two Depth Shift intervals."""

    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    sample_definition["data"]["DepthMeasurements"][0]["VerticalMeasurement"] = 1010.0
    sample_definition["data"]["DepthMeasurements"][1]["VerticalMeasurement"] = 1014.0
    sample_definition["data"]["DefinitiveDepthShift"]["DefinitiveDepthShiftID"] = f"{depth_shift_record_id}:"

    case, method, call_args = _prepare_return_data_call(
        api,
        endpoint,
        args,
        create_apply_depth_shift_case,
        sample_definition,
    )

    params = add_search_scope(
        {
            "orient": "records",
            "depth_shift_policy": "definitive",
        },
        endpoint,
        case,
    )

    response = method(*call_args, params=params)
    expected_data = _expected_nmr_data(tests_data, case)

    expected_depth_shift_data = {
        "SampleTop": 1010,
        "SampleBase": 1014.0,
        "ShiftedSampleTop": 1012.5,
        "ShiftedSampleBase": 1016.5,
        "DepthShiftWarnings": [],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "definitive",
        "definitiveDepthShiftAvailable": True,
        "usedDefinitive": True,
        "warnings": [],
    }

    actual_data = _first_response_row(response, endpoint, params, case)
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(
        response["DepthShiftData"][0], expected_depth_shift_data
    )
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize(
    "endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS
)
def test_apply_depth_shift_with_sample_top_and_sample_in_different_intervals(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    create_depth_shift_dataset,
    create_apply_depth_shift_case,
    add_search_scope
):
    """Verify depth shift when Sample Top and Sample Base falls into different Depth Shift intervals."""

    depth_shift_payload = copy.deepcopy(
        tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA_RECORDS_FORMAT)
    )
    depth_shift_payload["DepthShiftSet"][0]["ShiftedBaseDepth"] = 1013.5
    create_depth_shift_dataset(depth_shift_record_id, [depth_shift_payload])

    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    sample_definition["data"]["DepthMeasurements"][0]["VerticalMeasurement"] = 1008.0
    sample_definition["data"]["DepthMeasurements"][1]["VerticalMeasurement"] = 1012.0
    case, method, call_args = _prepare_return_data_call(
        api,
        endpoint,
        args,
        create_apply_depth_shift_case,
        sample_definition,
    )

    params = add_search_scope(
        {
            "orient": "records",
            "depth_shift_policy": "id_provided",
            "depth_shift_id": depth_shift_record_id,
        },
        endpoint,
        case,
    )

    response = method(*call_args, params=params)
    expected_data = _expected_nmr_data(tests_data, case)

    expected_depth_shift_data = {
        "SampleTop": 1008.0,
        "SampleBase": 1012.0,
        "ShiftedSampleTop": 1011.1,
        "ShiftedSampleBase": 1015.9,
        "DepthShiftWarnings": [],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "user-provided",
        "definitiveDepthShiftAvailable": False,
        "usedDefinitive": False,
        "warnings": [],
    }

    actual_data = _first_response_row(
        response,
        endpoint,
        params,
        case,
        requested_depth_shift_id=depth_shift_record_id,
    )
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(
        response["DepthShiftData"][0], expected_depth_shift_data
    )
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize(
    "endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS
)
def test_apply_depth_shift_with_sample_top_in_gap_between_intervals(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    create_depth_shift_dataset,
    create_apply_depth_shift_case,
    add_search_scope
):
    """Verify depth shift when Sample Top falls into gap between Depth Shift intervals."""

    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    sample_definition["data"]["DepthMeasurements"][0]["VerticalMeasurement"] = 1015.0
    sample_definition["data"]["DepthMeasurements"][1]["VerticalMeasurement"] = 1022.0

    # Update Depth Shift Set under Core To Log content data
    depth_shift_payload = copy.deepcopy(
        tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA_RECORDS_FORMAT)
    )
    depth_shift_payload["DepthShiftWPCID"] = f"{depth_shift_record_id}:"
    depth_shift_payload["DepthShiftSet"][1]["OriginalTopDepth"] = 1020.0
    depth_shift_payload["DepthShiftSet"][1]["OriginalBaseDepth"] = 1030.0
    create_depth_shift_dataset(depth_shift_record_id, [depth_shift_payload])

    case, method, call_args = _prepare_return_data_call(
        api,
        endpoint,
        args,
        create_apply_depth_shift_case,
        sample_definition,
    )

    params = add_search_scope(
        {
            "orient": "records",
            "depth_shift_policy": "id_provided",
            "depth_shift_id": depth_shift_record_id,
        },
        endpoint,
        case,
    )

    response = method(*call_args, params=params)
    expected_data = _expected_nmr_data(tests_data, case)

    expected_depth_shift_data = {
        "SampleTop": 1015.0,
        "SampleBase": 1022.0,
        "ShiftedSampleTop": 1015.0,
        "ShiftedSampleBase": 1022.0,
        "DepthShiftWarnings": [
            "Sample not shifted: SampleTop 1015.000 falls outside all shift intervals."
        ],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "user-provided",
        "definitiveDepthShiftAvailable": False,
        "usedDefinitive": False,
        "warnings": [],
    }

    actual_data = _first_response_row(
        response,
        endpoint,
        params,
        case,
        requested_depth_shift_id=depth_shift_record_id,
    )
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(
        response["DepthShiftData"][0], expected_depth_shift_data
    )
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize(
    "endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS
)
def test_apply_depth_shift_with_measurement_source_not_driller(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    create_apply_depth_shift_case,
    add_search_scope
):
    """Verify depth shift when VerticalMeasurementSource is not Driller."""

    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    source_id = f"{DATA_PARTITION_ID}:reference-data--VerticalMeasurementSource:LOG:"
    sample_definition["data"]["DepthMeasurements"][0][
        "VerticalMeasurementSourceID"
    ] = source_id
    case, method, call_args = _prepare_return_data_call(
        api,
        endpoint,
        args,
        create_apply_depth_shift_case,
        sample_definition,
    )

    params = add_search_scope(
        {
            "orient": "records",
            "depth_shift_policy": "id_provided",
            "depth_shift_id": depth_shift_record_id,
        },
        endpoint,
        case,
    )

    response = method(*call_args, params=params)
    expected_data = _expected_nmr_data(tests_data, case)

    expected_depth_shift_data = {
        "SampleTop": 1002.0,
        "SampleBase": 1005.0,
        "ShiftedSampleTop": 1003.5,
        "ShiftedSampleBase": 1006.5,
        "DepthShiftWarnings": [
            "Warning: Sample depths (SampleTop, SampleBase, and/or SampleMean) are reported as 'LOG' depth and may not "
            "need to be shifted. Expected source is Driller (DRL). Shifted depths may need to be validated."
        ],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "user-provided",
        "definitiveDepthShiftAvailable": False,
        "usedDefinitive": False,
        "warnings": [],
    }

    actual_data = _first_response_row(
        response,
        endpoint,
        params,
        case,
        requested_depth_shift_id=depth_shift_record_id,
    )
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(
        response["DepthShiftData"][0], expected_depth_shift_data
    )
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize(
    "endpoint,args",
    SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS,
)
def test_apply_depth_shift_with_different_wellbore_ids(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    create_apply_depth_shift_case,
    add_search_scope
):
    """Verify depth shift when the Sample and Depth Shift WPC use different wellbores."""

    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    sample_wellbore_id = f"{DATA_PARTITION_ID}:master-data--Wellbore:TectonicDrift:"
    sample_definition["data"]["SampleAcquisition"]["SampleAcquisitionDetail"][
        "WellboreID"
    ] = sample_wellbore_id
    case, method, call_args = _prepare_return_data_call(
        api,
        endpoint,
        args,
        create_apply_depth_shift_case,
        sample_definition,
    )

    params = add_search_scope(
        {
            "orient": "records",
            "depth_shift_policy": "id_provided",
            "depth_shift_id": depth_shift_record_id,
        },
        endpoint,
        case,
    )

    response = method(*call_args, params=params)
    expected_data = _expected_nmr_data(tests_data, case)

    expected_depth_shift_data = {
        "SampleTop": 1002.0,
        "SampleBase": 1005.0,
        "ShiftedSampleTop": 1003.5,
        "ShiftedSampleBase": 1006.5,
        "DepthShiftWarnings": [
            (
                f"Wellbore mismatch: sample wellbore "
                f"'{sample_wellbore_id}' differs from depth-shift wellbore "
                f"'{DATA_PARTITION_ID}:master-data--Wellbore:MagmaPulse:'."
            )
        ],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "user-provided",
        "definitiveDepthShiftAvailable": False,
        "usedDefinitive": False,
        "warnings": [],
    }

    actual_data = _first_response_row(
        response,
        endpoint,
        params,
        case,
        requested_depth_shift_id=depth_shift_record_id,
    )

    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(
        response["DepthShiftData"][0],
        expected_depth_shift_data,
    )
    helper.compare_response_fields(
        response["DepthShiftMetadata"],
        expected_metadata,
    )


@pytest.mark.parametrize(
    "endpoint,args",
    SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS,
)
def test_apply_depth_shift_with_different_depth_shift_ids(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    fresh_depth_shift_record_id,
    fresh_depth_shift_dataset_id,
    create_apply_depth_shift_case,
    add_search_scope
):
    """Verify an explicitly provided depth shift is used when it differs from the definitive one."""

    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    sample_definition["data"]["DefinitiveDepthShift"]["DefinitiveDepthShiftID"] = f"{fresh_depth_shift_record_id}:"

    case, method, call_args = _prepare_return_data_call(
        api,
        endpoint,
        args,
        create_apply_depth_shift_case,
        sample_definition,
    )

    params = add_search_scope(
        {
            "orient": "records",
            "depth_shift_policy": "id_provided",
            "depth_shift_id": depth_shift_record_id,
        },
        endpoint,
        case,
    )

    response = method(*call_args, params=params)
    expected_data = _expected_nmr_data(tests_data, case)

    expected_depth_shift_data = {
        "SampleTop": 1002.0,
        "SampleBase": 1005.0,
        "ShiftedSampleTop": 1003.5,
        "ShiftedSampleBase": 1006.5,
        "DepthShiftWarnings": [],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "user-provided",
        "definitiveDepthShiftAvailable": True,
        "usedDefinitive": False,
        "warnings": [
            f"Sample references a definitive depth shift "
            f"({fresh_depth_shift_record_id}) that differs from the requested "
            f"depth_shift_id ({depth_shift_record_id}). RAFS applied the requested "
            f"depth_shift_id because depth_shift_policy=id_provided."
        ],
    }

    actual_data = _first_response_row(
        response,
        endpoint,
        params,
        case,
        requested_depth_shift_id=depth_shift_record_id,
    )

    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(
        response["DepthShiftData"][0],
        expected_depth_shift_data,
    )
    helper.compare_response_fields(
        response["DepthShiftMetadata"],
        expected_metadata,
    )


@pytest.mark.parametrize(
    "endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS
)
def test_apply_depth_shift_with_sample_top_only(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    create_apply_depth_shift_case,
    add_search_scope
):
    """Verify depth shift when there is only Sample Top defined and no Sample Base."""

    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    del sample_definition["data"]["DepthMeasurements"][1]
    case, method, call_args = _prepare_return_data_call(
        api,
        endpoint,
        args,
        create_apply_depth_shift_case,
        sample_definition,
    )
    params = add_search_scope(
        {
            "orient": "records",
            "depth_shift_policy": "id_provided",
            "depth_shift_id": depth_shift_record_id,
        },
        endpoint,
        case,
    )

    response = method(*call_args, params=params)
    expected_data = _expected_nmr_data(tests_data, case)

    expected_depth_shift_data = {
        "SampleTop": 1002.0,
        "SampleBase": None,
        "SampleMean": None,
        "ShiftedSampleTop": 1003.5,
        "ShiftedSampleBase": None,
        "ShiftedSampleMean": None,
        "DepthShiftWarnings": [],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "user-provided",
        "definitiveDepthShiftAvailable": False,
        "usedDefinitive": False,
        "warnings": [],
    }

    actual_data = _first_response_row(
        response,
        endpoint,
        params,
        case,
        requested_depth_shift_id=depth_shift_record_id,
    )
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(
        response["DepthShiftData"][0], expected_depth_shift_data
    )
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize(
    "endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS
)
def test_apply_depth_shift_with_sample_base_only(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    create_apply_depth_shift_case,
    add_search_scope
):
    """Verify depth shift when there is only Sample Base defined and no Sample Top."""

    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    del sample_definition["data"]["DepthMeasurements"][0]
    case, method, call_args = _prepare_return_data_call(
        api,
        endpoint,
        args,
        create_apply_depth_shift_case,
        sample_definition,
    )
    params = add_search_scope(
        {
            "orient": "records",
            "depth_shift_policy": "id_provided",
            "depth_shift_id": depth_shift_record_id,
        },
        endpoint,
        case,
    )

    response = method(*call_args, params=params)
    expected_data = _expected_nmr_data(tests_data, case)

    expected_depth_shift_data = {
        "SampleTop": None,
        "SampleBase": 1005.0,
        "SampleMean": None,
        "ShiftedSampleTop": None,
        "ShiftedSampleBase": 1006.5,
        "ShiftedSampleMean": None,
        "DepthShiftWarnings": [
            f"No SampleTop provided for {case['sample_id']}. "
            f"Sample has been shifted based on SampleBase depth."
        ],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "user-provided",
        "definitiveDepthShiftAvailable": False,
        "usedDefinitive": False,
        "warnings": [],
    }

    actual_data = _first_response_row(
        response,
        endpoint,
        params,
        case,
        requested_depth_shift_id=depth_shift_record_id,
    )
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(
        response["DepthShiftData"][0], expected_depth_shift_data
    )
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize(
    "endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS
)
def test_apply_depth_shift_with_sample_mean_only(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    create_apply_depth_shift_case,
    add_search_scope
):
    """Verify depth shift when there is only Sample Mean defined and no Sample Top and no Sample Base."""

    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    measurement_type = (
        f"{DATA_PARTITION_ID}:reference-data--VerticalMeasurementType:SampleMean:"
    )
    sample_definition["data"]["DepthMeasurements"][0][
        "VerticalMeasurementTypeID"
    ] = measurement_type
    del sample_definition["data"]["DepthMeasurements"][1]
    case, method, call_args = _prepare_return_data_call(
        api,
        endpoint,
        args,
        create_apply_depth_shift_case,
        sample_definition,
    )
    params = add_search_scope(
        {
            "orient": "records",
            "depth_shift_policy": "id_provided",
            "depth_shift_id": depth_shift_record_id,
        },
        endpoint,
        case,
    )

    response = method(*call_args, params=params)
    expected_data = _expected_nmr_data(tests_data, case)

    expected_depth_shift_data = {
        "SampleTop": None,
        "SampleBase": None,
        "SampleMean": 1002.0,
        "ShiftedSampleTop": None,
        "ShiftedSampleBase": None,
        "ShiftedSampleMean": 1003.5,
        "DepthShiftWarnings": [
            f"No SampleTop or SampleBase provided for {case['sample_id']}. "
            f"Sample has been shifted based on SampleMean depth."
        ],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "user-provided",
        "definitiveDepthShiftAvailable": False,
        "usedDefinitive": False,
        "warnings": [],
    }

    actual_data = _first_response_row(
        response,
        endpoint,
        params,
        case,
        requested_depth_shift_id=depth_shift_record_id,
    )
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(
        response["DepthShiftData"][0], expected_depth_shift_data
    )
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize(
    "endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS
)
def test_apply_depth_shift_with_sample_top_sample_mean_only(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    create_depth_shift_dataset,
    create_apply_depth_shift_case,
    add_search_scope
):
    """Verify depth shift when there is Sample Top and Sample Mean defined and no Sample Base."""

    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    measurement_type = (
        f"{DATA_PARTITION_ID}:reference-data--VerticalMeasurementType:SampleMean:"
    )
    sample_definition["data"]["DepthMeasurements"][1][
        "VerticalMeasurementTypeID"
    ] = measurement_type

    # Update Depth Shift Set under Core To Log content data
    depth_shift_payload = copy.deepcopy(
        tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA_RECORDS_FORMAT)
    )
    depth_shift_payload["DepthShiftWPCID"] = f"{depth_shift_record_id}:"
    depth_shift_payload["DepthShiftSet"][0]["ShiftedBaseDepth"] = 1013.5
    create_depth_shift_dataset(depth_shift_record_id, [depth_shift_payload])

    case, method, call_args = _prepare_return_data_call(
        api,
        endpoint,
        args,
        create_apply_depth_shift_case,
        sample_definition,
    )
    params = add_search_scope(
        {
            "orient": "records",
            "depth_shift_policy": "id_provided",
            "depth_shift_id": depth_shift_record_id,
        },
        endpoint,
        case,
    )

    response = method(*call_args, params=params)
    expected_data = _expected_nmr_data(tests_data, case)

    expected_depth_shift_data = {
        "SampleTop": 1002.0,
        "SampleBase": None,
        "SampleMean": 1005.0,
        "ShiftedSampleTop": 1003.9,
        "ShiftedSampleBase": None,
        "ShiftedSampleMean": 1007.5,
        "DepthShiftWarnings": [],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "user-provided",
        "definitiveDepthShiftAvailable": False,
        "usedDefinitive": False,
        "warnings": [],
    }

    actual_data = _first_response_row(
        response,
        endpoint,
        params,
        case,
        requested_depth_shift_id=depth_shift_record_id,
    )
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(
        response["DepthShiftData"][0], expected_depth_shift_data
    )
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize(
    "endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS
)
def test_apply_depth_shift_with_sample_base_sample_mean_only(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    create_apply_depth_shift_case,
    add_search_scope
):
    """Verify depth shift when there is Sample Base and Sample Mean defined and no Sample Top."""

    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    measurement_type = (
        f"{DATA_PARTITION_ID}:reference-data--VerticalMeasurementType:SampleMean:"
    )
    sample_definition["data"]["DepthMeasurements"][0][
        "VerticalMeasurementTypeID"
    ] = measurement_type
    sample_definition["data"]["DepthMeasurements"][0]["VerticalMeasurement"] = 1008.0
    sample_definition["data"]["DepthMeasurements"][1]["VerticalMeasurement"] = 1010.0
    case, method, call_args = _prepare_return_data_call(
        api,
        endpoint,
        args,
        create_apply_depth_shift_case,
        sample_definition,
    )
    params = add_search_scope(
        {
            "orient": "records",
            "depth_shift_policy": "id_provided",
            "depth_shift_id": depth_shift_record_id,
        },
        endpoint,
        case,
    )

    response = method(*call_args, params=params)
    expected_data = _expected_nmr_data(tests_data, case)

    expected_depth_shift_data = {
        "SampleTop": None,
        "SampleBase": 1010.0,
        "SampleMean": 1008.0,
        "ShiftedSampleTop": None,
        "ShiftedSampleBase": 1012.5,
        "ShiftedSampleMean": 1010.5,
        "DepthShiftWarnings": [
            f"No SampleTop provided for {case['sample_id']}. "
            f"Sample has been shifted based on SampleBase depth (SampleMean ignored)."
        ],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "user-provided",
        "definitiveDepthShiftAvailable": False,
        "usedDefinitive": False,
        "warnings": [],
    }

    actual_data = _first_response_row(
        response,
        endpoint,
        params,
        case,
        requested_depth_shift_id=depth_shift_record_id,
    )
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(
        response["DepthShiftData"][0], expected_depth_shift_data
    )
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize(
    "endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS
)
def test_apply_depth_shift_without_depth_measurements(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    create_depth_shift_dataset,
    create_apply_depth_shift_case,
    add_search_scope
):
    """Verify depth shift sourced from SampleAcquisitionDetail when there is no DepthMeasurements."""

    depth_shift_payload = copy.deepcopy(
        tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA_RECORDS_FORMAT)
    )
    depth_shift_payload["DepthShiftSet"][0]["ShiftedBaseDepth"] = 1013.5
    create_depth_shift_dataset(depth_shift_record_id, [depth_shift_payload])

    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    del sample_definition["data"]["DepthMeasurements"]
    case, method, call_args = _prepare_return_data_call(
        api,
        endpoint,
        args,
        create_apply_depth_shift_case,
        sample_definition,
    )
    params = add_search_scope(
        {
            "orient": "records",
            "depth_shift_policy": "id_provided",
            "depth_shift_id": depth_shift_record_id,
        },
        endpoint,
        case,
    )

    response = method(*call_args, params=params)
    expected_data = _expected_nmr_data(tests_data, case)

    expected_depth_shift_data = {
        "SampleTop": 1000.0,
        "SampleBase": 1020.0,
        "SampleMean": None,
        "ShiftedSampleTop": 1001.5,
        "ShiftedSampleBase": 1025.5,
        "ShiftedSampleMean": None,
        "DepthShiftWarnings": [
            "Sample depths sourced from SampleAcquisitionDetail (TopDepth/BaseDepth) because DepthMeasurements is "
            "absent or contains no recognizable depth entries."
        ],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "user-provided",
        "definitiveDepthShiftAvailable": False,
        "usedDefinitive": False,
        "warnings": [],
    }

    actual_data = _first_response_row(
        response,
        endpoint,
        params,
        case,
        requested_depth_shift_id=depth_shift_record_id,
    )
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(
        response["DepthShiftData"][0], expected_depth_shift_data
    )
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)
