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
from dataclasses import dataclass
from typing import Any, List, NamedTuple, Optional, Set, Tuple

from loguru import logger
from pydantic.main import BaseModel

from app.resources.errors import FilterValidationError


class Aggregation(NamedTuple):
    FUNCTIONS = {"mean", "count", "max", "min", "sum", "describe"}
    N_ELEMENTS = 2


class Predicate(NamedTuple):
    OPERATORS = {"lt": "<", "gt": ">", "lte": "<=", "gte": ">=", "eq": "=", "neq": "!="}
    N_ELEMENTS = 3


class Separator(NamedTuple):
    DOT = "."
    COMMA = ","


class FilterIndex(NamedTuple):
    COLUMN = 0
    OPERATOR = 1
    COMP_VALUE = 2


class DottedColumn(NamedTuple):
    COLUMN_INDEX = 0
    FIELD_INDEX = 1
    N_ELEMENTS = 2


class RowsFilter(NamedTuple):
    column: str
    operator: str
    comp_value: Any
    field: Optional[str] = None


class ColumnsFilter(NamedTuple):
    colums: List[str]


class ColumnsAggregation(NamedTuple):
    column: str
    function: str
    field: Optional[str] = None


@dataclass
class DataFrameFilterValidator(object):
    """Validation of query paramenters.

    :raises FilterValidationError: If any validation error occurs
    :raises NotImplementedError: For not implemented features
    """
    model: BaseModel
    raw_columns_filter: Optional[str] = None
    raw_rows_filter: Optional[str] = None
    raw_columns_aggregation: Optional[str] = None

    @property
    def all_valid_columns(self) -> Set[str]:
        return set(self.model.__fields__.keys())

    @property
    def valid_columns_filter(self) -> Optional[ColumnsFilter]:
        columns_filter = None
        if self.raw_columns_filter:
            columns_filter = self._validate_columns_filter()
        return columns_filter

    @property
    def valid_rows_filter(self) -> Optional[RowsFilter]:
        rows_filter = None
        if self.raw_rows_filter:
            rows_filter = self._validate_rows_filter()
        return rows_filter

    @property
    def valid_columns_aggregation(self) -> Optional[ColumnsAggregation]:
        columns_aggregation = None
        if self.raw_columns_aggregation:
            columns_aggregation = self._validate_columns_aggregation()
        return columns_aggregation

    def _validate_column_value(self, column: str, comp_value: str, field: Optional[str] = None) -> Any:
        val_type = self._get_type_from_schema(column, field)
        try:
            match val_type:
                case "integer":
                    validated_value = int(comp_value)
                case "number":
                    validated_value = float(comp_value)
                case "boolean":
                    validated_value = comp_value.lower() == "true"
                case "string":
                    validated_value = str(comp_value)
                case _:
                    raise FilterValidationError(f"Filter not supported on {val_type}")
            return validated_value
        except ValueError as exc:
            raise FilterValidationError(exc)

    def _validate_aggregation_func(self, agg_func: str) -> str:
        if agg_func not in Aggregation.FUNCTIONS:
            raise FilterValidationError(f"Invalid aggregation operator not in: {Aggregation.FUNCTIONS}")
        return agg_func

    def _validate_comparison_operator(self, operator: str) -> str:
        operator = Predicate.OPERATORS.get(operator)
        if not operator:
            possible_operators = Predicate.OPERATORS.keys()
            raise FilterValidationError(f"Invalid comparison operator not in: {possible_operators}")
        return operator

    def _validate_rows_filter(self) -> RowsFilter:
        rows_filter_list = self.raw_rows_filter.split(Separator.COMMA)
        if len(rows_filter_list) != Predicate.N_ELEMENTS:
            raise FilterValidationError(
                "Bad rows_filter expression. Correct form 'ColumnName[.FieldName],operator,value'",
            )

        valid_column, valid_field = self._validate_column(rows_filter_list[FilterIndex.COLUMN], "filter")
        valid_operator = self._validate_comparison_operator(rows_filter_list[FilterIndex.OPERATOR])
        valid_value = self._validate_column_value(
            valid_column, rows_filter_list[FilterIndex.COMP_VALUE], valid_field,
        )
        return RowsFilter(column=valid_column, operator=valid_operator, comp_value=valid_value, field=valid_field)

    def _validate_columns_aggregation(self) -> ColumnsAggregation:
        columns_aggregation_list = self.raw_columns_aggregation.split(Separator.COMMA)
        if len(columns_aggregation_list) != Aggregation.N_ELEMENTS:
            raise FilterValidationError("Bad aggregation expression. Correct form 'ColumnName[.FieldName],operator'")

        valid_column, valid_field = self._validate_column(columns_aggregation_list[FilterIndex.COLUMN], "aggregation")
        valid_func = self._validate_aggregation_func(columns_aggregation_list[FilterIndex.OPERATOR])
        return ColumnsAggregation(column=valid_column, function=valid_func, field=valid_field)

    def _validate_columns_filter(self) -> ColumnsFilter:
        raw_columns_filter = self.raw_columns_filter.split(Separator.COMMA)
        valid_columns = [raw_column for raw_column in raw_columns_filter if raw_column in self.all_valid_columns]
        invalid_columns = set(raw_columns_filter) - set(valid_columns)
        if invalid_columns:
            raise FilterValidationError(f"Invalid columns: {invalid_columns}. Select one of {self.all_valid_columns}")
        return ColumnsFilter(colums=valid_columns)

    def _validate_column(self, full_column_name: str, operation: str) -> Tuple[str, str]:
        column_name, field_name = full_column_name, None
        if Separator.DOT in full_column_name:
            logger.debug(f"DOT in column: {full_column_name}")
            dot_cols = full_column_name.split(Separator.DOT)
            column_name = dot_cols[DottedColumn.COLUMN_INDEX]
            field_name = dot_cols[DottedColumn.FIELD_INDEX]
            if len(dot_cols) != DottedColumn.N_ELEMENTS or not re.match(r"\w+", field_name):
                raise FilterValidationError("Wrong Column or Field name syntax: correct form: {ColumnName.FieldName}")
            if column_name not in self.all_valid_columns:
                raise FilterValidationError(f"For {operation} select one of {self.all_valid_columns}")
        elif full_column_name not in self.all_valid_columns:
            raise FilterValidationError(f"For {operation} column select one of {self.all_valid_columns}")

        return column_name, field_name

    def _get_type_from_schema(self, column: str, field: Optional[str] = None) -> str:
        column_definition = self._get_column_definition_from_schema(column)
        value_type = column_definition.get("type")

        if field:
            props = column_definition.get("properties", {})
            value_type = props.get(field, {}).get("type")
            if not value_type:
                error_msg = f"'{field}' is not defined in the {column} schema: {props}."
                logger.debug(error_msg)
                raise FilterValidationError(error_msg)
        return value_type

    def _get_column_definition_from_schema(self, column: str) -> dict:
        schema = self.model.schema()

        schema_column_by_def = schema.get("definitions", {}).get(column, {})
        schema_column_by_prop = schema.get("properties", {}).get(column, {})

        if schema_column_by_def.get("type"):
            column_definition = schema_column_by_def
        elif schema_column_by_prop.get("type"):
            column_definition = schema_column_by_prop
        else:
            # verify if the property has a different definition name
            def_name_index = -1
            def_name = schema_column_by_prop.get("$ref", "").split("/")[def_name_index]
            column_definition = schema.get("definitions", {}).get(def_name, {})

        return column_definition
