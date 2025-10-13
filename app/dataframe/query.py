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

import operator
from types import MappingProxyType
from typing import Any, List, Optional

import pandas as pd

OPERATOR_TYPES = MappingProxyType({
    "=": operator.eq,
    "!=": operator.ne,
    "<=": operator.le,
    ">=": operator.ge,
    "<": operator.lt,
    ">": operator.gt,
})


class PandasDFQueryBase(object):
    """Class to perform simple queries on a Pandas DataFrame."""

    def __init__(self, df: pd.DataFrame) -> None:
        """Init.

        :param pd.DataFrame df: the DataFrame to query
        """
        self._df = df

    @property
    def df(self) -> pd.DataFrame:
        """DataFrame.

        :return pd.DataFrame: the DataFrame to query
        """
        return self._df

    def project(self, columns: Optional[List[str]] = None) -> "PandasDFQueryBase":
        """Project given columns over DataFrame.

        :param columns: list of columns to project, defaults to None
        :type columns: Optional[List[str]], optional
        :return: an updated PandasDFQueryBase object
        :rtype: PandasDFQueryBase
        """
        df_query = self
        if columns:
            df_query = PandasDFQueryBase(self.df[columns])
        return df_query

    def select(self, column: str, op_type: str, comp_val: Any, field: Optional[str] = None) -> "PandasDFQueryBase":
        """Select (filter) rows given a condition.

        :param column: the column name
        :type column: str
        :param op_type: the operator type
        :type op_type: str
        :param comp_val: the comparison value
        :type comp_val: Any
        :param field: an optional field of the column, defaults to None
        :type field: Optional[str], optional
        :return: an updated PandasDFQueryBase object
        :rtype: PandasDFQueryBase
        """
        oper = OPERATOR_TYPES.get(op_type)
        df_query = self
        df_col = self.df[column]

        if oper:
            cond = df_col.apply(lambda row: oper(row[field], comp_val)) if field else oper(df_col, comp_val)
            df_query = PandasDFQueryBase(self.df[cond])

        return df_query

    def aggregate(self, column: str, agg_func: str, field: Optional[str] = None) -> "PandasDFQueryBase":
        """Aggregate DataFrame column based on an operator function.

        :param column: the column name
        :type column: str
        :param agg_func: the operator function name
        :type agg_func: str
        :param field: an optional field of the column, defaults to None
        :type field: Optional[str], optional
        :return: an updated PandasDFQueryBase object
        :rtype: PandasDFQueryBase
        """
        df_col = self.df[column]

        if field:
            agg = df_col.apply(lambda row: row[field]).agg([agg_func])
        else:
            agg = df_col.agg([agg_func])

        if isinstance(agg, pd.Series):
            agg = agg.to_frame()

        return PandasDFQueryBase(agg)
