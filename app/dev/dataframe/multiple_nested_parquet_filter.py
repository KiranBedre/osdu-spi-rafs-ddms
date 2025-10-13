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

import re
from typing import Any, List, Optional, Tuple

import pandas as pd
import pyarrow as pa
from loguru import logger
from pyarrow import parquet as pq

from app.dataframe.query import OPERATOR_TYPES
from app.dev.dataframe.nested_query import PandasDFQueryNested
from app.dev.resources.multiple_nested_filters import (
    ColumnsAggregation,
    ColumnsFilter,
    DFMultipleNestedFilterValidator,
    LogicalOperators,
    Predicate,
    RowsFilter,
    RowsFilterValidator,
    RowsMultipleFilter,
    Separator,
)
from app.exceptions.exceptions import UnprocessableContentException


def apply_filters_from_bytes(
    parquet_bytes: bytes,
    df_filter: DFMultipleNestedFilterValidator,
) -> pd.DataFrame:
    """Apply filters to parquet data and return a filtered pandas.DataFrame.

    :param bytes parquet_bytes: parquet as read from blob storage
    :param DFMultipleNestedFilterValidator df_filter: df filter
        validator
    :return pd.DataFrame: the pd.DataFrame result from applying filters
    """
    return apply_filters_from_df(pq.read_table(pa.BufferReader(parquet_bytes)).to_pandas(), df_filter)


def apply_filters_from_df(
    df: pd.DataFrame,
    df_filter: DFMultipleNestedFilterValidator,
) -> pd.DataFrame:
    """Apply filters to dataframe.

    :param df: dataframe
    :type df: pd.DataFrame
    :param df_filter: dataframe filter
    :type df_filter: DFMultipleNestedFilterValidator
    :raises UnprocessableContentException: if there are issue with
        filter
    :return: filtered dataframe
    :rtype: pd.DataFrame
    """
    query_df = PandasDFQueryNested(df)
    rows_filter_processor = RowsFilterProcessor()
    rows_multiple_filter_processor = RowsMultipleFilterProcessor(rows_filter_processor)
    columns_filter_processor = ColumnsFilterProcessor()
    columns_aggregation_processor = ColumnsAggregationProcessor()
    try:
        if df_filter.valid_rows_multiple_filter:
            query_df = rows_multiple_filter_processor.apply_rows_multiple_filter(
                query_df, df_filter.valid_rows_multiple_filter,
            )
        elif df_filter.valid_rows_filter:
            query_df = rows_filter_processor.apply_rows_filter(query_df, df_filter.valid_rows_filter)
        if df_filter.valid_columns_filter and not query_df.df.empty:
            query_df = columns_filter_processor.apply_columns_filter(query_df, df_filter.valid_columns_filter)
        if df_filter.valid_columns_aggregation and not query_df.df.empty:
            query_df = columns_aggregation_processor.apply_columns_aggregation_filter(
                query_df, df_filter.valid_columns_aggregation,
            )
    except Exception as exc:  # noqa: B902
        exc_type = type(exc)
        error_msg = f"Processing filter exception ({exc_type}): {exc}"
        logger.error(error_msg)
        raise UnprocessableContentException(detail=error_msg)

    return query_df.df


