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

from app.resources.common_headers import ACCEPT
from tests.integration.config import (
    CONFIG,
    DataFiles,
    SamplesAnalysisEndpoints,
    SEARCH_PAGE_LIMITS,
)

DATA_PARTITION_ID = CONFIG["DATA_PARTITION"]
GEO_PARAMS = [
    ("field_id", "Field"),
    ("basin_id", "Basin"),
    ("wellbore_id", "Wellbore"),
]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RECORD_ID_ENDPOINTS_ARGS)
def test_nmr_negative_invalid_regex_record_id_in_url(
    api, tests_data, endpoint, args, version, dataset_id_v1, analysis_type
):
    """Reject record IDs not matching OSDU pattern with 422 Unprocessable Content."""
    record_id = "invalid_id"
    dataset_id = dataset_id_v1
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_kwargs = {name: local_vars[name] for name in args}

    call_kwargs.update({
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    })

    if endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        call_kwargs["body"] = data_payload

    response = method(**call_kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert (
        "work-product-component--SamplesAnalysis ID is not provided in expected OSDU pattern "
        '"^[\\w\\-\\.]+:work-product-component--SamplesAnalysis:[\\w\\-\\.\\:\\%]+$"'
    ) in body["errors"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RECORD_ID_ENDPOINTS_ARGS)
def test_nmr_negative_invalid_data_partition_id_record_id_in_url(
    api, tests_data, endpoint, args, version, dataset_id_v1, analysis_type
):
    """Reject record ID with wrong partition prefix with 400 Bad Request."""
    dataset_id = dataset_id_v1
    method = getattr(api.sample_analysis, endpoint)
    record_id = "WrongID:work-product-component--SamplesAnalysis:Test123"
    local_vars = locals().copy()
    call_kwargs = {name: local_vars[name] for name in args}

    call_kwargs.update({
        "allowed_codes": [status.HTTP_400_BAD_REQUEST],
        "raw": True,
    })

    if endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        call_kwargs["body"] = data_payload

    response = method(**call_kwargs)

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert f"Invalid record ID" in body["reason"]
    assert f"The record '{record_id}' does not belong to account '{DATA_PARTITION_ID}'" in body["message"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RECORD_ID_ENDPOINTS_ARGS)
def test_nmr_negative_non_existing_record_id_in_url(
    api, tests_data, endpoint, args, version, dataset_id_v1, analysis_type
):
    """Reject non-existent record ID with 404 Not Found."""
    dataset_id = dataset_id_v1
    method = getattr(api.sample_analysis, endpoint)
    record_id = f"{DATA_PARTITION_ID}:work-product-component--SamplesAnalysis:NonExistingID"
    local_vars = locals().copy()
    call_kwargs = {name: local_vars[name] for name in args}


    call_kwargs.update({
        "allowed_codes": [status.HTTP_404_NOT_FOUND],
        "raw": True,
    })

    if endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        call_kwargs["body"] = data_payload

    response = method(**call_kwargs)

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert "Record not found" in body["reason"]
    assert (
        f"The record '{record_id}' was not found" in body["message"]
        or f"Record with id '{record_id}' does not exist" in body["message"]
    )


def test_nmr_negative_non_existing_version_in_url(api, tests_data, record_id):
    """Reject non-existent version number with 404 Not Found."""
    version = 10000001
    kwargs = {
        "allowed_codes": [status.HTTP_404_NOT_FOUND],
        "raw": True,
    }

    response = api.sample_analysis.get_record_version(record_id, version, **kwargs)

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert "Record version not found" in body["reason"]
    assert "The requested record version was not found" in body["message"]


def test_nmr_negative_edge_max_version_in_url(api, tests_data, record_id):
    """Reject extreme version number - boundary testing."""
    version = 12345678901234567890
    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = api.sample_analysis.get_record_version(record_id, version, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert "version Input should be less than or equal to 9223372036854775807" in body["errors"]


def test_nmr_negative_edge_min_version_in_url(api, tests_data, record_id):
    """Reject zero/negative version numbers boundary testing."""
    version = 0
    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = api.sample_analysis.get_record_version(record_id, version, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert "version Input should be greater than or equal to 1" in body["errors"]


def test_nmr_negative_invalid_regex_dataset_id_in_url(api, tests_data, record_id, analysis_type):
    """Reject dataset IDs not matching UUID or OSDU format with 422 Unprocessable Content."""
    dataset_id_v1 = "invalid_id"
    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = api.sample_analysis.get_data(record_id, dataset_id_v1, analysis_type, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert (
        'content_id string does not match regex "([\\w\\-\\.]+:dataset--File.Generic:[\\w\\-\\d\\.]+:?'
        '[\\w\\-\\.\\:\\%]*)|([\\d\\w]+-[\\d\\w]+-[\\d\\w]+-[\\d\\w]+-[\\d\\w]+)"'
    ) in body["errors"]


def test_nmr_negative_invalid_data_partition_id_in_dataset_id_in_url(api, tests_data, record_id, analysis_type):
    """Reject dataset ID with wrong partition prefix with 404 Not Found."""
    dataset_id = f"WrongID:dataset--File.Generic:{analysis_type}-Test123"
    kwargs = {
        "allowed_codes": [status.HTTP_404_NOT_FOUND],
        "raw": True,
    }

    response = api.sample_analysis.get_data(record_id, dataset_id, analysis_type, **kwargs)

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert "Not found." in body["reason"]
    assert f"{dataset_id} does not exist in current record." in body["message"]


def test_nmr_negative_non_existing_dataset_id_in_url(api, tests_data, record_id, analysis_type):
    """Reject non-existent dataset ID with 404 Not Found."""
    dataset_id = f"{DATA_PARTITION_ID}:dataset--File.Generic:{analysis_type}-InvalidId"
    kwargs = {
        "allowed_codes": [status.HTTP_404_NOT_FOUND],
        "raw": True,
    }

    response = api.sample_analysis.get_data(record_id, dataset_id, analysis_type, **kwargs)

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert "Not found." in body["reason"]
    assert f"{dataset_id} does not exist in current record." in body["message"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_nmr_negative_invalid_columns_filter_param(
    api, tests_data, endpoint, args, record_id, dataset_id_v1, analysis_type
):
    """Reject non-existent columns in filter with 422 Unprocessable Content."""
    dataset_id = dataset_id_v1
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {"columns_filter": "InvalidColumn"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Invalid columns: {'InvalidColumn'}. Select one of " in body["reason"]
    assert "SamplesAnalysisID" in body["reason"]
    assert "SampleID" in body["reason"]
    assert "Meta" in body["reason"]
    assert "NMRTest" in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_nmr_negative_invalid_column_in_rows_filter_param(
    api, tests_data, endpoint, args, record_id, dataset_id_v1, analysis_type
):
    """Reject non-existent column in rows filter with 422 Unprocessable Content."""
    dataset_id = dataset_id_v1
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {"rows_filter": f"InvalidColumn,equal,{record_id}:"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "For filter select one of " in body["reason"]
    assert "SamplesAnalysisID" in body["reason"]
    assert "SampleID" in body["reason"]
    assert "Meta" in body["reason"]
    assert "NMRTest" in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_nmr_negative_invalid_operator_in_rows_filter_param(
    api, tests_data, endpoint, args, record_id, dataset_id_v1, analysis_type
):
    """Reject unsupported operators in rows filter with 422 Unprocessable Content."""
    dataset_id = dataset_id_v1
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {"rows_filter": f"SamplesAnalysisID,equal,{record_id}:"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Invalid comparison operator 'equal'. Allowed: ['lt', 'gt', 'lte', 'gte', 'eq', 'neq']" in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_nmr_negative_invalid_syntax_rows_filter_param(
    api, tests_data, endpoint, args, record_id, dataset_id_v1, analysis_type
):
    """Reject malformed rows filter syntax with 422 Unprocessable Content."""
    dataset_id = dataset_id_v1
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {"rows_filter": "Invalid syntax"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Bad rows_filter expression. Correct format: 'Column[.Field],operator,value" in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_nmr_negative_unsupported_filtering_rows_filter_param(
    api, tests_data, endpoint, args, record_id, dataset_id_v1, analysis_type
):
    """Reject dotted field access on array columns with 422 Unprocessable Content."""
    dataset_id = dataset_id_v1
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {"rows_filter": "NMRTest.TestConditionID,eq,dummy"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert (
        "Column 'NMRTest' is an array; dotted field access ('NMRTest.TestConditionID') is not supported."
    ) in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_nmr_negative_invalid_column_in_columns_aggregation_param(
    api, tests_data, endpoint, args, record_id, dataset_id_v1, analysis_type
):
    """Reject non-existent column in aggregation with 422 Unprocessable Content."""
    dataset_id = dataset_id_v1
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {"columns_aggregation": "InvalidColumn,mean"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "For aggregation select one of " in body["reason"]
    assert "SamplesAnalysisID" in body["reason"]
    assert "SampleID" in body["reason"]
    assert "Meta" in body["reason"]
    assert "NMRTest" in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_nmr_negative_invalid_operator_in_columns_aggregation_param(
    api, tests_data, endpoint, args, record_id, dataset_id_v1, analysis_type
):
    """Reject unsupported operators in aggregation with 422 Unprocessable Content."""
    dataset_id = dataset_id_v1
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    params = {"columns_aggregation": "SampleID,avg"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Invalid aggregation operator 'avg'. Allowed: " in body["reason"]
    assert "describe" in body["reason"]
    assert "min" in body["reason"]
    assert "max" in body["reason"]
    assert "sum" in body["reason"]
    assert "mean" in body["reason"]
    assert "count" in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_nmr_negative_invalid_syntax_aggregation_param(
    api, tests_data, endpoint, args, record_id, dataset_id_v1, analysis_type
):
    """Reject malformed aggregation syntax with 422 Unprocessable Content."""
    dataset_id = dataset_id_v1
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    params = {"columns_aggregation": "Invalid syntax"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Bad aggregation expression. Correct form 'Column[.Field],operator'" in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_nmr_negative_unsupported_aggregation_on_array_fields(
    api, tests_data, endpoint, args, record_id, dataset_id_v1, analysis_type
):
    """Reject dotted field access on array columns in aggregation with 422 Unprocessable Content."""
    dataset_id = dataset_id_v1
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    params = {"columns_aggregation": "NMRTest.TestConditionID,describe"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert (
        "Column 'NMRTest' is an array; dotted field access ('NMRTest.TestConditionID') is not supported."
    ) in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_nmr_negative_params_conflict(api, tests_data, endpoint, args, record_id, dataset_id_v1, analysis_type):
    """Reject incompatible parameter combinations with 422 Unprocessable Content."""
    dataset_id = dataset_id_v1
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    aggregated_column = "SamplesAnalysisID"
    params = {
        "columns_filter": "SampleID,NMRTest",
        "columns_aggregation": f"{aggregated_column},describe",
    }

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert (
        f"Filter conflict: 'columns_aggregation' column '{aggregated_column}' is not included in 'columns_filter'. "
        f"Either add '{aggregated_column}' to 'columns_filter' or remove 'columns_filter'."
    ) in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.ORIENT_ENDPOINTS_ARGS)
def test_nmr_negative_invalid_orient_param(
    api, tests_data, endpoint, args, record_id, dataset_id_v1, analysis_type
):
    """Reject invalid orient parameter values with 422 Unprocessable Content."""
    dataset_id = dataset_id_v1
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    params = {"orient": "dummy"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert "orient Input should be 'split' or 'records'" in body["errors"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.SEARCH_ENDPOINTS_ARGS)
def test_nmr_negative_invalid_format_indexed_start_date_param(api, tests_data, endpoint, args, analysis_type):
    """Reject invalid indexed_start_date format (not YYYY-MM-DD) with 422 Unprocessable Content."""
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    params = {"indexed_start_date": "18-02-2026"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Invalid format for indexed_start_date: '18-02-2026'. Expected format: YYYY-MM-DD." in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.SEARCH_ENDPOINTS_ARGS)
def test_nmr_negative_invalid_format_indexed_end_date_param(api, tests_data, endpoint, args, analysis_type):
    """Reject invalid indexed_end_date format (not YYYY-MM-DD) with 422 Unprocessable Content."""
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    params = {"indexed_end_date": "2026/02/18"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Invalid format for indexed_end_date: '2026/02/18'. Expected format: YYYY-MM-DD." in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.SEARCH_ENDPOINTS_ARGS)
def test_nmr_negative_indexed_end_date_before_indexed_start_date_param(
    api, tests_data, endpoint, args, analysis_type
):
    """Reject end_date before start_date with 422 Unprocessable Content."""
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    params = {
        "indexed_start_date": "2026-02-19",
        "indexed_end_date": "2026-02-18",
    }

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "indexed_start_date must be before or equal to indexed_end_date" in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.SEARCH_ENDPOINTS_ARGS)
def test_nmr_negative_invalid_format_page_limit_param(api, tests_data, endpoint, args, analysis_type):
    """Reject non-integer page_limit with 422 Unprocessable Content."""
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    params = {"page_limit": "dummy"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert "page_limit Input should be a valid integer, unable to parse string as an integer" in body["errors"]


@pytest.mark.parametrize(("endpoint", "max_limit"), SEARCH_PAGE_LIMITS.items())
def test_nmr_negative_boundary_value_page_limit_param(api, tests_data, endpoint, max_limit, analysis_type):
    """Reject page_limit exceeding maximum with 422 Unprocessable Content."""
    method = getattr(api.sample_analysis, endpoint)
    params = {"page_limit": max_limit + 1}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(analysis_type=analysis_type, params=params, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert f"page_limit Input should be less than or equal to {max_limit}" in body["errors"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.SEARCH_ENDPOINTS_ARGS)
def test_nmr_negative_invalid_format_offset_param(api, tests_data, endpoint, args, analysis_type):
    """Reject non-integer offset with 422 Unprocessable Content."""
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    params = {"offset": "dummy"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert "offset Input should be a valid integer, unable to parse string as an integer" in body["errors"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.SEARCH_ENDPOINTS_ARGS)
def test_nmr_negative_boundary_value_offset_param(api, tests_data, endpoint, args, analysis_type):
    """Reject negative offset with 422 Unprocessable Content."""
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    params = {"offset": -1}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert "offset Input should be greater than or equal to 0" in body["errors"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.SCHEMA_VERSION_ENDPOINTS_ARGS)
def test_nmr_negative_missing_schema_version(
    api, tests_data, endpoint, args, record_id, dataset_id_v1, analysis_type
):
    """Reject missing schema version with 406 Not Applicable."""
    dataset_id = dataset_id_v1
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_kwargs = {name: local_vars[name] for name in args}

    call_kwargs.update({
        "schema_version": None,
        "allowed_codes": [status.HTTP_406_NOT_ACCEPTABLE],
        "raw": True,
    })

    if endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        call_kwargs["body"] = data_payload

    response = method(**call_kwargs)

    # Assert
    assert response.status_code == 406
    body = response.json()
    assert (
        "No schema version specified or invalid schema format. Use the content_schema_version query parameter "
        "(e.g. ?content_schema_version=1.0.0). The deprecated Accept header versioning is also still accepted "
        "(e.g. Accept: */*;version=1.0.0)."
    ) in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.SCHEMA_VERSION_ENDPOINTS_ARGS)
def test_nmr_negative_unsupported_format_schema_version(
    api, tests_data, endpoint, args, record_id, dataset_id_v1, analysis_type
):
    """Reject unsupported format for schema version with 422 Unprocessable Content."""
    dataset_id = dataset_id_v1
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_kwargs = {name: local_vars[name] for name in args}

    call_kwargs.update({
        "schema_version": "0",
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    })

    if endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        call_kwargs["body"] = data_payload

    response = method(**call_kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert (
        "Invalid version format in content_schema_version: '0'. Expected format: major.minor.patch (e.g. 1.0.0)"
    ) in body["reason"]


@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.SCHEMA_VERSION_ENDPOINTS_ARGS)
def test_nmr_negative_unsupported_schema_version(
    api, tests_data, endpoint, args, record_id, dataset_id_v1, analysis_type
):
    """Reject unsupported schema version with 404 Not Found."""
    dataset_id = dataset_id_v1
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_kwargs = {name: local_vars[name] for name in args}

    call_kwargs.update({
        "schema_version": "0.0.7",
        "allowed_codes": [status.HTTP_404_NOT_FOUND],
        "raw": True,
    })

    if endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        call_kwargs["body"] = data_payload

    response = method(**call_kwargs)

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert (
        f"Model not found for type '{analysis_type}',  version '0.0.7'. Available versions: {{'1.0.0'}}"
    ) in body["reason"]

@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.SCHEMA_VERSION_ENDPOINTS_ARGS)
def test_nmr_negative_schema_version_overwritten_by_param(
    api, tests_data, endpoint, args, record_id, dataset_id_v1, analysis_type
):
    """Reject unsupported schema version from param that takes precedence over the Accept header."""
    dataset_id = dataset_id_v1
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_kwargs = {name: local_vars[name] for name in args}

    call_kwargs.update({
        "schema_version": "0.0.7",
        "allowed_codes": [status.HTTP_404_NOT_FOUND],
        "raw": True,
        "headers": {ACCEPT: "application/json;version=1.0.0"},
    })

    if endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.NMR_DATA_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        call_kwargs["body"] = data_payload

    response = method(**call_kwargs)

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert (
        f"Model not found for type '{analysis_type}',  version '0.0.7'. Available versions: {{'1.0.0'}}"
    ) in body["reason"]


@pytest.mark.parametrize("geo_param,master_data_type", GEO_PARAMS)
@pytest.mark.parametrize("endpoint,args", SamplesAnalysisEndpoints.SEARCH_ENDPOINTS_ARGS)
def test_nmr_negative_invalid_geo_param_value(api, endpoint, args, analysis_type, geo_param, master_data_type):
    """Reject incorrect regex for geo param with 400 Bad Request."""
    method = getattr(api.sample_analysis, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    params = {f"{geo_param}": "dummy"}

    kwargs = {
        "allowed_codes": [status.HTTP_400_BAD_REQUEST],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert (
        f"Invalid '{geo_param}' format. Expected OSDU record ID matching ^[\\w\\-\\.]+:master-data--{master_data_type}:"
        "[\\w\\-\\.\\:\\%]+$. Got: dummy"
    ) in body["reason"]
