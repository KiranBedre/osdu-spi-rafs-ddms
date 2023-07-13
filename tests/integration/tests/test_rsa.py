#  Copyright 2023 ExxonMobil Technology and Engineering Company
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


import pytest
from starlette import status

from tests.integration.config import DataFiles, DataTemplates, DataTypes


@pytest.mark.smoke
@pytest.mark.parametrize(
    "rows_filter, expected_result",
    [
        (
            "RockSampleID,eq,opendes:master-data--RockSample:1:",
            [["opendes:master-data--RockSample:1:"]],
        ),  # exact match
        (
            "CoringID,neq,opendes:master-data--Coring:1:",
            [["opendes:master-data--Coring:2:"]],
        ),  # not equal
        pytest.param(
            "SampleDepth.Value,gt,10", [[{
                "UnitOfMeasure": "opendes:reference-data--UnitOfMeasure:M:",
                "Value": 346.0,
            }]],
            marks=[pytest.mark.xfail(reason="XOMROCK-563")],
        ),  # greater than
        pytest.param(
            "Permeability.Value,gte,1", [[1], [1]],
            marks=[pytest.mark.xfail(reason="XOMROCK-563")],
        ),  # greater than or equal to
        pytest.param(
            "Porosity.Value,lt,100", [[89.0, 56.5]],
            marks=[pytest.mark.xfail(reason="XOMROCK-563")],
        ),  # less than
        pytest.param(
            "GrainDensity.Value,lte,10", [[10], [1.3]],
            marks=[pytest.mark.xfail(reason="XOMROCK-563")],
        ),  # less than or equal to
    ],
    ids=[
        "RockSampleID_eq",
        "CoringID_neq",
        "SampleDepth_gt",
        "Permeability_gte",
        "Porosity_lt",
        "GrainDensity_lte",
    ],
)
@pytest.mark.parametrize(
    "data_file_name, measurements_file, api_path, id_template", [
        (DataFiles.RSA, DataFiles.RCA, DataTypes.RSA, DataTemplates.ID_RSA),
    ], ids=["RSA"],
)
def test_measurements_filters_positive(
    api, helper, tests_data, create_record, rows_filter, expected_result, data_file_name,
    measurements_file, api_path, id_template,
):
    record_data, created_record = create_record(api_path, data_file_name, id_template)

    full_dataset_id = getattr(api, api_path).post_measurements(
        record_data["id"], tests_data(measurements_file),
    )["ddms_urn"]
    dataset_id = helper.get_dataset_id_from_ddms_urn(full_dataset_id)

    columns_filter = rows_filter.split(",")[0].split(".")[0]  # column name only
    response = getattr(api, api_path).get_measurements(
        record_data["id"],
        dataset_id,
        columns_filter=columns_filter,
        rows_filter=rows_filter,
    )

    assert response["columns"] == [columns_filter], "Wrong columns value"
    assert response["data"] == expected_result, "Wrong filtration"


@pytest.mark.smoke
@pytest.mark.parametrize(
    "column, operator, expected_result", [
        ("SampleDepth", "count", [[2]]),
        ("SampleDepth.Value", "min", [[5.44]]),
        ("SampleDepth.Value", "mean", [[175.72]]),
    ],
    ids=[
        "SampleDepth_count",
        "SampleDepth_min",
        "SampleDepth_mean",
    ],
)
@pytest.mark.parametrize(
    "data_file_name, measurements_file, api_path, id_template", [
        (DataFiles.RSA, DataFiles.RCA, DataTypes.RSA, DataTemplates.ID_RSA),
    ], ids=["RSA"],
)
def test_measurements_aggregation_positive(
    api, helper, tests_data, create_record, column, operator, expected_result,
    data_file_name, measurements_file, api_path, id_template,
):
    record_data, created_record = create_record(api_path, data_file_name, id_template)

    full_dataset_id = getattr(api, api_path).post_measurements(
        record_data["id"], tests_data(measurements_file),
    )["ddms_urn"]
    dataset_id = helper.get_dataset_id_from_ddms_urn(full_dataset_id)

    print("column", column)
    response = getattr(api, api_path).get_measurements(
        record_data["id"],
        dataset_id,
        columns_aggregation=",".join([column, operator]),
    )

    assert response["data"] == expected_result, "Wrong aggregation"