class RowsFilterProcessor(object):

    def apply_rows_filter(  # noqa:CCR001
        self,
        query_df: PandasDFQueryNested,
        rows_filter: RowsFilter,
    ) -> PandasDFQueryNested:
        """Applies the rows filter given a specific set of cases.

        :param query_df: the query dataframe
        :type query_df: PandasDFQueryNested
        :param rows_filter: a valid rows filter tuple
        :type rows_filter: RowsFilter
        :raises NotImplementedError: If a filter is from a not supported
            case
        :return: the query result over the filtering
        :rtype: PandasDFQueryNested
        """
        prop_names = rows_filter.column.split(Separator.DOT)

        array_indices = []
        for prop_name in prop_names:
            array_indices.append(Separator.ARRAY in prop_name)

        case_not_array = not (any(array_indices))
        case_array_column = array_indices.count(True) == 1 and array_indices.index(True) == 0
        case_array_property = array_indices.count(True) == 1 and array_indices.index(True) > 0
        case_nested_array = array_indices.count(True) == 2 and array_indices.index(True) == 0

        if case_not_array:
            query_df = self._select_not_array(query_df, rows_filter)
        elif case_array_column:
            query_df = self._select_in_array_column(query_df, rows_filter)
        elif case_array_property:
            query_df = self._select_in_array_property(query_df, rows_filter)
        elif case_nested_array:
            query_df = self._select_in_array_column(query_df, rows_filter, case_nested_array=True)
        else:
            raise NotImplementedError(f"Filter over this nested level array is not supported: {prop_names}")

        return query_df

    def _get_array_path_and_props_path(self, prop_names: List[str]) -> Tuple[List[str], List[str]]:
        """Retrieves the array property path and the remaining properties path.
        Assumes only one array in prop_names.

        :param prop_names: list of property names
        :type prop_names: List[str]
        :return: array_path, props_path
        :rtype: Tuple[List[str], List[str]
        """
        array_path = []
        ix = 0
        for prop_name in prop_names:
            ix += 1
            array_path.append(prop_name.replace(Separator.ARRAY, ""))
            if Separator.ARRAY in prop_name:
                break

        props_path = [field.replace(Separator.ARRAY, "") for field in prop_names[ix:]]

        return array_path, props_path

    def _select_not_array(self, query_df: PandasDFQueryNested, rows_filter: RowsFilter) -> PandasDFQueryNested:
        """Peforms the rows filter selection when there are not array
        properties.

        :param query_df: the query dataframe
        :type query_df: PandasDFQueryNested
        :param rows_filter: the rows filter
        :type rows_filter: RowsFilter
        :return: the query result over the filtering
        :rtype: PandasDFQueryNested
        """
        prop_names = rows_filter.column.split(Separator.DOT)
        props_path = prop_names[1:] if len(prop_names) > 1 else None

        return query_df.select(
            prop_names[0],
            rows_filter.operator,
            rows_filter.comp_value,
            props_path,
        )

    def _select_in_array_column(
        self,
        query_df: PandasDFQueryNested,
        rows_filter: RowsFilter,
        case_nested_array: bool = False,
    ) -> PandasDFQueryNested:
        """Performs the row filter selection when the column is an array.

        :param query_df: the query dataframe
        :type query_df: PandasDFQueryNested
        :param rows_filter: the rows filter
        :type rows_filter: RowsFilter
        :param case_nested_array: flags a nested array, defaults to
            False
        :type case_nested_array: bool, optional
        :return: the query result over the filtering
        :rtype: PandasDFQueryNested
        """
        prop_names = rows_filter.column.split(Separator.DOT)
        array_path, props_path = self._get_array_path_and_props_path(prop_names=prop_names)
        array_column_name = array_path[0]

        original_df = query_df.df
        query_df = PandasDFQueryNested(query_df.df.explode(array_column_name))

        if case_nested_array:
            nested_array_rows_filter = RowsFilter(
                column=re.sub(re.escape(Separator.ARRAY), "", rows_filter.column, count=1),
                operator=rows_filter.operator,
                comp_value=rows_filter.comp_value,
            )
            query_df = self._select_in_array_property(query_df, nested_array_rows_filter)
        else:
            query_df = query_df.select(
                array_column_name,
                rows_filter.operator,
                rows_filter.comp_value,
                props_path,
            )

        columns_agg = {}
        for col_name in original_df.columns:
            if col_name == array_column_name:
                columns_agg[col_name] = list
            else:
                columns_agg[col_name] = "first"

        grouped = query_df.df.groupby(query_df.df.index).agg(columns_agg)
        return PandasDFQueryNested(grouped)

    def _select_in_array_property(self, query_df: PandasDFQueryNested, rows_filter: RowsFilter) -> PandasDFQueryNested:
        """Performs the row filter selection when the array is a property of
        the value object.

        :param query_df: the query dataframe
        :type query_df: PandasDFQueryNested
        :param rows_filter: the rows filter
        :type rows_filter: RowsFilter
        :return: the query result over the filtering
        :rtype: PandasDFQueryNested
        """
        prop_names = rows_filter.column.split(Separator.DOT)
        array_path, props_path = self._get_array_path_and_props_path(prop_names)

        def filter_array_values(obj_value: dict, prop_path: List[str], key_path: List[str], oper: str, comp_value: Any):
            for prop in prop_path:
                obj_value = obj_value.get(prop)

            filtered_array = [
                array_item for array_item in obj_value if apply_oper(array_item, key_path, oper, comp_value)
            ]
            return bool(filtered_array)

        def apply_oper(array_item: Optional[dict], key_path: List[str], oper: str, comp_value: Any):
            for prop in key_path:
                if array_item:
                    array_item = array_item.get(prop, {})

            oper = OPERATOR_TYPES.get(oper)
            return bool(array_item) and oper(array_item, comp_value)

        # Apply the filter to the column
        column_name = array_path[0]
        array_prop_path = array_path[1:]
        df = query_df.df
        cond = df[column_name].apply(
            filter_array_values,
            prop_path=array_prop_path,
            key_path=props_path,
            oper=rows_filter.operator,
            comp_value=rows_filter.comp_value,
        )

        return PandasDFQueryNested(df[cond])


