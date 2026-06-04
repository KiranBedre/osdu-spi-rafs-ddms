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

from typing import Any, List, Optional

from app.dataframe.query import OPERATOR_TYPES, PandasDFQueryBase


class PandasDFQueryNested(PandasDFQueryBase):
    """Class to perform simple queries on a Pandas DataFrame."""

    def select(
        self,
        column: str,
        op_type: str,
        comp_val: Any,
        prop_path: Optional[List[str]] = None,
    ) -> "PandasDFQueryNested":
        """Select (filter) rows given a condition.

        :param column: the column name
        :type column: str
        :param op_type: the operator type
        :type op_type: str
        :param comp_val: the comparison value
        :type comp_val: Any
        :param prop_path: an optional prop_path of the column, defaults
            to None
        :type prop_path: Optional[List[str]], optional
        :return: an updated PandasDFQueryNested object
        :rtype: PandasDFQueryNested
        """
        oper = OPERATOR_TYPES.get(op_type)
        df_query = self
        df_col = self.df[column]

        def get_field(row: dict, prop_path: List[str]) -> Any:
            field = row
            for path in prop_path:
                field = field.get(path)
            return field

        if oper:
            cond = (
                df_col.apply(
                    lambda row: oper(get_field(row, prop_path), comp_val),
                )
                if prop_path
                else oper(df_col, comp_val)
            )
            df_query = PandasDFQueryNested(self.df[cond])

        return df_query
