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

from dataclasses import dataclass
from typing import Any, Dict, List, NamedTuple, Optional, Set, Tuple

from loguru import logger
from pydantic.main import BaseModel

from app.resources.errors import FilterValidationError
from app.resources.model_to_schema import build_normalized_schema_from_model


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


true_values = {"true", "1"}
false_values = {"false", "0"}


def parse_bool(str_value: str) -> bool:
    stripped_value = str_value.strip().lower()
    if stripped_value in true_values:
        return True
    if stripped_value in false_values:
        return False
    raise ValueError(f"Invalid boolean string: {str_value!r}")


@dataclass
class DataFrameFilterValidator(object):
    """Validation of query parameters for DataFrame-style filters."""

    model: BaseModel
    raw_columns_filter: Optional[str] = None
    raw_rows_filter: Optional[str] = None
    raw_columns_aggregation: Optional[str] = None

    def __post_init__(self) -> None:
        self._schema: Dict[str, Any] = build_normalized_schema_from_model(self.model)

    @property
    def all_valid_columns(self) -> Set[str]:
        return set(self._schema.get("properties", {}).keys())

    @property
    def valid_rows_filter(self) -> Optional[RowsFilter]:
        return self._validate_rows_filter() if self.raw_rows_filter else None

    @property
    def valid_columns_filter(self) -> Optional[ColumnsFilter]:
        return self._validate_columns_filter() if self.raw_columns_filter else None

    @property
    def valid_columns_aggregation(self) -> Optional[ColumnsAggregation]:
        return self._validate_columns_aggregation() if self.raw_columns_aggregation else None

    def _validate_column_value(self, column: str, comp_value: str, field: Optional[str]) -> Any:
        value_type = self._get_type_from_schema(column, field)

        casted_result = None
        error = None
        match value_type:
            case "integer":
                try:
                    casted_result = int(comp_value)
                except ValueError:
                    error = f"Wrong type for value: '{comp_value}'. Expected type: '{value_type}'"
            case "number":
                try:
                    casted_result = float(comp_value)
                except ValueError:
                    error = f"Wrong type for value: '{comp_value}'. Expected type: '{value_type}'"
            case "boolean":
                try:
                    casted_result = comp_value.lower() == "true"
                except ValueError:
                    error = f"Expected boolean values: {true_values} {false_values}"
            case "string":
                casted_result = comp_value
            case _:
                raise FilterValidationError(
                    "".join([
                        f"Filtering not supported on type '{value_type}' ",
                        f"for '{column}{'.' + field if field else ''}'.",  # noqa: WPS529, WPS237, WPS336
                    ]),
                )
        if error:
            raise FilterValidationError(error)
        return casted_result

    def _validate_comparison_operator(self, operator: str) -> str:
        op = Predicate.OPERATORS.get(operator)
        if not op:
            allowed = list(Predicate.OPERATORS.keys())
            raise FilterValidationError(
                "".join([
                    f"Invalid comparison operator '{operator}'. ",
                    f"Allowed: {allowed}",
                ]),
            )
        return op

    def _validate_rows_filter(self) -> RowsFilter:
        parts = self.raw_rows_filter.split(Separator.COMMA)
        if len(parts) != Predicate.N_ELEMENTS:
            raise FilterValidationError(
                "Bad rows_filter expression. Correct format: 'Column[.Field],operator,value'",
            )

        full_column, operator, raw_value = parts

        column, field = self._validate_column(full_column, "filter")
        operator = self._validate_comparison_operator(operator)
        comp_value = self._validate_column_value(column, raw_value, field)

        return RowsFilter(column=column, operator=operator, comp_value=comp_value, field=field)

    def _validate_column(  # noqa: WPS238, CCR001
        self,
        full_column_name: str,
        operation: str,
    ) -> Tuple[str, Optional[str]]:
        if "[]" in full_column_name:
            logger.debug("Array filtering syntax detected but not yet supported. Trimming [].")
            full_column_name = full_column_name.replace("[]", "")

        # No dot: plain column
        if Separator.DOT not in full_column_name:
            if full_column_name not in self.all_valid_columns:
                raise FilterValidationError(
                    f"For {operation} select one of {self.all_valid_columns}",
                )
            return full_column_name, None

        # Dotted column: <Column>.<Field>
        logger.debug(f"DOT in column: {full_column_name}")
        dot_cols = full_column_name.split(Separator.DOT)
        if len(dot_cols) != DottedColumn.N_ELEMENTS:
            raise FilterValidationError(
                "Wrong Column or Field name syntax: correct form: {ColumnName.FieldName}",
            )

        column_name = dot_cols[DottedColumn.COLUMN_INDEX]
        field_name = dot_cols[DottedColumn.FIELD_INDEX]

        if column_name not in self.all_valid_columns:
            raise FilterValidationError(
                f"For {operation} select one of {self.all_valid_columns}",
            )

        column_schema = self._get_column_definition_from_schema(column_name)
        col_type = column_schema.get("type")

        if col_type == "array":
            raise FilterValidationError(
                "".join([
                    f"Column '{column_name}' is an array; dotted field access ",
                    f"('{column_name}.{field_name}') is not supported.",
                ]),
            )
        if col_type != "object":
            raise FilterValidationError(
                "".join([
                    f"Column '{column_name}' is of type '{col_type}', dotted syntax ",
                    "requires an object column.",
                ]),
            )

        properties = column_schema.get("properties", {})
        if field_name not in properties:
            raise FilterValidationError(
                "".join([
                    f"Field '{field_name}' does not exist in column '{column_name}'. ",
                    f"Available fields: {list(properties.keys())}",  # noqa: WPS237
                ]),
            )

        return column_name, field_name

    def _get_type_from_schema(self, column: str, field: Optional[str]) -> str:
        column_schema = self._get_column_definition_from_schema(column)

        if field:
            props = column_schema.get("properties", {})
            field_schema = props.get(field, {})
            value_type = field_schema.get("type")
            if not value_type:
                raise FilterValidationError(
                    f"'{field}' is not defined in the '{column}' schema: {field_schema}.",
                )
            return value_type

        return column_schema.get("type")

    def _get_column_definition_from_schema(self, column: str) -> Dict[str, Any]:
        """
        Use the fully normalized schema to get the definition of a top-level property.
        """
        props = self._schema.get("properties", {})
        column_schema = props.get(column, {})

        if not column_schema:
            raise FilterValidationError(f"Schema definition not found for column '{column}'.")

        return column_schema

    def _validate_columns_filter(self) -> ColumnsFilter:
        raw_columns_filter = self.raw_columns_filter.split(Separator.COMMA)
        valid_columns = [col for col in raw_columns_filter if col in self.all_valid_columns]
        invalid_columns = set(raw_columns_filter) - set(valid_columns)
        if invalid_columns:
            raise FilterValidationError(
                f"Invalid columns: {invalid_columns}. Select one of {self.all_valid_columns}",
            )
        return ColumnsFilter(colums=valid_columns)

    def _validate_columns_aggregation(self) -> ColumnsAggregation:
        parts = self.raw_columns_aggregation.split(Separator.COMMA)
        if len(parts) != Aggregation.N_ELEMENTS:
            raise FilterValidationError(
                "Bad aggregation expression. Correct form 'Column[.Field],operator'",
            )

        expr, func = parts
        column, field = self._validate_column(expr, "aggregation")

        if func not in Aggregation.FUNCTIONS:
            allowed = list(Aggregation.FUNCTIONS)
            raise FilterValidationError(
                f"Invalid aggregation operator '{func}'. Allowed: {allowed}",
            )

        return ColumnsAggregation(column=column, function=func, field=field)