class ColumnsFilterProcessor(object):

    def apply_columns_filter(
        self,
        query_df: PandasDFQueryNested,
        columns_filter: Optional[ColumnsFilter],
    ) -> PandasDFQueryNested:
        """Applies the columns filter over the query dataframe.

        :param query_df: the query dataframe
        :type query_df: PandasDFQueryNested
        :param columns_filter: a valid columns tuple
        :type columns_filter: ColumnsFilter, optional
        :return: the query result over the filtering
        :rtype: PandasDFQueryNested
        """
        columns = columns_filter.columns if columns_filter else None
        return query_df.project(columns)


def normalize_df_column(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """Apply a json normalization operation and updates column names over a
    dataframe column.

    :param df: The dataframe
    :type df: pd.DataFrame
    :param column_name: the column name
    :type column_name: str
    :return: the normalized dataframe from given column
    :rtype: pd.DataFrame
    """
    normalized_df = pd.json_normalize(df[column_name])
    normalized_df.columns = [f"{column_name}.{col_name}" for col_name in normalized_df.columns]
    return normalized_df


class ColumnsAggregationProcessor(object):

    def apply_columns_aggregation_filter(
        self,
        query_df: PandasDFQueryNested,
        columns_aggregation: ColumnsAggregation,
    ) -> PandasDFQueryNested:
        """Applies a function to aggregate over a column or property.

        :param query_df: the query dataframe
        :type query_df: PandasDFQueryNested
        :param columns_aggregation: valid columns aggregation tuple
        :type columns_aggregation: ColumnsAggregation
        :return: the query result over the filtering
        :rtype: PandasDFQueryNested
        """
        query_df = self._expand_query_df_for_aggregation(query_df, columns_aggregation)

        return query_df.aggregate(
            columns_aggregation.column.replace(Separator.ARRAY, ""),
            columns_aggregation.function,
        )

    def _expand_query_df_for_aggregation(
        self,
        query_df: PandasDFQueryNested,
        columns_aggregation: ColumnsAggregation,
    ) -> PandasDFQueryNested:
        """Performs an iterative explosion operation over array properties to
        prepare for aggregation.

        :param query_df: the query dataframe
        :type query_df: PandasDFQueryNested
        :param columns_aggregation: valid columns aggregation tuple
        :type columns_aggregation: ColumnsAggregation
        :return: the query result over the filtering
        :rtype: PandasDFQueryNested
        """
        full_column_name = columns_aggregation.column
        if Separator.DOT in full_column_name:
            props = full_column_name.split(Separator.DOT)
            for ix, prop in enumerate(props):
                prop_name = Separator.DOT.join(props[:ix + 1]).replace(Separator.ARRAY, "").strip(Separator.DOT)
                if Separator.ARRAY in prop:
                    query_df = PandasDFQueryNested(normalize_df_column(query_df.df.explode(prop_name), prop_name))
                elif ix == 0:
                    query_df = PandasDFQueryNested(normalize_df_column(query_df.df, prop_name))
        return query_df


class RowsMultipleFilterProcessor(object):

    SOLVED_FILTER: str = "solved_filter"

    def __init__(self, rows_filter_processor: RowsFilterProcessor = None):
        self._rows_filter_processor = rows_filter_processor or RowsFilterProcessor()

    def apply_rows_multiple_filter(  # noqa: CCR001
        self,
        query_df: PandasDFQueryNested,
        rows_multiple_filter: RowsMultipleFilter,
    ) -> PandasDFQueryNested:
        stack = [rows_multiple_filter.conditions]
        while stack:
            current_condition = stack.pop()
            if self._is_logical_oper(current_condition):
                current_op = self._get_operator(current_condition)
                conditions_list = current_condition[current_op]
                if self._is_all_predicate_or_solved(conditions_list):
                    current_condition[self.SOLVED_FILTER] = self._apply_oper(query_df, current_op, conditions_list)
                    del current_condition[current_op]
                else:
                    stack.append(current_condition)
                    for nested_condition in conditions_list:
                        if self._is_logical_oper(nested_condition):  # noqa: WPS220
                            stack.append(nested_condition)  # noqa: WPS220
            else:
                current_condition[self.SOLVED_FILTER] = self._apply_oper(
                    query_df, LogicalOperators.AND, [current_condition],
                )
        return rows_multiple_filter.conditions[self.SOLVED_FILTER]

    def _apply_conjunction(  # noqa: CCR001
        self,
        query_df: PandasDFQueryNested,
        predicates: List[dict],
    ) -> PandasDFQueryNested:
        dfs = self._get_dfs_from_predicates(query_df, predicates)

        if dfs and all((not check_df.empty for check_df in dfs)):
            if len(dfs) > 1:
                common_indexes = dfs[0].index
                for df in dfs[1:]:
                    common_indexes = common_indexes.intersection(df.index)
                common_indexes = common_indexes.tolist()
                merged_df = dfs[0].loc[common_indexes]
            else:
                merged_df = dfs[0]
        else:
            merged_df = pd.DataFrame()

        return PandasDFQueryNested(merged_df)

    def _apply_disjunction(self, query_df: PandasDFQueryNested, predicates: List[dict]) -> PandasDFQueryNested:
        concatenated_df = pd.concat(self._get_dfs_from_predicates(query_df, predicates))
        unique_df = concatenated_df[~concatenated_df.index.duplicated()]
        return PandasDFQueryNested(unique_df)

    def _is_all_predicate_or_solved(self, predicates: List[dict]) -> bool:
        predicate_or_solved = []
        for predicate in predicates:
            if RowsFilterValidator.VALID_FILTER in predicate or self.SOLVED_FILTER in predicate:
                predicate_or_solved.append(True)
            else:
                predicate_or_solved.append(False)
        return all(predicate_or_solved)

    def _apply_oper(self, query_df, operator, predicates):
        if LogicalOperators.AND == operator:
            query_df = self._apply_conjunction(query_df, predicates)
        elif LogicalOperators.OR == operator:
            query_df = self._apply_disjunction(query_df, predicates)
        return query_df

    def _get_dfs_from_predicates(self, query_df, predicates) -> List[pd.DataFrame]:
        dfs = []
        for predicate in predicates:
            if RowsFilterValidator.VALID_FILTER in predicate:
                dfs.append(
                    self._rows_filter_processor.apply_rows_filter(
                        query_df, predicate.get(RowsFilterValidator.VALID_FILTER),
                    ).df,
                )
            elif self.SOLVED_FILTER in predicate:
                dfs.append(predicate.get(self.SOLVED_FILTER).df)
        return dfs

    def _is_logical_oper(self, condition: dict) -> bool:
        return any(oper in condition for oper in Predicate.LOGICAL_OPERATORS)

    def _get_operator(self, conditions: dict):
        for operator in Predicate.LOGICAL_OPERATORS:
            if operator in conditions:
                return operator
