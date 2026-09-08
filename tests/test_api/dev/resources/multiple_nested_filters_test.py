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

import json
import re

import pytest
from pydantic.main import BaseModel

from app.dev.resources.multiple_nested_filters import (
    ColumnsAggregation,
    ColumnsFilter,
    DFMultipleNestedFilterValidator,
    RowsFilter,
)
from app.resources.errors import FilterValidationError


class NestedModel(BaseModel):
    nested_field: str


class Field3(NestedModel): ...


class MockModel(BaseModel):
    Field1: str
    Field2: int
    Field3: NestedModel


class MockModelSameNestedName(BaseModel):
    Field1: str
    Field2: int
    Field3: Field3


def test_valid_columns_filter():
    expected_columns_filter = ColumnsFilter(["Field1", "Field2"])
    validator = DFMultipleNestedFilterValidator(
        MockModel.model_json_schema(),
        raw_columns_filter='["Field1" , "Field2"]',
    )
    assert validator.valid_columns_filter == expected_columns_filter


@pytest.mark.parametrize("raw_columns_filter", ['["Field1", "field4"]', '["Field2,"]'])
def test_valid_columns_filter_invalid_columns(raw_columns_filter):
    validator = DFMultipleNestedFilterValidator(MockModel.model_json_schema(), raw_columns_filter=raw_columns_filter)
    with pytest.raises(FilterValidationError) as exc_info:
        validator.valid_columns_filter
    wrong_column = json.loads(raw_columns_filter)[-1]
    assert (
        str(
            exc_info.value,
        )
        == f"Wrong property name: {wrong_column}. Reason: {wrong_column} not in ['Field1', 'Field2', 'Field3']"
    )


@pytest.mark.parametrize(
    "operator_name,operator_value", [("eq", "="), ("gt", ">"), ("lt", "<"), ("neq", "!="), ("lte", "<="), ("gte", ">=")]
)
def test_valid_rows_filter(operator_name, operator_value):
    expected_rows_filter = RowsFilter("Field1", operator_value, "value1")
    validator = DFMultipleNestedFilterValidator(
        MockModel.model_json_schema(),
        raw_rows_filter=f'{{"Field1": {{"${operator_name}": "value1"}}}}',
    )
    assert validator.valid_rows_filter == expected_rows_filter


@pytest.mark.parametrize(
    "operator_name,operator_value", [("eq", "="), ("gt", ">"), ("lt", "<"), ("neq", "!="), ("lte", "<="), ("gte", ">=")]
)
def test_valid_rows_filter_with_nested_field(operator_name, operator_value):
    expected_rows_filter = RowsFilter("Field3.nested_field", operator_value, "value1")
    nested_validator = DFMultipleNestedFilterValidator(
        MockModelSameNestedName.model_json_schema(),
        raw_rows_filter=f'{{"Field3.nested_field": {{"${operator_name}": "value1"}}}}',
    )
    assert nested_validator.valid_rows_filter == expected_rows_filter


@pytest.mark.parametrize(
    "operator_name,operator_value", [("eq", "="), ("gt", ">"), ("lt", "<"), ("neq", "!="), ("lte", "<="), ("gte", ">=")]
)
def test_valid_rows_filter_with_nested_field_different_name(operator_name, operator_value):
    expected_rows_filter = RowsFilter("Field3.nested_field", operator_value, "value1")
    nested_validator = DFMultipleNestedFilterValidator(
        MockModel.model_json_schema(),
        raw_rows_filter=f'{{"Field3.nested_field": {{"${operator_name}": "value1"}}}}',
    )
    assert nested_validator.valid_rows_filter == expected_rows_filter


def test_valid_rows_filter_invalid_format():
    validator = DFMultipleNestedFilterValidator(MockModel.model_json_schema(), raw_rows_filter="Field1,eq")
    with pytest.raises(FilterValidationError) as exc_info:
        validator.valid_rows_filter
    expected_error_msg = (
        "Bad rows_filter expression. "
        "Correct form {'PropertyX[.PropertyXFieldA]': {'$gt': '{Value}'}}. "
        "Json load error: Expecting value: line 1 column 1 (char 0)"
    )
    assert str(exc_info.value) == expected_error_msg


@pytest.mark.parametrize("aggregation_func", ["mean", "count", "max", "min", "sum", "describe"])
def test_valid_columns_aggregation(aggregation_func):
    expected_columns_aggregation = ColumnsAggregation("Field1", aggregation_func)
    validator = DFMultipleNestedFilterValidator(
        MockModel.model_json_schema(),
        raw_columns_aggregation=f'["Field1", "{aggregation_func}"]',
    )
    assert validator.valid_columns_aggregation == expected_columns_aggregation


@pytest.mark.parametrize("aggregation_func", ["mean", "count", "max", "min", "sum", "describe"])
def test_valid_columns_aggregation_with_nested_field(aggregation_func):
    expected_columns_aggregation = ColumnsAggregation("Field3.nested_field", aggregation_func)
    nested_validator = DFMultipleNestedFilterValidator(
        MockModel.model_json_schema(),
        raw_columns_aggregation=f'["Field3.nested_field", "{aggregation_func}"]',
    )
    assert nested_validator.valid_columns_aggregation == expected_columns_aggregation


def test_valid_columns_aggregation_invalid_format():
    validator = DFMultipleNestedFilterValidator(MockModel.model_json_schema(), raw_columns_aggregation="Field1")
    with pytest.raises(FilterValidationError) as exc_info:
        validator.valid_columns_aggregation
    expected_error_msg = (
        "Bad columns_aggregation expression. Correct form ['ColumnName[.FieldName]', 'function']."
        " Json load error: Expecting value: line 1 column 1 (char 0)"
    )
    assert str(exc_info.value) == expected_error_msg


def test_valid_columns_aggregation_invalid_operator():
    validator = DFMultipleNestedFilterValidator(
        MockModel.model_json_schema(), raw_columns_aggregation='["Field1", "average"]'
    )
    with pytest.raises(FilterValidationError) as exc_info:
        validator.valid_columns_aggregation
    assert re.match(r"Invalid aggregation operator not in: {.+}", str(exc_info.value))


def test_invalid_aggregatiom_dotted_colums():
    nested_aggregation_validator = DFMultipleNestedFilterValidator(
        MockModel.model_json_schema(),
        raw_columns_aggregation='["Field3.", "mean"]',
        raw_rows_filter='{"Field3.": {"$eq": "test"}}',
    )

    with pytest.raises(FilterValidationError) as exc_info:
        nested_aggregation_validator.valid_columns_aggregation
    assert str(exc_info.value) == "Wrong property name: Field3.. Reason:  not in ['nested_field']"

    with pytest.raises(FilterValidationError) as exc_info:
        nested_aggregation_validator.valid_rows_filter
    assert str(exc_info.value) == "Wrong property name: Field3.. Reason:  not in ['nested_field']"
