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

import pandas as pd
import pytest

from app.dev.dataframe.multiple_nested_parquet_filter import (
    ColumnsAggregationProcessor,
    ColumnsFilterProcessor,
    RowsFilterProcessor,
    RowsMultipleFilterProcessor,
    apply_filters_from_df,
)
from app.dev.dataframe.nested_query import PandasDFQueryNested
from app.dev.resources.multiple_nested_filters import (
    DFMultipleNestedFilterValidator,
)
from tests.test_api.dev.dataframe.sample_dataframe_data import (
    SAMPLE_DATA,
    generate_json_schema,
)


@pytest.fixture
def sample_dataframe():
    return pd.DataFrame(SAMPLE_DATA)


@pytest.fixture
def sample_schema(sample_dataframe):
    record_data = json.loads(sample_dataframe.to_json(orient="records"))[0]
    return generate_json_schema(record_data)


def test_columns_filter(sample_dataframe, sample_schema):
    df_filter = DFMultipleNestedFilterValidator(
        sample_schema,
        raw_columns_filter='["TextColumn", "FloatColumn"]',
    )

    query_df = PandasDFQueryNested(sample_dataframe)
    columns_filter_processor = ColumnsFilterProcessor()
    result_df = columns_filter_processor.apply_columns_filter(
        query_df,
        df_filter.valid_columns_filter,
    ).df

    expected_columns = ["TextColumn", "FloatColumn"]
    assert list(result_df.columns) == expected_columns


def test_columns_filter_all(sample_dataframe, sample_schema):
    df_filter = DFMultipleNestedFilterValidator(sample_schema)

    query_df = PandasDFQueryNested(sample_dataframe)
    columns_filter_processor = ColumnsFilterProcessor()
    result_df = columns_filter_processor.apply_columns_filter(
        query_df,
        df_filter.valid_columns_filter,
    ).df

    assert list(result_df.columns) == list(sample_dataframe.columns)


@pytest.mark.parametrize(
    "raw_rows_filter",
    [
        ('{"TextColumn": {"$lt": "Row3"}}'),
        ('{"IntColumn": {"$lte": 30}}'),
        ('{"FloatColumn": {"$lt": 2.1}}'),
        ('{"ObjectColumn.number": {"$lte": 2.0}}'),
        ('{"ObjectColumn.inner_object.inner_text": {"$lt": "InnerText3"}}'),
    ],
)
def test_rows_filter_no_array(sample_dataframe, sample_schema, raw_rows_filter):
    df_filter = DFMultipleNestedFilterValidator(
        schema=sample_schema,
        raw_rows_filter=raw_rows_filter,
    )

    query_df = PandasDFQueryNested(sample_dataframe)
    rows_filter_processor = RowsFilterProcessor()
    result_df = rows_filter_processor.apply_rows_filter(
        query_df,
        df_filter.valid_rows_filter,
    ).df

    expected_df = sample_dataframe.iloc[[0, 1]]
    assert result_df.equals(expected_df)


@pytest.mark.parametrize(
    "raw_rows_filter",
    [
        ('{"ObjectColumnNestedArray.ArrayProperty.number": {"$lte": 8.0}}'),
        ('{"ArrayColumn.number": {"$lt": 9.0}}'),
        ('{"ArrayColumnNestedArray.ArrayProperty.number": {"$lte": 8.0}}'),
    ],
)
def test_rows_filter_array(sample_dataframe, sample_schema, raw_rows_filter):
    df_filter = DFMultipleNestedFilterValidator(
        schema=sample_schema,
        raw_rows_filter=raw_rows_filter,
    )

    query_df = PandasDFQueryNested(sample_dataframe)
    rows_filter_processor = RowsFilterProcessor()
    result_df = rows_filter_processor.apply_rows_filter(
        query_df,
        df_filter.valid_rows_filter,
    ).df

    expected_df = sample_dataframe.iloc[[0, 1]]
    assert result_df.equals(expected_df)


@pytest.mark.parametrize(
    "raw_columns_aggregation,result",
    [
        (
            '["ObjectColumnNestedArray.ArrayProperty.number", "mean"]',
            8.5,
        ),
        (
            '["ArrayColumn.number", "min"]',
            1.0,
        ),
        (
            '["ArrayColumnNestedArray.ArrayProperty.number", "max"]',
            16.0,
        ),
        (
            '["ObjectColumn.inner_object.inner_text", "count"]',
            4,
        ),
    ],
)
def test_colums_aggregation(sample_dataframe, sample_schema, raw_columns_aggregation, result):
    df_filter = DFMultipleNestedFilterValidator(
        schema=sample_schema,
        raw_columns_aggregation=raw_columns_aggregation,
    )

    columns_aggregation_processor = ColumnsAggregationProcessor()

    query_df = PandasDFQueryNested(sample_dataframe)
    aggregated_df = columns_aggregation_processor.apply_columns_aggregation_filter(
        query_df,
        df_filter.valid_columns_aggregation,
    ).df

    column_name = df_filter.valid_columns_aggregation.column.replace("[]", "")
    assert aggregated_df.columns == [column_name]
    assert aggregated_df.iloc[0][column_name] == result


