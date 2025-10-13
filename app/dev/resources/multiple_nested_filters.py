#  Copyright 2024 ExxonMobil Technology and Engineering Company
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
from dataclasses import dataclass
from typing import Any, Dict, List, NamedTuple, Optional, Set

import jsonref
from loguru import logger

from app.resources.errors import FilterValidationError


class Aggregation(object):
    FUNCTIONS = {"mean", "count", "max", "min", "sum", "describe"}
    N_ELEMENTS = 2


class LogicalOperators(object):
    OR = "$or"
    AND = "$and"


class Predicate(object):
    OPERATORS = {"$lt": "<", "$gt": ">", "$lte": "<=", "$gte": ">=", "$eq": "=", "$neq": "!="}
    N_ELEMENTS = 3
    LOGICAL_OPERATORS = {LogicalOperators.OR, LogicalOperators.AND}


class Separator(object):
    DOT = "."
    COMMA = ","
    ARRAY = "[]"


class FilterExamples(object):
    PREDICATE = {
        "PropertyX[.PropertyXFieldA]": {
            "$gt": "{Value}",
        },
    }
    AGGREGATION = ["ColumnName[.FieldName]", "function"]
    PROJECTION = ["ColumnName1[.FieldName1]", "ColumnName2[.FieldName2]"]
    LOGICAL_PREDICATE = {
        "$and": [
            {
                "PropertyX[.PropertyXFieldA]": {
                    "$gt": "{Value}",
                },
            },
            {
                "$or": [
                    {
                        "PropertyY[.PropertyYFieldB]": {
                            "$eq": "{Value}",
                        },
                    },
                    {
                        "PropertyZ[.PropertyZFieldC]": {
                            "$le": "{Value}",
                        },
                    },
                ],
            },
        ],
    }


class FilterErrorMessage(object):
    ROWS_FILTER = f"Bad rows_filter expression. Correct form {FilterExamples.PREDICATE}"
    COLUMNS_AGGREGATION = f"Bad columns_aggregation expression. Correct form {FilterExamples.AGGREGATION}"
    COLUMNS_FILTER = f"Bad columns expression. Correct form {FilterExamples.PROJECTION}"
    ROWS_MULTIPLE_FILTER = f"Bad rows_multiple_filter expression. Correct form {FilterExamples.LOGICAL_PREDICATE}"


class FilterIndex(object):
    COLUMN_OR_PROP_NAME = 0
    OPERATOR = 1
    COMP_VALUE = 2


class PropertyInfo(NamedTuple):
    name: str
    type: str


class RowsFilter(NamedTuple):
    column: str
    operator: str
    comp_value: Any


class RowsMultipleFilter(NamedTuple):
    conditions: dict


class ColumnsFilter(NamedTuple):
    columns: List[str]


class ColumnsAggregation(NamedTuple):
    column: str
    function: str


