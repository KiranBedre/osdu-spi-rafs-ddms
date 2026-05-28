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
    Endpoints,
)

DATA_PARTITION_ID = CONFIG["DATA_PARTITION"]


@pytest.mark.parametrize("endpoint,args", Endpoints.RECORD_ID_ENDPOINTS_ARGS)
def test_rsrp_negative_invalid_regex_record_id_in_url(api, tests_data, endpoint, args, version, dataset_id):
    """Reject record IDs not matching OSDU pattern with 422 Unprocessable Content."""
    method = getattr(api.simulation_rock_physics, endpoint)
    record_id = "invalid_id"
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    if endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        kwargs["body"] = data_payload

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert (
        "work-product-component--ReservoirSimulationRockPhysicsModel ID is not provided in expected OSDU pattern "
        '"^[\\w\\-\\.]+:work-product-component--ReservoirSimulationRockPhysicsModel:[\\w\\-\\.\\:\\%]+$"'
    ) in body["errors"]


@pytest.mark.parametrize("endpoint,args", Endpoints.RECORD_ID_ENDPOINTS_ARGS)
def test_rsrp_negative_invalid_data_partition_id_record_id_in_url(api, tests_data, endpoint, args, version, dataset_id):
    """Reject record ID with wrong partition prefix with 400 Bad Request."""
    method = getattr(api.simulation_rock_physics, endpoint)
    record_id = "WrongID:work-product-component--ReservoirSimulationRockPhysicsModel:Test123"
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "allowed_codes": [status.HTTP_400_BAD_REQUEST],
        "raw": True,
    }

    if endpoint == "post_data":
        pytest.skip(reason="#733")
        data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        kwargs["body"] = data_payload

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 400
    body = response.json()
    assert f"The record '{record_id}' does not belong to account '{DATA_PARTITION_ID}'" in body["reason"]


@pytest.mark.parametrize("endpoint,args", Endpoints.RECORD_ID_ENDPOINTS_ARGS)
def test_rsrp_negative_non_existing_record_id_in_url(api, tests_data, endpoint, args, version, dataset_id):
    """Reject non-existent record ID with 404 Not Found."""
    method = getattr(api.simulation_rock_physics, endpoint)
    record_id = f"{DATA_PARTITION_ID}:work-product-component--ReservoirSimulationRockPhysicsModel:NonExistingID"
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "allowed_codes": [status.HTTP_404_NOT_FOUND],
        "raw": True,
    }

    if endpoint == "post_data":
        pytest.skip(reason="#733")
        data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        kwargs["body"] = data_payload

    response = method(*call_args, **kwargs)

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert "Record not found" in body["reason"]
    assert (
        f"The record '{record_id}' was not found" in body["message"]
        or f"Record with id '{record_id}' does not exist" in body["message"]
    )


def test_rsrp_negative_non_existing_version_in_url(api, tests_data, record_id):
    """Reject non-existent version number with 404 Not Found."""
    version = 10000001
    kwargs = {
        "allowed_codes": [status.HTTP_404_NOT_FOUND],
        "raw": True,
    }

    response = api.simulation_rock_physics.get_record_version(record_id, version, **kwargs)

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert "Record version not found" in body["reason"]
    assert "The requested record version was not found" in body["message"]


