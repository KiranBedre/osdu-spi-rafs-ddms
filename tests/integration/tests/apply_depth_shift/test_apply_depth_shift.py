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


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_id_provided_depth_shift_with_constant_offset(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    sample_analysis_record_id,
    sample_analysis_dataset_id,
    analysis_type,
    search_available,
):
    """Verify constant-offset depth shift when requested via user-provided depth_shift_id."""
    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {
        "orient": "records",
        "depth_shift_policy": "id_provided",
        "depth_shift_id": depth_shift_record_id,
    }
    if endpoint == "search_data":
        params["wellbore_id"] = f"{DATA_PARTITION_ID}:master-data--Wellbore:MagmaPulse:"
        params["rows_filter"] = f"SamplesAnalysisID,eq,{sample_analysis_record_id}:"

    response = method(*call_args, params=params)

    expected_data = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1_RECORDS_FORMAT))
    expected_data["SamplesAnalysisID"] = f"{sample_analysis_record_id}:"

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

    # Assert
    actual_data = response["data"][0] if endpoint == "get_data" else response["result"][0]
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(response["DepthShiftData"][0], expected_depth_shift_data)
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_definitive_depth_shift_with_constant_offset(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    sample_analysis_record_id,
    sample_analysis_dataset_id,
    analysis_type,
):
    """Verify constant-offset depth shift when requested via definitive depth shift policy."""

    # Update sample definition with definitive depth shift id
    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    sample_definition["data"]["DefinitiveDepthShift"]["DefinitiveDepthShiftID"] = depth_shift_record_id
    api.storage.create_or_update_records([sample_definition])

    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {
        "orient": "records",
        "depth_shift_policy": "definitive",
    }
    if endpoint == "search_data":
        params["wellbore_id"] = f"{DATA_PARTITION_ID}:master-data--Wellbore:MagmaPulse:"
        params["rows_filter"] = f"SamplesAnalysisID,eq,{sample_analysis_record_id}:"

    response = method(*call_args, params=params)

    expected_data = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1_RECORDS_FORMAT))
    expected_data["SamplesAnalysisID"] = f"{sample_analysis_record_id}:"

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

    # Assert
    actual_data = response["data"][0] if endpoint == "get_data" else response["result"][0]
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(response["DepthShiftData"][0], expected_depth_shift_data)
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_id_provided_depth_shift_with_interpolation(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    sample_analysis_record_id,
    sample_analysis_dataset_id,
    analysis_type,
):
    """Verify interpolated depth shift when requested via user-provided depth_shift_id."""

    # Update Depth Shift Set under Core To Log content data
    depth_shift_payload = copy.deepcopy(tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA_RECORDS_FORMAT))
    depth_shift_payload["DepthShiftWPCID"] = f"{depth_shift_record_id}:"
    depth_shift_payload["DepthShiftSet"][0]["ShiftedBaseDepth"] = 1013.5
    api.depth_shift.post_data(depth_shift_record_id, [depth_shift_payload])

    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {
        "orient": "records",
        "depth_shift_policy": "id_provided",
        "depth_shift_id": depth_shift_record_id,
    }
    if endpoint == "search_data":
        params["wellbore_id"] = f"{DATA_PARTITION_ID}:master-data--Wellbore:MagmaPulse:"
        params["rows_filter"] = f"SamplesAnalysisID,eq,{sample_analysis_record_id}:"

    response = method(*call_args, params=params)

    expected_data = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1_RECORDS_FORMAT))
    expected_data["SamplesAnalysisID"] = f"{sample_analysis_record_id}:"

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

    # Assert
    actual_data = response["data"][0] if endpoint == "get_data" else response["result"][0]
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(response["DepthShiftData"][0], expected_depth_shift_data)
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_definitive_depth_shift_with_interpolation(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    sample_analysis_record_id,
    sample_analysis_dataset_id,
    analysis_type,
):
    """Verify interpolated depth shift when requested via definitive depth shift policy."""
    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {
        "orient": "records",
        "depth_shift_policy": "definitive",
    }
    if endpoint == "search_data":
        params["wellbore_id"] = f"{DATA_PARTITION_ID}:master-data--Wellbore:MagmaPulse:"
        params["rows_filter"] = f"SamplesAnalysisID,eq,{sample_analysis_record_id}:"

    response = method(*call_args, params=params)

    expected_data = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1_RECORDS_FORMAT))
    expected_data["SamplesAnalysisID"] = f"{sample_analysis_record_id}:"

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

    # Assert
    actual_data = response["data"][0] if endpoint == "get_data" else response["result"][0]
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(response["DepthShiftData"][0], expected_depth_shift_data)
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_depth_shift_with_none_interpolation_method(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    sample_analysis_record_id,
    sample_analysis_dataset_id,
    analysis_type,
):
    """Verify interpolated depth shift when interpolation method is None."""

    # Update Depth Shift Set under Core To Log content data
    depth_shift_payload = copy.deepcopy(tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA_RECORDS_FORMAT))
    depth_shift_payload["DepthShiftWPCID"] = f"{depth_shift_record_id}:"
    interpolation_method = f"{DATA_PARTITION_ID}:reference-data--DepthShiftInterpolationMethod:None:"
    depth_shift_payload["DepthShiftSet"][0]["DepthShiftInterpolationMethodID"] = interpolation_method
    depth_shift_payload["DepthShiftSet"][0]["ShiftedBaseDepth"] = 1013.5
    api.depth_shift.post_data(depth_shift_record_id, [depth_shift_payload])

    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {
        "orient": "records",
        "depth_shift_policy": "id_provided",
        "depth_shift_id": depth_shift_record_id,
    }
    if endpoint == "search_data":
        params["wellbore_id"] = f"{DATA_PARTITION_ID}:master-data--Wellbore:MagmaPulse:"
        params["rows_filter"] = f"SamplesAnalysisID,eq,{sample_analysis_record_id}:"

    response = method(*call_args, params=params)

    expected_data = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1_RECORDS_FORMAT))
    expected_data["SamplesAnalysisID"] = f"{sample_analysis_record_id}:"

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

    # Assert
    actual_data = response["data"][0] if endpoint == "get_data" else response["result"][0]
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(response["DepthShiftData"][0], expected_depth_shift_data)
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_depth_shift_with_sample_top_below_all_intervals(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    sample_analysis_record_id,
    sample_analysis_dataset_id,
    analysis_type,
):
    """Verify depth shift when Sample Top below all Depth Shift intervals."""

    # Update sample definition
    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    sample_definition["data"]["DepthMeasurements"][0]["VerticalMeasurement"] = 998.0
    api.storage.create_or_update_records([sample_definition])

    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {
        "orient": "records",
        "depth_shift_policy": "id_provided",
        "depth_shift_id": depth_shift_record_id,
    }
    if endpoint == "search_data":
        params["wellbore_id"] = f"{DATA_PARTITION_ID}:master-data--Wellbore:MagmaPulse:"
        params["rows_filter"] = f"SamplesAnalysisID,eq,{sample_analysis_record_id}:"

    response = method(*call_args, params=params)

    expected_data = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1_RECORDS_FORMAT))
    expected_data["SamplesAnalysisID"] = f"{sample_analysis_record_id}:"

    expected_depth_shift_data = {
        "SampleTop": 998.0,
        "SampleBase": 1005.0,
        "ShiftedSampleTop": 998.0,
        "ShiftedSampleBase": 1005.0,
        "DepthShiftWarnings": ["Sample not shifted: SampleTop 998.000 falls outside all shift intervals."],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "user-provided",
        "definitiveDepthShiftAvailable": False,
        "usedDefinitive": False,
        "warnings": [],
    }

    # Assert
    actual_data = response["data"][0] if endpoint == "get_data" else response["result"][0]
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(response["DepthShiftData"][0], expected_depth_shift_data)
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_depth_shift_with_sample_top_interval_boundary(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    sample_analysis_record_id,
    sample_analysis_dataset_id,
    analysis_type,
):
    """Verify depth shift when Sample Top falls exactly on the boundary between two Depth Shift intervals."""

    # Update sample definition
    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    sample_definition["data"]["DepthMeasurements"][0]["VerticalMeasurement"] = 1010.0
    sample_definition["data"]["DepthMeasurements"][1]["VerticalMeasurement"] = 1014.0
    sample_definition["data"]["DefinitiveDepthShift"]["DefinitiveDepthShiftID"] = depth_shift_record_id
    api.storage.create_or_update_records([sample_definition])

    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {
        "orient": "records",
        "depth_shift_policy": "definitive",
    }
    if endpoint == "search_data":
        params["wellbore_id"] = f"{DATA_PARTITION_ID}:master-data--Wellbore:MagmaPulse:"
        params["rows_filter"] = f"SamplesAnalysisID,eq,{sample_analysis_record_id}:"

    response = method(*call_args, params=params)

    expected_data = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1_RECORDS_FORMAT))
    expected_data["SamplesAnalysisID"] = f"{sample_analysis_record_id}:"

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

    # Assert
    actual_data = response["data"][0] if endpoint == "get_data" else response["result"][0]
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(response["DepthShiftData"][0], expected_depth_shift_data)
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_depth_shift_with_sample_top_and_sample_in_different_intervals(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    sample_analysis_record_id,
    sample_analysis_dataset_id,
    analysis_type,
):
    """Verify depth shift when Sample Top and Sample Base falls into different Depth Shift intervals."""

    # Update sample definition
    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    sample_definition["data"]["DepthMeasurements"][0]["VerticalMeasurement"] = 1008.0
    sample_definition["data"]["DepthMeasurements"][1]["VerticalMeasurement"] = 1012.0
    api.storage.create_or_update_records([sample_definition])

    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {
        "orient": "records",
        "depth_shift_policy": "id_provided",
        "depth_shift_id": depth_shift_record_id,
    }
    if endpoint == "search_data":
        params["wellbore_id"] = f"{DATA_PARTITION_ID}:master-data--Wellbore:MagmaPulse:"
        params["rows_filter"] = f"SamplesAnalysisID,eq,{sample_analysis_record_id}:"

    response = method(*call_args, params=params)

    expected_data = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1_RECORDS_FORMAT))
    expected_data["SamplesAnalysisID"] = f"{sample_analysis_record_id}:"

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

    # Assert
    actual_data = response["data"][0] if endpoint == "get_data" else response["result"][0]
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(response["DepthShiftData"][0], expected_depth_shift_data)
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_depth_shift_with_sample_top_in_gap_between_intervals(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    sample_analysis_record_id,
    sample_analysis_dataset_id,
    analysis_type,
):
    """Verify depth shift when Sample Top falls into gap between Depth Shift intervals."""

    # Update sample definition
    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    sample_definition["data"]["DepthMeasurements"][0]["VerticalMeasurement"] = 1015.0
    sample_definition["data"]["DepthMeasurements"][1]["VerticalMeasurement"] = 1022.0
    api.storage.create_or_update_records([sample_definition])

    # Update Depth Shift Set under Core To Log content data
    depth_shift_payload = copy.deepcopy(tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA_RECORDS_FORMAT))
    depth_shift_payload["DepthShiftWPCID"] = f"{depth_shift_record_id}:"
    depth_shift_payload["DepthShiftSet"][1]["OriginalTopDepth"] = 1020.0
    depth_shift_payload["DepthShiftSet"][1]["OriginalBaseDepth"] = 1030.0
    api.depth_shift.post_data(depth_shift_record_id, [depth_shift_payload])

    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {
        "orient": "records",
        "depth_shift_policy": "id_provided",
        "depth_shift_id": depth_shift_record_id,
    }
    if endpoint == "search_data":
        params["wellbore_id"] = f"{DATA_PARTITION_ID}:master-data--Wellbore:MagmaPulse:"
        params["rows_filter"] = f"SamplesAnalysisID,eq,{sample_analysis_record_id}:"

    response = method(*call_args, params=params)

    expected_data = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1_RECORDS_FORMAT))
    expected_data["SamplesAnalysisID"] = f"{sample_analysis_record_id}:"

    expected_depth_shift_data = {
        "SampleTop": 1015.0,
        "SampleBase": 1022.0,
        "ShiftedSampleTop": 1015.0,
        "ShiftedSampleBase": 1022.0,
        "DepthShiftWarnings": ["Sample not shifted: SampleTop 1015.000 falls outside all shift intervals."],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "user-provided",
        "definitiveDepthShiftAvailable": False,
        "usedDefinitive": False,
        "warnings": [],
    }

    # Assert
    actual_data = response["data"][0] if endpoint == "get_data" else response["result"][0]
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(response["DepthShiftData"][0], expected_depth_shift_data)
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_depth_shift_with_measurement_source_not_driller(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    sample_analysis_record_id,
    sample_analysis_dataset_id,
    analysis_type,
):
    """Verify depth shift when VerticalMeasurementSource is not Driller."""

    # Update sample definition
    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    source_id = f"{DATA_PARTITION_ID}:reference-data--VerticalMeasurementSource:LOG:"
    sample_definition["data"]["DepthMeasurements"][0]["VerticalMeasurementSourceID"] = source_id
    api.storage.create_or_update_records([sample_definition])

    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {
        "orient": "records",
        "depth_shift_policy": "id_provided",
        "depth_shift_id": depth_shift_record_id,
    }
    if endpoint == "search_data":
        params["wellbore_id"] = f"{DATA_PARTITION_ID}:master-data--Wellbore:MagmaPulse:"
        params["rows_filter"] = f"SamplesAnalysisID,eq,{sample_analysis_record_id}:"

    response = method(*call_args, params=params)

    expected_data = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1_RECORDS_FORMAT))
    expected_data["SamplesAnalysisID"] = f"{sample_analysis_record_id}:"

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

    # Assert
    actual_data = response["data"][0] if endpoint == "get_data" else response["result"][0]
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(response["DepthShiftData"][0], expected_depth_shift_data)
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_depth_shift_with_different_wellbore_ids(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    sample_analysis_record_id,
    sample_analysis_dataset_id,
    analysis_type,
):
    """Verify depth shift when assigned WellboreID differs between Sample and Depth Shift WPC."""

    # Update sample definition
    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    wellbore_id = f"{DATA_PARTITION_ID}:master-data--Wellbore:TectonicDrift:"
    sample_definition["data"]["SampleAcquisition"]["SampleAcquisitionDetail"]["WellboreID"] = wellbore_id
    api.storage.create_or_update_records([sample_definition])

    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {
        "orient": "records",
        "depth_shift_policy": "id_provided",
        "depth_shift_id": depth_shift_record_id,
    }
    if endpoint == "search_data":
        params["wellbore_id"] = f"{DATA_PARTITION_ID}:master-data--Wellbore:TectonicDrift:"
        params["rows_filter"] = f"SamplesAnalysisID,eq,{sample_analysis_record_id}:"

    response = method(*call_args, params=params)

    expected_data = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1_RECORDS_FORMAT))
    expected_data["SamplesAnalysisID"] = f"{sample_analysis_record_id}:"

    expected_depth_shift_data = {
        "SampleTop": 1002.0,
        "SampleBase": 1005.0,
        "ShiftedSampleTop": 1003.5,
        "ShiftedSampleBase": 1006.5,
        "DepthShiftWarnings": [
            f"Wellbore mismatch: sample wellbore '{DATA_PARTITION_ID}:master-data--Wellbore:TectonicDrift:' differs "
            f"from depth-shift wellbore '{DATA_PARTITION_ID}:master-data--Wellbore:MagmaPulse:'."
        ],
    }

    expected_metadata = {
        "appliedDepthShiftId": depth_shift_record_id,
        "source": "user-provided",
        "definitiveDepthShiftAvailable": False,
        "usedDefinitive": False,
        "warnings": [],
    }

    # Assert
    actual_data = response["data"][0] if endpoint == "get_data" else response["result"][0]
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(response["DepthShiftData"][0], expected_depth_shift_data)
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_depth_shift_with_different_depth_shift_ids(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    sample_analysis_record_id,
    sample_analysis_dataset_id,
    fresh_depth_shift_record_id,
    fresh_depth_shift_dataset_id,
    analysis_type,
):
    """Verify depth shift when assigned depth shift id is different than deifnitive depth shift id."""

    # Update sample definition with definitive depth shift id
    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    sample_definition["data"]["DefinitiveDepthShift"]["DefinitiveDepthShiftID"] = fresh_depth_shift_record_id
    api.storage.create_or_update_records([sample_definition])
    api.storage.create_or_update_records([sample_definition])

    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {
        "orient": "records",
        "depth_shift_policy": "id_provided",
        "depth_shift_id": depth_shift_record_id,
    }
    if endpoint == "search_data":
        params["wellbore_id"] = f"{DATA_PARTITION_ID}:master-data--Wellbore:MagmaPulse:"
        params["rows_filter"] = f"SamplesAnalysisID,eq,{sample_analysis_record_id}:"

    response = method(*call_args, params=params)

    expected_data = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1_RECORDS_FORMAT))
    expected_data["SamplesAnalysisID"] = f"{sample_analysis_record_id}:"

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
            f"Sample references a definitive depth shift ({fresh_depth_shift_record_id}) that differs from the "
            f"requested depth_shift_id ({depth_shift_record_id}). RAFS applied the requested depth_shift_id because "
            f"depth_shift_policy=id_provided."
        ],
    }

    # Assert
    actual_data = response["data"][0] if endpoint == "get_data" else response["result"][0]
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(response["DepthShiftData"][0], expected_depth_shift_data)
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_depth_shift_with_sample_top_only(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    sample_analysis_record_id,
    sample_analysis_dataset_id,
    analysis_type,
):
    """Verify depth shift when there is only Sample Top defined and no Sample Base."""

    # Update sample definition
    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    del sample_definition["data"]["DepthMeasurements"][1]
    api.storage.create_or_update_records([sample_definition])

    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {
        "orient": "records",
        "depth_shift_policy": "id_provided",
        "depth_shift_id": depth_shift_record_id,
    }
    if endpoint == "search_data":
        params["wellbore_id"] = f"{DATA_PARTITION_ID}:master-data--Wellbore:MagmaPulse:"
        params["rows_filter"] = f"SamplesAnalysisID,eq,{sample_analysis_record_id}:"

    response = method(*call_args, params=params)

    expected_data = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1_RECORDS_FORMAT))
    expected_data["SamplesAnalysisID"] = f"{sample_analysis_record_id}:"

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

    # Assert
    actual_data = response["data"][0] if endpoint == "get_data" else response["result"][0]
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(response["DepthShiftData"][0], expected_depth_shift_data)
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_depth_shift_with_sample_base_only(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    sample_analysis_record_id,
    sample_analysis_dataset_id,
    analysis_type,
):
    """Verify depth shift when there is only Sample Base defined and no Sample Top."""

    # Update sample definition
    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    del sample_definition["data"]["DepthMeasurements"][0]
    api.storage.create_or_update_records([sample_definition])

    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {
        "orient": "records",
        "depth_shift_policy": "id_provided",
        "depth_shift_id": depth_shift_record_id,
    }
    if endpoint == "search_data":
        params["wellbore_id"] = f"{DATA_PARTITION_ID}:master-data--Wellbore:MagmaPulse:"
        params["rows_filter"] = f"SamplesAnalysisID,eq,{sample_analysis_record_id}:"

    response = method(*call_args, params=params)

    expected_data = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1_RECORDS_FORMAT))
    expected_data["SamplesAnalysisID"] = f"{sample_analysis_record_id}:"

    expected_depth_shift_data = {
        "SampleTop": None,
        "SampleBase": 1005.0,
        "SampleMean": None,
        "ShiftedSampleTop": None,
        "ShiftedSampleBase": 1006.5,
        "ShiftedSampleMean": None,
        "DepthShiftWarnings": [
            f"No SampleTop provided for {DATA_PARTITION_ID}:master-data--Sample:Master_Sample. "
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

    # Assert
    actual_data = response["data"][0] if endpoint == "get_data" else response["result"][0]
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(response["DepthShiftData"][0], expected_depth_shift_data)
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_depth_shift_with_sample_mean_only(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    sample_analysis_record_id,
    sample_analysis_dataset_id,
    analysis_type,
):
    """Verify depth shift when there is only Sample Mean defined and no Sample Top and no Sample Base."""

    # Update sample definition
    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    measurement_type = f"{DATA_PARTITION_ID}:reference-data--VerticalMeasurementType:SampleMean:"
    sample_definition["data"]["DepthMeasurements"][0]["VerticalMeasurementTypeID"] = measurement_type
    del sample_definition["data"]["DepthMeasurements"][1]
    api.storage.create_or_update_records([sample_definition])

    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {
        "orient": "records",
        "depth_shift_policy": "id_provided",
        "depth_shift_id": depth_shift_record_id,
    }
    if endpoint == "search_data":
        params["wellbore_id"] = f"{DATA_PARTITION_ID}:master-data--Wellbore:MagmaPulse:"
        params["rows_filter"] = f"SamplesAnalysisID,eq,{sample_analysis_record_id}:"

    response = method(*call_args, params=params)

    expected_data = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1_RECORDS_FORMAT))
    expected_data["SamplesAnalysisID"] = f"{sample_analysis_record_id}:"

    expected_depth_shift_data = {
        "SampleTop": None,
        "SampleBase": None,
        "SampleMean": 1002.0,
        "ShiftedSampleTop": None,
        "ShiftedSampleBase": None,
        "ShiftedSampleMean": 1003.5,
        "DepthShiftWarnings": [
            f"No SampleTop or SampleBase provided for {DATA_PARTITION_ID}:master-data--Sample:Master_Sample. "
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

    # Assert
    actual_data = response["data"][0] if endpoint == "get_data" else response["result"][0]
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(response["DepthShiftData"][0], expected_depth_shift_data)
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_depth_shift_with_sample_top_sample_mean_only(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    sample_analysis_record_id,
    sample_analysis_dataset_id,
    analysis_type,
):
    """Verify depth shift when there is Sample Top and Sample Mean defined and no Sample Base."""

    # Update sample definition
    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    measurement_type = f"{DATA_PARTITION_ID}:reference-data--VerticalMeasurementType:SampleMean:"
    sample_definition["data"]["DepthMeasurements"][1]["VerticalMeasurementTypeID"] = measurement_type
    api.storage.create_or_update_records([sample_definition])

    # Update Depth Shift Set under Core To Log content data
    depth_shift_payload = copy.deepcopy(tests_data(DataFiles.CORE_TO_LOG_DEPTH_SHIFT_DATA_RECORDS_FORMAT))
    depth_shift_payload["DepthShiftWPCID"] = f"{depth_shift_record_id}:"
    depth_shift_payload["DepthShiftSet"][0]["ShiftedBaseDepth"] = 1013.5
    api.depth_shift.post_data(depth_shift_record_id, [depth_shift_payload])

    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {
        "orient": "records",
        "depth_shift_policy": "id_provided",
        "depth_shift_id": depth_shift_record_id,
    }
    if endpoint == "search_data":
        params["wellbore_id"] = f"{DATA_PARTITION_ID}:master-data--Wellbore:MagmaPulse:"
        params["rows_filter"] = f"SamplesAnalysisID,eq,{sample_analysis_record_id}:"

    response = method(*call_args, params=params)

    expected_data = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1_RECORDS_FORMAT))
    expected_data["SamplesAnalysisID"] = f"{sample_analysis_record_id}:"

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

    # Assert
    actual_data = response["data"][0] if endpoint == "get_data" else response["result"][0]
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(response["DepthShiftData"][0], expected_depth_shift_data)
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_depth_shift_with_sample_base_sample_mean_only(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    sample_analysis_record_id,
    sample_analysis_dataset_id,
    analysis_type,
):
    """Verify depth shift when there is Sample Base and Sample Mean defined and no Sample Top."""

    # Update sample definition
    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    measurement_type = f"{DATA_PARTITION_ID}:reference-data--VerticalMeasurementType:SampleMean:"
    sample_definition["data"]["DepthMeasurements"][0]["VerticalMeasurementTypeID"] = measurement_type
    sample_definition["data"]["DepthMeasurements"][0]["VerticalMeasurement"] = 1008.0
    sample_definition["data"]["DepthMeasurements"][1]["VerticalMeasurement"] = 1010.0
    api.storage.create_or_update_records([sample_definition])

    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {
        "orient": "records",
        "depth_shift_policy": "id_provided",
        "depth_shift_id": depth_shift_record_id,
    }
    if endpoint == "search_data":
        params["wellbore_id"] = f"{DATA_PARTITION_ID}:master-data--Wellbore:MagmaPulse:"
        params["rows_filter"] = f"SamplesAnalysisID,eq,{sample_analysis_record_id}:"

    response = method(*call_args, params=params)

    expected_data = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1_RECORDS_FORMAT))
    expected_data["SamplesAnalysisID"] = f"{sample_analysis_record_id}:"

    expected_depth_shift_data = {
        "SampleTop": None,
        "SampleBase": 1010.0,
        "SampleMean": 1008.0,
        "ShiftedSampleTop": None,
        "ShiftedSampleBase": 1012.5,
        "ShiftedSampleMean": 1010.5,
        "DepthShiftWarnings": [
            f"No SampleTop provided for {DATA_PARTITION_ID}:master-data--Sample:Master_Sample. "
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

    # Assert
    actual_data = response["data"][0] if endpoint == "get_data" else response["result"][0]
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(response["DepthShiftData"][0], expected_depth_shift_data)
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_apply_depth_shift_without_depth_measurements(
    api,
    helper,
    tests_data,
    endpoint,
    args,
    depth_shift_record_id,
    depth_shift_dataset_id,
    sample_analysis_record_id,
    sample_analysis_dataset_id,
    analysis_type,
):
    """Verify depth shift sourced from SampleAcquisitionDetail when there is no DepthMeasurements."""

    # Update sample definition
    sample_definition = copy.deepcopy(tests_data(DataFiles.SAMPLE))
    del sample_definition["data"]["DepthMeasurements"]
    api.storage.create_or_update_records([sample_definition])

    record_id = sample_analysis_record_id
    dataset_id = sample_analysis_dataset_id
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {
        "orient": "records",
        "depth_shift_policy": "id_provided",
        "depth_shift_id": depth_shift_record_id,
    }
    if endpoint == "search_data":
        params["wellbore_id"] = f"{DATA_PARTITION_ID}:master-data--Wellbore:MagmaPulse:"
        params["rows_filter"] = f"SamplesAnalysisID,eq,{sample_analysis_record_id}:"

    response = method(*call_args, params=params)

    expected_data = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1_RECORDS_FORMAT))
    expected_data["SamplesAnalysisID"] = f"{sample_analysis_record_id}:"

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

    # Assert
    actual_data = response["data"][0] if endpoint == "get_data" else response["result"][0]
    helper.compare_response_fields(actual_data, expected_data)
    helper.compare_response_fields(response["DepthShiftData"][0], expected_depth_shift_data)
    helper.compare_response_fields(response["DepthShiftMetadata"], expected_metadata)