@dataclass
class DFMultipleNestedFilterValidator(object):
    """Validation of query paramenters.

    :raises FilterValidationError: If any validation error occurs
    :raises NotImplementedError: For not implemented features
    """
    schema: Optional[Dict[str, Any]] = None
    raw_columns_filter: Optional[str] = None
    raw_rows_filter: Optional[str] = None
    raw_columns_aggregation: Optional[str] = None
    raw_rows_multiple_filter: Optional[str] = None

    def __post_init__(self):
        self._expanded_schema = jsonref.loads(json.dumps(self.schema))
        self._prop_processor = PropertyInfoProcessor(self._expanded_schema)
        self._rows_filter_validator = RowsFilterValidator(self._prop_processor)
        self._columns_aggregation_validator = ColumnsAggregationValidator(self._prop_processor)
        self._columns_filter_validator = ColumnsFilterValidator(self._prop_processor)

    @property
    def all_valid_columns(self) -> Set[str]:
        return set(self._expanded_schema["properties"].keys())

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
    def valid_rows_multiple_filter(self) -> Optional[dict]:
        rows_multiple_filter = None
        if self.raw_rows_multiple_filter:
            rows_multiple_filter = self._validate_rows_multiple_filter()
        return rows_multiple_filter

    @property
    def valid_columns_aggregation(self) -> Optional[ColumnsAggregation]:
        columns_aggregation = None
        if self.raw_columns_aggregation:
            columns_aggregation = self._validate_columns_aggregation()
        return columns_aggregation

    def _get_filter_from_json_str(self, json_str: str, error_str: str) -> Dict:
        try:
            return json.loads(json_str)
        except json.decoder.JSONDecodeError as exc:
            full_error_string = f"{error_str}. Json load error: {exc}"
            logger.error(full_error_string)
            raise FilterValidationError(full_error_string)

    def _validate_rows_filter(self) -> RowsFilter:
        rows_filter_dict = self._get_filter_from_json_str(
            self.raw_rows_filter, FilterErrorMessage.ROWS_FILTER,
        )
        return self._rows_filter_validator.validate(rows_filter_dict)

    def _validate_rows_multiple_filter(self) -> RowsFilter:
        rows_mutiple_filter_dict = self._get_filter_from_json_str(
            self.raw_rows_multiple_filter, FilterErrorMessage.ROWS_MULTIPLE_FILTER,
        )
        return self._rows_filter_validator.validate_multiple_filter(rows_mutiple_filter_dict)

    def _validate_columns_aggregation(self) -> ColumnsAggregation:
        columns_aggregation_list = self._get_filter_from_json_str(
            self.raw_columns_aggregation, FilterErrorMessage.COLUMNS_AGGREGATION,
        )
        return self._columns_aggregation_validator.validate(columns_aggregation_list)

    def _validate_columns_filter(self) -> ColumnsFilter:
        columns_filter_list = self._get_filter_from_json_str(
            self.raw_columns_filter, FilterErrorMessage.COLUMNS_FILTER,
        )
        return self._columns_filter_validator.validate(columns_filter_list)


class PropertyInfoProcessor(object):

    def __init__(self, schema: dict):
        self._schema = schema

    def get_prop_info(self, flatten_prop_name: str) -> PropertyInfo:
        """Traverses the schema to get the property info.

        :param flatten_prop_name: the flatten property name
        :type flatten_prop_name: str
        :raises KeyError: when a property does not exist in the schema
        :raises FilterValidationError: with the full description of the
            KeyError
        :return: the property info
        :rtype: PropertyInfo
        """
        prop_schema = self._schema
        prop_names = []
        for prop_name in flatten_prop_name.split(Separator.DOT):
            try:
                prop_schema = self._handle_jsonschema_refs(prop_schema)
                prop_type = prop_schema["type"]
                if prop_type == "object":
                    prop_schema = prop_schema["properties"][prop_name]
                    prop_names.append(prop_name)
                elif prop_type == "array":
                    prop_names[-1] = f"{prop_names[-1]}[]"  # noqa: WPS237
                    prop_schema = prop_schema["items"]["properties"][prop_name]
                    prop_names.append(f"{prop_name}")
                else:
                    raise KeyError(f"Extra property: {prop_name}")
            except KeyError:
                schema_props = prop_schema.get("properties") or prop_schema.get(
                    "items", {},
                ).get("properties") or prop_schema
                valid_schema_keys = list(schema_props.keys())
                raise FilterValidationError(
                    f"Wrong property name: {flatten_prop_name}. Reason: {prop_name} not in {valid_schema_keys}",
                )
        return PropertyInfo(name=Separator.DOT.join(prop_names), type=prop_schema.get("type"))

    def _handle_jsonschema_refs(self, prop_schema: dict):
        if "allOf" in prop_schema:
            new_prop_schema = {}
            for schema in prop_schema.get("allOf"):
                new_prop_schema.update(schema)
            prop_schema = new_prop_schema
        return prop_schema