@pytest.mark.parametrize(
    "raw_rows_filter,raw_columns_aggregation,result",
    [
        (
            '{"FloatColumn": {"$lte": 2.0}}',
            '["ObjectColumnNestedArray.ArrayProperty.number", "mean"]',
            4.5,
        ),
        (
            '{"ObjectColumnNestedArray.ArrayProperty.number": {"$gt": 8.0}}',
            '["ArrayColumn.number", "min"]',
            9.0,
        ),
        (
            '{"ArrayColumn.number": {"$gte": 9.0}}',
            '["ArrayColumnNestedArray.ArrayProperty.number", "max"]',
            16.0,
        ),
        (
            '{"ArrayColumnNestedArray.ArrayProperty.number": {"$gt": 8.0}}',
            '["ObjectColumn.inner_object.inner_text", "count"]',
            2,
        ),
    ],
)
def test_colums_aggregation_after_row_filter(
    sample_dataframe,
    sample_schema,
    raw_rows_filter,
    raw_columns_aggregation,
    result,
):
    df_filter = DFMultipleNestedFilterValidator(
        schema=sample_schema,
        raw_rows_filter=raw_rows_filter,
        raw_columns_aggregation=raw_columns_aggregation,
    )

    aggregated_df = apply_filters_from_df(sample_dataframe, df_filter)

    column_name = df_filter.valid_columns_aggregation.column.replace("[]", "")
    assert aggregated_df.columns == [column_name]
    assert aggregated_df.iloc[0][column_name] == result


@pytest.mark.parametrize(
    "raw_rows_multiple_filter,expected_df",
    [
        (
            """
            {
                "$and": [
                    {
                        "FloatColumn": {"$gt": 2.0}
                    },
                    {
                        "FloatColumn": {"$lt": 4.0}
                    }
                ]
            }
            """,
            pd.DataFrame(SAMPLE_DATA).iloc[[2]],
        ),
        (
            """
            {
                "$or": [
                    {
                        "FloatColumn": {"$eq": 2.0}
                    },
                    {
                        "FloatColumn": {"$eq": 4.0}
                    }
                ]
            }
            """,
            pd.DataFrame(SAMPLE_DATA).iloc[[1, 3]],
        ),
        (
            """
            {
                "$or": [
                    {
                        "IntColumn": {"$eq": 25}
                    },
                    {
                        "$and": [
                            {
                                "FloatColumn": {"$gt": 2.0}
                            },
                            {
                                "FloatColumn": {"$lt": 4.0}
                            }
                        ]
                    }
                ]
            }
            """,
            pd.DataFrame(SAMPLE_DATA).iloc[[0, 2]],
        ),
        (
            """
            {
                "$and": [
                    {
                        "IntColumn": {"$gt": 25}
                    },
                    {
                        "$or": [
                            {
                                "FloatColumn": {"$eq": 2.0}
                            },
                            {
                                "FloatColumn": {"$eq": 4.0}
                            }
                        ]
                    }
                ]
            }
            """,
            pd.DataFrame(SAMPLE_DATA).iloc[[1, 3]],
        ),
        (
            """
            {
                "$and": [
                    {
                        "IntColumn": {"$gt": 25}
                    },
                    {
                        "$or": [
                            {
                                "ObjectColumnNestedArray.ArrayProperty.number": {"$gte": 15.0}
                            },
                            {
                                "$and": [
                                    {
                                        "ArrayColumnNestedArray.ArrayProperty.number": {"$gt": 8.0}
                                    },
                                    {
                                        "TextColumn": {"$eq": "Row3"}
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
            """,
            pd.DataFrame(SAMPLE_DATA).iloc[[2, 3]],
        ),
    ],
)
def test_rows_multiple_filter(sample_dataframe, sample_schema, raw_rows_multiple_filter, expected_df):
    df_filter = DFMultipleNestedFilterValidator(
        schema=sample_schema,
        raw_rows_multiple_filter=raw_rows_multiple_filter,
    )

    query_df = PandasDFQueryNested(sample_dataframe)
    rows_multiple_filter_processor = RowsMultipleFilterProcessor()
    result_df = rows_multiple_filter_processor.apply_rows_multiple_filter(
        query_df,
        df_filter.valid_rows_multiple_filter,
    ).df

    assert result_df.equals(expected_df)
