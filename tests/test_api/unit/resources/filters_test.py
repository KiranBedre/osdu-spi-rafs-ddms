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

import re

import pytest
from pydantic.main import BaseModel

from app.resources.errors import FilterValidationError
from app.resources.filters import (
    ColumnsAggregation,
    ColumnsFilter,
    DataFrameFilterValidator,
    RowsFilter,
)


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
    validator = DataFrameFilterValidator(MockModel, raw_columns_filter="Field1,Field2")
    assert validator.valid_columns_filter == expected_columns_filter


@pytest.mark.parametrize("raw_columns_filter", ["Field1,field4", "Field2,"])
def test_valid_columns_filter_invalid_columns(raw_columns_filter):
    validator = DataFrameFilterValidator(MockModel, raw_columns_filter=raw_columns_filter)
    with pytest.raises(FilterValidationError) as exc_info:
        validator.valid_columns_filter
    assert re.match(r"Invalid columns: {'.*'}. Select one of {.+}", str(exc_info.value))


@pytest.mark.parametrize(
    "operator_name,operator_value", [("eq", "="), ("gt", ">"), ("lt", "<"), ("neq", "!="), ("lte", "<="), ("gte", ">=")]
)
def test_valid_rows_filter(operator_name, operator_value):
    expected_rows_filter = RowsFilter("Field1", operator_value, "value1")
    validator = DataFrameFilterValidator(MockModel, raw_rows_filter=f"Field1,{operator_name},value1")
    assert validator.valid_rows_filter == expected_rows_filter


@pytest.mark.parametrize(
    "operator_name,operator_value", [("eq", "="), ("gt", ">"), ("lt", "<"), ("neq", "!="), ("lte", "<="), ("gte", ">=")]
)
def test_valid_rows_filter_with_nested_field(operator_name, operator_value):
    expected_rows_filter = RowsFilter("Field3", operator_value, "value1", "nested_field")
    nested_validator = DataFrameFilterValidator(
        MockModelSameNestedName,
        raw_rows_filter=f"Field3.nested_field,{operator_name},value1",
    )
    assert nested_validator.valid_rows_filter == expected_rows_filter


@pytest.mark.parametrize(
    "operator_name,operator_value", [("eq", "="), ("gt", ">"), ("lt", "<"), ("neq", "!="), ("lte", "<="), ("gte", ">=")]
)
def test_valid_rows_filter_with_nested_field_different_name(operator_name, operator_value):
    expected_rows_filter = RowsFilter("Field3", operator_value, "value1", "nested_field")
    nested_validator = DataFrameFilterValidator(
        MockModel,
        raw_rows_filter=f"Field3.nested_field,{operator_name},value1",
    )
    assert nested_validator.valid_rows_filter == expected_rows_filter


def test_valid_rows_filter_invalid_format():
    validator = DataFrameFilterValidator(MockModel, raw_rows_filter="Field1,eq")
    with pytest.raises(FilterValidationError) as exc_info:
        validator.valid_rows_filter
    assert str(exc_info.value) == "Bad rows_filter expression. Correct format: 'Column[.Field],operator,value'"


@pytest.mark.parametrize("aggregation_func", ["mean", "count", "max", "min", "sum", "describe"])
def test_valid_columns_aggregation(aggregation_func):
    expected_columns_aggregation = ColumnsAggregation("Field1", aggregation_func)
    validator = DataFrameFilterValidator(MockModel, raw_columns_aggregation=f"Field1,{aggregation_func}")
    assert validator.valid_columns_aggregation == expected_columns_aggregation


@pytest.mark.parametrize("aggregation_func", ["mean", "count", "max", "min", "sum", "describe"])
def test_valid_columns_aggregation_with_nested_field(aggregation_func):
    expected_columns_aggregation = ColumnsAggregation("Field3", aggregation_func, "nested_field")
    nested_validator = DataFrameFilterValidator(
        MockModel,
        raw_columns_aggregation=f"Field3.nested_field,{aggregation_func}",
    )
    assert nested_validator.valid_columns_aggregation == expected_columns_aggregation


def test_valid_columns_aggregation_invalid_format():
    validator = DataFrameFilterValidator(MockModel, raw_columns_aggregation="Field1")
    with pytest.raises(FilterValidationError) as exc_info:
        validator.valid_columns_aggregation
    assert str(exc_info.value) == "Bad aggregation expression. Correct form 'Column[.Field],operator'"


def test_valid_columns_aggregation_invalid_operator():
    validator = DataFrameFilterValidator(MockModel, raw_columns_aggregation="Field1,average")
    with pytest.raises(FilterValidationError) as exc_info:
        validator.valid_columns_aggregation
    assert re.match(r"Invalid aggregation operator 'average'\. Allowed: \[.+\]", str(exc_info.value))


def test_invalid_aggregatiom_dotted_colums():
    nested_aggregation_validator = DataFrameFilterValidator(
        MockModel,
        raw_columns_aggregation="Field3.,mean",
        raw_rows_filter="Field3.,eq,test",
    )

    with pytest.raises(FilterValidationError) as exc_info:
        nested_aggregation_validator.valid_columns_aggregation
    assert str(exc_info.value) == "Field '' does not exist in column 'Field3'. Available fields: ['nested_field']"

    with pytest.raises(FilterValidationError) as exc_info:
        nested_aggregation_validator.valid_rows_filter
    assert str(exc_info.value) == "Field '' does not exist in column 'Field3'. Available fields: ['nested_field']"


def test_validate_combination_conflict():
    validator = DataFrameFilterValidator(
        MockModel,
        raw_columns_filter="Field1,Field2",
        raw_columns_aggregation="Field3,mean",
    )
    with pytest.raises(FilterValidationError) as exc_info:
        validator.validate_combination()
    assert "Filter conflict" in str(exc_info.value)
    assert "Field3" in str(exc_info.value)
    assert "columns_filter" in str(exc_info.value)


def test_validate_combination_no_conflict():
    validator = DataFrameFilterValidator(
        MockModel,
        raw_columns_filter="Field1,Field3",
        raw_columns_aggregation="Field3,mean",
    )
    validator.validate_combination()  # should not raise


def test_validate_combination_only_filter():
    validator = DataFrameFilterValidator(MockModel, raw_columns_filter="Field1,Field2")
    validator.validate_combination()  # should not raise


def test_validate_combination_only_aggregation():
    validator = DataFrameFilterValidator(MockModel, raw_columns_aggregation="Field1,mean")
    validator.validate_combination()  # should not raise