class RowsFilterValidator(object):

    VALID_FILTER: str = "valid_filter"

    def __init__(self, prop_processor: PropertyInfoProcessor):
        self._prop_processor = prop_processor

    def validate(self, row_filter_condition: dict) -> RowsFilter:
        """Validates single row filter condition.

        :param condition: a dictionary with row filter condition
        :type condition: dict
        :raises FilterValidationError: when condition format does not
            meet criteria
        :return: validated rows filter
        :rtype: RowsFilter
        """

        if not isinstance(row_filter_condition, dict) or not self._is_predicate(row_filter_condition):
            raise FilterValidationError(
                f"{FilterErrorMessage.ROWS_FILTER}. Must be a dict. Example {FilterExamples.PREDICATE}",
            )

        property_name = next(iter(row_filter_condition.keys()))
        prop_info = self._prop_processor.get_prop_info(property_name)
        comparison_obj = next(iter(row_filter_condition.values()))
        operator = next(iter(comparison_obj.keys()))
        valid_operator = self._validate_comparison_operator(operator)
        valid_value = self._validate_column_value(comparison_obj[operator], prop_info.type)

        return RowsFilter(column=prop_info.name, operator=valid_operator, comp_value=valid_value)

    def validate_multiple_filter(self, row_filter_conditions: dict) -> RowsMultipleFilter:
        """Validate a set of conditions nested with $and and $or operands.

        :param row_filter_conditions: the dictionary with multiple
            conditions
        :type row_filter_conditions: dict
        :raises FilterValidationError: when the dicionary does not meet
            the accepted format
        :return: validated condition dictionary
        :rtype: RowsMultipleFilter
        """
        validated_row_filter_conditions = {}
        stack = [(row_filter_conditions, validated_row_filter_conditions)]
        while stack:
            current_condition, validated_condition = stack.pop()
            self._validate_condition_format(current_condition)

            if self._is_predicate(current_condition):
                validated_condition.update({self.VALID_FILTER: self.validate(current_condition)})
            elif self._is_logical_oper(current_condition):
                self._handle_logical_oper(current_condition, validated_condition, stack)

        return RowsMultipleFilter(conditions=validated_row_filter_conditions)

    def _handle_logical_oper(self, current_condition: dict, validated_condition: dict, stack: list):
        current_op = self._get_operator(current_condition)
        validated_condition[current_op] = []
        new_conditions = current_condition[current_op]

        if not new_conditions or not isinstance(new_conditions, list):
            raise FilterValidationError(f"{current_condition}. Operator content should be a non-empty array.")

        for index, new_condition in enumerate(new_conditions):
            self._validate_condition_format(new_condition)
            validated_condition[current_op].append({})
            stack.append((new_condition, validated_condition[current_op][index]))

    def _validate_condition_format(self, condition: Any):
        if not isinstance(condition, dict):
            error_msg = f"Must be a dict. {FilterErrorMessage.ROWS_MULTIPLE_FILTER}"
            logger.error(error_msg)
            raise FilterValidationError(error_msg)

        if not (self._is_predicate(condition) or self._is_logical_oper(condition)):
            error_msg = [
                f"Wrong format in {condition}. ",
                f"Valid predicate operators {Predicate.OPERATORS}. ",
                f"Valid logical operators {Predicate.LOGICAL_OPERATORS}. ",
                f"Example: {FilterExamples.LOGICAL_PREDICATE}",
            ]
            logger.error("".join(error_msg))
            raise FilterValidationError("".join(error_msg))

    def _is_predicate(self, condition: dict) -> bool:
        is_predicate = False
        if len(condition) == 1:
            inner_dict = next(iter(condition.values()))
            if isinstance(inner_dict, dict) and len(inner_dict) == 1:
                inner_key = next(iter(inner_dict.keys()))
                is_predicate = inner_key in Predicate.OPERATORS
        return is_predicate

    def _is_logical_oper(self, condition: dict) -> bool:
        return any(oper in condition for oper in Predicate.LOGICAL_OPERATORS)

    def _get_operator(self, conditions: dict):
        if len(conditions.keys()) != 1:
            raise FilterValidationError(
                f"Only one operator per filter object is allowed. See Example {FilterExamples.LOGICAL_PREDICATE}",
            )

        for operator in Predicate.LOGICAL_OPERATORS:
            if operator in conditions:
                return operator

    def _validate_comparison_operator(self, operator: str) -> str:
        valid_operator = Predicate.OPERATORS.get(operator)
        if not valid_operator:
            possible_operators = list(Predicate.OPERATORS.keys())
            raise FilterValidationError(f"Invalid comparison operator, '{operator}' not in {possible_operators}")
        return valid_operator

    def _validate_column_value(self, comp_value: str, val_type: str) -> Any:
        try:
            match val_type:
                case "integer":
                    validated_value = int(comp_value)
                case "number":
                    validated_value = float(comp_value)
                case "boolean":
                    validated_value = bool(comp_value)
                case "string":
                    validated_value = str(comp_value)
                case _:
                    raise FilterValidationError(f"Filter not supported on {val_type}")
            return validated_value
        except ValueError as exc:
            raise FilterValidationError(exc)


