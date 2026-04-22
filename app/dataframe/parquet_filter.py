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

import pandas as pd
import pyarrow as pa
from loguru import logger
from pyarrow import parquet as pq

from app.dataframe.query import PandasDFQueryBase
from app.exceptions.exceptions import UnprocessableContentException
from app.resources.filters import DataFrameFilterValidator


def apply_filters_from_bytes(
    parquet_bytes: bytes,
    df_filter: DataFrameFilterValidator,
) -> pd.DataFrame:
    """Apply filters to parquet data and return a filtered pandas.DataFrame.

    :param bytes parquet_bytes: parquet as read from blob storage
    :param DataFrameFilterValidator df_filter: df filter validator
    :return pd.DataFrame: the pd.DataFrame result from applying filters
    """
    return apply_filters_from_df(pq.read_table(pa.BufferReader(parquet_bytes)).to_pandas(), df_filter)


def apply_filters_from_df(
    df: pd.DataFrame,
    df_filter: DataFrameFilterValidator,
) -> pd.DataFrame:
    """Apply filters to dataframe.

    :param df: dataframe
    :type df: pd.DataFrame
    :param df_filter: dataframe filter
    :type df_filter: DataFrameFilterValidator
    :raises UnprocessableContentException: if there are issue with
        filter
    :return: filtered dataframe
    :rtype: pd.DataFrame
    """
    query_df = PandasDFQueryBase(df)
    try:
        if df_filter.valid_rows_filter:
            query_df = query_df.select(
                df_filter.valid_rows_filter.column,
                df_filter.valid_rows_filter.operator,
                df_filter.valid_rows_filter.comp_value,
                field=df_filter.valid_rows_filter.field,
            )
        if df_filter.valid_columns_filter:
            query_df = query_df.project(df_filter.valid_columns_filter.columns)
        if df_filter.valid_columns_aggregation:
            query_df = query_df.aggregate(
                df_filter.valid_columns_aggregation.column,
                df_filter.valid_columns_aggregation.function,
                field=df_filter.valid_columns_aggregation.field,
            )
    except Exception as exc:  # noqa: B902
        exc_type = type(exc)
        error_msg = f"Processing filter exception ({exc_type}): {exc}"
        logger.debug(error_msg)
        raise UnprocessableContentException(detail=error_msg)

    return query_df.df