def test_rsrp_negative_edge_max_version_in_url(api, tests_data, record_id):
    """Reject extreme version number - boundary testing."""
    version = 12345678901234567890
    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = api.simulation_rock_physics.get_record_version(record_id, version, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert "version ensure this value is less than or equal to 9223372036854775807" in body["errors"]


def test_rsrp_negative_edge_min_version_in_url(api, tests_data, record_id):
    """Reject zero/negative version numbers boundary testing."""
    version = 0
    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = api.simulation_rock_physics.get_record_version(record_id, version, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert "version ensure this value is greater than or equal to 1" in body["errors"]


def test_rsrp_negative_invalid_regex_dataset_id_in_url(api, tests_data, record_id):
    """Reject dataset IDs not matching UUID or OSDU format with 422 Unprocessable Content."""
    dataset_id = "invalid_id"
    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = api.simulation_rock_physics.get_data(record_id, dataset_id, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert (
        'content_id string does not match regex "([\\w\\-\\.]+:dataset--File.Generic:[\\w\\-\\d\\.]+:?'
        '[\\w\\-\\.\\:\\%]*)|([\\d\\w]+-[\\d\\w]+-[\\d\\w]+-[\\d\\w]+-[\\d\\w]+)"'
    ) in body["errors"]


def test_rsrp_negative_invalid_data_partition_id_in_dataset_id_in_url(api, tests_data, record_id):
    """Reject dataset ID with wrong partition prefix with 404 Not Found."""
    dataset_id = "WrongID:dataset--File.Generic:reservoirsimulationrockphysicsmodel-Test123"
    kwargs = {
        "allowed_codes": [status.HTTP_404_NOT_FOUND],
        "raw": True,
    }

    response = api.simulation_rock_physics.get_data(record_id, dataset_id, **kwargs)

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert "Not found." in body["reason"]
    assert f"{dataset_id} does not exist in current record." in body["message"]


def test_rsrp_negative_non_existing_dataset_id_in_url(api, tests_data, record_id):
    """Reject non-existent dataset ID with 404 Not Found."""
    dataset_id = f"{DATA_PARTITION_ID}:dataset--File.Generic:reservoirsimulationrockphysicsmodel-InvalidId"
    kwargs = {
        "allowed_codes": [status.HTTP_404_NOT_FOUND],
        "raw": True,
    }

    response = api.simulation_rock_physics.get_data(record_id, dataset_id, **kwargs)

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert "Not found." in body["reason"]
    assert f"{dataset_id} does not exist in current record." in body["message"]


@pytest.mark.parametrize("endpoint,args", Endpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_rsrp_negative_invalid_columns_filter_param(api, tests_data, endpoint, args, record_id, dataset_id):
    """Reject non-existent columns in filter with 422 Unprocessable Content."""
    method = getattr(api.simulation_rock_physics, endpoint)
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
    assert "ReservoirSimulationRockPhysicsID" in body["reason"]
    assert "Meta" in body["reason"]
    assert "Compressibility" in body["reason"]
    assert "ThermalModelDefinition" in body["reason"]


@pytest.mark.parametrize("endpoint,args", Endpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_rsrp_negative_invalid_column_in_rows_filter_param(api, tests_data, endpoint, args, record_id, dataset_id):
    """Reject non-existent column in rows filter with 422 Unprocessable Content."""
    method = getattr(api.simulation_rock_physics, endpoint)
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
    assert "ReservoirSimulationRockPhysicsID" in body["reason"]
    assert "Meta" in body["reason"]
    assert "Compressibility" in body["reason"]
    assert "ThermalModelDefinition" in body["reason"]


@pytest.mark.parametrize("endpoint,args", Endpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_rsrp_negative_invalid_operator_in_rows_filter_param(api, tests_data, endpoint, args, record_id, dataset_id):
    """Reject unsupported operators in rows filter with 422 Unprocessable Content."""
    method = getattr(api.simulation_rock_physics, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    params = {"rows_filter": f"ReservoirSimulationRockPhysicsID,equal,{record_id}:"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Invalid comparison operator 'equal'. Allowed: ['lt', 'gt', 'lte', 'gte', 'eq', 'neq']" in body["reason"]


@pytest.mark.parametrize("endpoint,args", Endpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_rsrp_negative_invalid_syntax_rows_filter_param(api, tests_data, endpoint, args, record_id, dataset_id):
    """Reject malformed rows filter syntax with 422 Unprocessable Content."""
    method = getattr(api.simulation_rock_physics, endpoint)
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


@pytest.mark.parametrize("endpoint,args", Endpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_rsrp_negative_unsupported_type_filtering_rows_filter_param(
    api, tests_data, endpoint, args, record_id, dataset_id
):
    """Reject dotted field access on array columns with 422 Unprocessable Content."""
    method = getattr(api.simulation_rock_physics, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    params = {"rows_filter": "ThermalModelDefinition.ThermalConductivity,eq,dummy"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Wrong type for value: 'dummy'. Expected type: 'number'" in body["reason"]


@pytest.mark.parametrize("endpoint,args", Endpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_rsrp_negative_invalid_column_in_columns_aggregation_param(
    api, tests_data, endpoint, args, record_id, dataset_id
):
    """Reject non-existent column in aggregation with 422 Unprocessable Content."""
    method = getattr(api.simulation_rock_physics, endpoint)
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
    assert "ReservoirSimulationRockPhysicsID" in body["reason"]
    assert "Meta" in body["reason"]
    assert "Compressibility" in body["reason"]
    assert "ThermalModelDefinition" in body["reason"]


@pytest.mark.parametrize("endpoint,args", Endpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_rsrp_negative_invalid_operator_in_columns_aggregation_param(
    api, tests_data, endpoint, args, record_id, dataset_id
):
    """Reject unsupported operators in aggregation with 422 Unprocessable Content."""
    method = getattr(api.simulation_rock_physics, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    params = {"columns_aggregation": "ReservoirSimulationRockPhysicsID,avg"}

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


@pytest.mark.parametrize("endpoint,args", Endpoints.ENDPOINTS_WITH_FILTERS_ARGS)
def test_rsrp_negative_invalid_syntax_aggregation_param(api, tests_data, endpoint, args, record_id, dataset_id):
    """Reject malformed aggregation syntax with 422 Unprocessable Content."""
    method = getattr(api.simulation_rock_physics, endpoint)
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


@pytest.mark.parametrize("endpoint,args", Endpoints.RETURN_DATA_ENDPOINTS_ARGS)
def test_rsrp_negative_params_conflict(api, tests_data, endpoint, args, record_id, dataset_id):
    """Reject incompatible parameter combinations with 422 Unprocessable Content."""
    method = getattr(api.simulation_rock_physics, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]
    aggregated_column = "ReservoirSimulationRockPhysicsID"
    params = {
        "columns_filter": "Compressibility,ThermalModelDefinition",
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


@pytest.mark.parametrize("endpoint,args", Endpoints.ORIENT_ENDPOINTS_ARGS)
def test_rsrp_negative_invalid_orient_param(api, tests_data, endpoint, args, record_id, dataset_id):
    """Reject invalid orient parameter values with 422 Unprocessable Content."""
    method = getattr(api.simulation_rock_physics, endpoint)
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
    assert "orient unexpected value; permitted: 'split', 'records'" in body["errors"]


@pytest.mark.parametrize("endpoint", Endpoints.SEARCH_ENDPOINTS)
def test_rsrp_negative_invalid_format_indexed_start_date_param(api, tests_data, endpoint):
    """Reject invalid indexed_start_date format (not YYYY-MM-DD) with 422 Unprocessable Content."""
    method = getattr(api.simulation_rock_physics, endpoint)
    params = {"indexed_start_date": "18-02-2026"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Invalid format for indexed_start_date: '18-02-2026'. Expected format: YYYY-MM-DD." in body["reason"]


@pytest.mark.parametrize("endpoint", Endpoints.SEARCH_ENDPOINTS)
def test_rsrp_negative_invalid_format_indexed_end_date_param(api, tests_data, endpoint):
    """Reject invalid indexed_end_date format (not YYYY-MM-DD) with 422 Unprocessable Content."""
    method = getattr(api.simulation_rock_physics, endpoint)
    params = {"indexed_end_date": "2026/02/18"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Invalid format for indexed_end_date: '2026/02/18'. Expected format: YYYY-MM-DD." in body["reason"]


@pytest.mark.parametrize("endpoint", Endpoints.SEARCH_ENDPOINTS)
def test_rsrp_negative_indexed_end_date_before_indexed_start_date_param(api, tests_data, endpoint):
    """Reject end_date before start_date with 422 Unprocessable Content."""
    method = getattr(api.simulation_rock_physics, endpoint)
    params = {
        "indexed_start_date": "2026-02-19",
        "indexed_end_date": "2026-02-18",
    }

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "indexed_start_date must be before or equal to indexed_end_date" in body["reason"]


@pytest.mark.parametrize("endpoint", Endpoints.SEARCH_ENDPOINTS)
def test_rsrp_negative_invalid_format_page_limit_param(api, tests_data, endpoint):
    """Reject non-integer page_limit with 422 Unprocessable Content."""
    method = getattr(api.simulation_rock_physics, endpoint)
    params = {"page_limit": "dummy"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert "page_limit value is not a valid integer" in body["errors"]


@pytest.mark.parametrize("endpoint", Endpoints.SEARCH_ENDPOINTS)
def test_rsrp_negative_boundary_value_page_limit_param(api, tests_data, endpoint):
    """Reject page_limit exceeding maximum (100) with 422 Unprocessable Content."""
    method = getattr(api.simulation_rock_physics, endpoint)
    params = {"page_limit": 101}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert "page_limit ensure this value is less than or equal to 100" in body["errors"]


@pytest.mark.parametrize("endpoint", Endpoints.SEARCH_ENDPOINTS)
def test_rsrp_negative_invalid_format_offset_param(api, tests_data, endpoint):
    """Reject non-integer offset with 422 Unprocessable Content."""
    method = getattr(api.simulation_rock_physics, endpoint)
    params = {"offset": "dummy"}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert "offset value is not a valid integer" in body["errors"]


@pytest.mark.parametrize("endpoint", Endpoints.SEARCH_ENDPOINTS)
def test_rsrp_negative_boundary_value_offset_param(api, tests_data, endpoint):
    """Reject negative offset with 422 Unprocessable Content."""
    method = getattr(api.simulation_rock_physics, endpoint)
    params = {"offset": -1}

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    response = method(params=params, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert "Unprocessable entity." in body["reason"]
    assert "offset ensure this value is greater than or equal to 0" in body["errors"]


@pytest.mark.parametrize("endpoint,args", Endpoints.SCHEMA_VERSION_ENDPOINTS_ARGS)
def test_rsrp_negative_missing_schema_version(api, tests_data, endpoint, args, record_id, dataset_id):
    """Reject missing schema version with 406 Not Applicable."""
    method = getattr(api.simulation_rock_physics, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "allowed_codes": [status.HTTP_406_NOT_ACCEPTABLE],
        "raw": True,
    }

    if endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        kwargs["body"] = data_payload

    response = method(schema_version=None, *call_args, **kwargs)

    # Assert
    assert response.status_code == 406
    body = response.json()
    assert (
        "No schema version specified or invalid schema format. Use the content_schema_version query parameter "
        "(e.g. ?content_schema_version=1.0.0). The deprecated Accept header versioning is also still accepted "
        "(e.g. Accept: */*;version=1.0.0)."
    ) in body["reason"]


@pytest.mark.parametrize("endpoint,args", Endpoints.SCHEMA_VERSION_ENDPOINTS_ARGS)
def test_rsrp_negative_unsupported_format_schema_version(api, tests_data, endpoint, args, record_id, dataset_id):
    """Reject unsupported format for schema version with 422 Unprocessable Content."""
    method = getattr(api.simulation_rock_physics, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "allowed_codes": [status.HTTP_422_UNPROCESSABLE_CONTENT],
        "raw": True,
    }

    if endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        kwargs["body"] = data_payload

    response = method(schema_version="0", *call_args, **kwargs)

    # Assert
    assert response.status_code == 422
    body = response.json()
    assert (
        "Invalid version format in content_schema_version: '0'. Expected format: major.minor.patch (e.g. 1.0.0)"
    ) in body["reason"]


@pytest.mark.parametrize("endpoint,args", Endpoints.SCHEMA_VERSION_ENDPOINTS_ARGS)
def test_rsrp_negative_unsupported_schema_version(api, tests_data, endpoint, args, record_id, dataset_id):
    """Reject unsupported schema version with 404 Not Found."""
    method = getattr(api.simulation_rock_physics, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "allowed_codes": [status.HTTP_404_NOT_FOUND],
        "raw": True,
    }

    if endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        kwargs["body"] = data_payload

    response = method(schema_version="0.0.7", *call_args, **kwargs)

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert (
        "Model not found for type 'reservoirsimulationrockphysicsmodel',  version '0.0.7'. "
        "Available versions: {'1.0.0'}"
    ) in body["reason"]


@pytest.mark.parametrize("endpoint,args", Endpoints.SCHEMA_VERSION_ENDPOINTS_ARGS)
def test_rsrp_negative_schema_version_overwritten_by_param(api, tests_data, endpoint, args, record_id, dataset_id):
    """Query param content_schema_version takes precedence over Accept header version."""
    method = getattr(api.simulation_rock_physics, endpoint)
    local_vars = locals().copy()
    call_args = [local_vars[name] for name in args]

    kwargs = {
        "allowed_codes": [status.HTTP_404_NOT_FOUND],
        "headers": {ACCEPT: "application/json;version=1.0.0"},
        "raw": True,
    }

    if endpoint == "post_data":
        data_payload = copy.deepcopy(tests_data(DataFiles.SIMULATION_ROCK_PHYSICS_DATA1_V1))
        data_payload["data"][0][0] = f"{record_id}:"
        kwargs["body"] = data_payload

    response = method(schema_version="0.0.7", *call_args, **kwargs)

    # Assert
    assert response.status_code == 404
    body = response.json()
    assert (
        "Model not found for type 'reservoirsimulationrockphysicsmodel',  version '0.0.7'. "
        "Available versions: {'1.0.0'}"
    ) in body["reason"]