class ColumnsAggregationValidator(object):

    def __init__(self, prop_processor: PropertyInfoProcessor):
        self._prop_processor = prop_processor

    def validate(self, columns_aggregation_list: list) -> ColumnsAggregation:
        """Validates columsn aggregation filter.

        :param columns_aggregation_list: list with column aggregation
            params
        :type columns_aggregation_list: list
        :raises FilterValidationError: when the format does not meet
            criteria
        :return: a valid columns aggregation tuple
        :rtype: ColumnsAggregation
        """
        if not isinstance(columns_aggregation_list, list) or len(columns_aggregation_list) != Aggregation.N_ELEMENTS:
            raise FilterValidationError(
                f"{FilterErrorMessage.COLUMNS_AGGREGATION}. Must be an array with {Aggregation.N_ELEMENTS}",
            )

        prop_info = self._prop_processor.get_prop_info(columns_aggregation_list[FilterIndex.COLUMN_OR_PROP_NAME])
        valid_func = self._validate_aggregation_func(columns_aggregation_list[FilterIndex.OPERATOR])

        return ColumnsAggregation(column=prop_info.name, function=valid_func)

    def _validate_aggregation_func(self, agg_func: str) -> str:
        if agg_func not in Aggregation.FUNCTIONS:
            raise FilterValidationError(f"Invalid aggregation operator not in: {Aggregation.FUNCTIONS}")
        return agg_func


class ColumnsFilterValidator(object):

    def __init__(self, prop_processor: PropertyInfoProcessor):
        self._prop_processor = prop_processor

    def validate(self, columns_filter_list) -> ColumnsFilter:
        """Validate the columns filter list.

        :param columns_filter_list: _description_
        :type columns_filter_list: _type_
        :raises FilterValidationError: when fortma is not array/list
        :raises FilterValidationError: when trying to project
            subproperties
        :return: a valid columns filter tuple
        :rtype: ColumnsFilter
        """
        if not isinstance(columns_filter_list, list):
            raise FilterValidationError(
                f"{FilterErrorMessage.COLUMNS_AGGREGATION}. Must be an array of column names",
            )

        valid_columns = []
        for column in columns_filter_list:
            column_name = self._prop_processor.get_prop_info(column).name
            if Separator.DOT in column_name:
                raise FilterValidationError(f"Subproperties are not supported for columns_filter: {column_name}")
            valid_columns.append(column_name.replace(Separator.ARRAY, ""))

        return ColumnsFilter(columns=valid_columns)