@pytest.mark.smoke
@pytest.mark.parametrize(
    "columns_filter, rows_filter, expected_result, status_code",
    [
        (
            ["WrongColumn"],
            ["SampleDepth,gt,"],
            "Invalid columns: {'WrongColumn'}. Select one of",
            status.HTTP_400_BAD_REQUEST,
        ),

        (
            None,
            [
                "SampleDepth", "SampleDepth,gt", "SampleDepth,gt.", "SampleDepth.gt,", "SampleDepth.gt.",
                "SampleDepth gt,", ",SampleDepth,gt,",
            ],
            "Bad rows_filter expression. Correct form 'ColumnName[.FieldName],operator,value'",
            status.HTTP_400_BAD_REQUEST,
        ),
        (
            None,
            ["SampleDepth.,gt,"],
            "Wrong Column or Field name syntax: correct form: {ColumnName.FieldName}",
            status.HTTP_400_BAD_REQUEST,
        ),
        (
            None,
            ["SampleDepth,gt.,", "SampleDepth,.gt,", "SampleDepth,GT,", "SampleDepth,qq,", "SampleDepth,>,"],
            "Invalid comparison operator not in:",
            status.HTTP_400_BAD_REQUEST,
        ),
        (
            None,
            ["WrongColumn,gt,"],
            "For filter column select one of",
            status.HTTP_400_BAD_REQUEST,
        ),
        (
            None,
            ["SampleDepth.WrongFieldName,gt,"],
            "'WrongFieldName' is not defined in the SampleDepth schema:",
            status.HTTP_400_BAD_REQUEST,
        ),
    ],
    ids=[
        "Invalid_columns",
        "Bad_rows_filter",
        "Wrong_column_dotted_name",
        "Invalid_operator",
        "Wrong_filter_column",
        "Wrong_field_name",
    ],
)
@pytest.mark.parametrize(
    "data_file_name, measurements_file, api_path, id_template", [
        (DataFiles.RSA, DataFiles.RCA, DataTypes.RSA, DataTemplates.ID_RSA),
    ], ids=["RSA"],
)
def test_filters_syntax_error(
    api, helper, tests_data, create_record, columns_filter, rows_filter, expected_result, status_code,
    data_file_name,
    measurements_file, api_path, id_template,
):
    record_data, created_record = create_record(api_path, data_file_name, id_template)

    full_dataset_id = getattr(api, api_path).post_measurements(
        record_data["id"], tests_data(measurements_file),
    )["ddms_urn"]
    dataset_id = helper.get_dataset_id_from_ddms_urn(full_dataset_id)

    for row_filter in rows_filter:
        response = getattr(api, api_path).get_measurements(
            record_data["id"],
            dataset_id,
            columns_filter=columns_filter if columns_filter else None,
            rows_filter=row_filter,
            allowed_codes=[status_code],
        )

        assert expected_result in response["reason"], f"\nWrong error message: \n{row_filter=}\n{expected_result=}\n"


@pytest.mark.smoke
@pytest.mark.parametrize(
    "columns_aggregation, expected_result, status_code",
    [
        (
            ["SampleDepth", "SampleDepth.", ".SampleDepth.", "SampleDepth,min,.", "SampleDepth,max,123"],
            "Bad aggregation expression. Correct form 'ColumnName[.FieldName],operator'",
            status.HTTP_400_BAD_REQUEST,
        ),
        (
            ["SampleDepth.,max"],
            "Wrong Column or Field name syntax: correct form: {ColumnName.FieldName}",
            status.HTTP_400_BAD_REQUEST,
        ),
        (
            ["SampleDepth,", "SampleDepth.min,", "SampleDepth,ma", "SampleDepth,>"],
            "Invalid aggregation operator not in:",
            status.HTTP_400_BAD_REQUEST,
        ),
        (
            ["WrongColumn,max"],
            "For aggregation column select one of",
            status.HTTP_400_BAD_REQUEST,
        ),
        (
            ["SampleDepth.WrongFieldName,max"],
            "Processing filter exception (<class 'KeyError'>): 'WrongFieldName'",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ),
    ],
    ids=[
        "Bad_aggregation_expression",
        "Wrong_column_dotted_name",
        "Invalid_operator",
        "Wrong_aggregation_column",
        "Wrong_field_name",
    ],
)
@pytest.mark.parametrize(
    "data_file_name, measurements_file, api_path, id_template", [
        (DataFiles.RSA, DataFiles.RCA, DataTypes.RSA, DataTemplates.ID_RSA),
    ], ids=["RSA"],
)
def test_aggregation_syntax_error(
    api, helper, tests_data, create_record, columns_aggregation, expected_result, status_code,
    data_file_name, measurements_file, api_path, id_template,
):
    record_data, created_record = create_record(api_path, data_file_name, id_template)

    full_dataset_id = getattr(api, api_path).post_measurements(
        record_data["id"], tests_data(measurements_file),
    )["ddms_urn"]
    dataset_id = helper.get_dataset_id_from_ddms_urn(full_dataset_id)

    for aggregation in columns_aggregation:
        response = getattr(api, api_path).get_measurements(
            record_data["id"],
            dataset_id,
            columns_aggregation=aggregation,
            allowed_codes=[status_code],
        )

        assert expected_result in response["reason"], f"\nWrong error message: \n{aggregation=}\n{expected_result=}\n"
