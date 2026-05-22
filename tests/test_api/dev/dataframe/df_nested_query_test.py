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
import pytest

from app.dev.dataframe.nested_query import PandasDFQueryNested
from tests.test_api.dev.dataframe.sample_dataframe_data import SAMPLE_DATA


@pytest.fixture
def sample_dataframe():
    return pd.DataFrame(SAMPLE_DATA)


class TestPandasDFQueryNested:

    @pytest.mark.parametrize(
        "column,operator,comp_val,field",
        [
            ("IntColumn", "<", 35, None),
            ("IntColumn", "<=", 30, None),
            ("FloatColumn", "<", 2.1, None),
            ("FloatColumn", "<=", 2.0, None),
            ("ObjectColumn", "<", 2.1, "number"),
            ("ObjectColumn", "<=", 2.0, "number"),
        ],
    )
    def test_select_lt_lte(self, column, operator, comp_val, field, sample_dataframe):
        query_df = PandasDFQueryNested(sample_dataframe)
        prop_path = [field] if field else None
        selected = query_df.select(column, operator, comp_val, prop_path)
        expected_df = sample_dataframe.iloc[[0, 1]]
        assert selected.df.equals(expected_df)

    @pytest.mark.parametrize(
        "column,operator,comp_val,field",
        [
            ("IntColumn", ">", 30, None),
            ("IntColumn", ">=", 35, None),
            ("FloatColumn", ">", 2.0, None),
            ("FloatColumn", ">=", 3.0, None),
            ("ObjectColumn", ">", 2.0, "number"),
            ("ObjectColumn", ">=", 3.0, "number"),
        ],
    )
    def test_select_gt_gte(self, column, operator, comp_val, field, sample_dataframe):
        query_df = PandasDFQueryNested(sample_dataframe)
        prop_path = [field] if field else None
        selected = query_df.select(column, operator, comp_val, prop_path)
        expected_df = sample_dataframe.iloc[[2, 3]]
        assert selected.df.equals(expected_df)

    @pytest.mark.parametrize(
        "column,operator,comp_val,field",
        [
            ("TextColumn", "=", "Row3", None),
            ("IntColumn", "=", 35, None),
            ("FloatColumn", "=", 3.0, None),
            ("ObjectColumn", "=", 3.0, "number"),
            ("ObjectColumn", "=", "Text3", "text"),
        ],
    )
    def test_select_eq(self, column, operator, comp_val, field, sample_dataframe):
        query_df = PandasDFQueryNested(sample_dataframe)
        prop_path = [field] if field else None
        selected = query_df.select(column, operator, comp_val, prop_path)
        expected_df = sample_dataframe.iloc[[2]]
        assert selected.df.equals(expected_df)

    @pytest.mark.parametrize(
        "column,operator,comp_val,field",
        [
            ("TextColumn", "!=", "Row4", None),
            ("IntColumn", "!=", 40, None),
            ("FloatColumn", "!=", 4.0, None),
            ("ObjectColumn", "!=", 4.0, "number"),
            ("ObjectColumn", "!=", "Text4", "text"),
        ],
    )
    def test_select_neq(self, column, operator, comp_val, field, sample_dataframe):
        query_df = PandasDFQueryNested(sample_dataframe)
        prop_path = [field] if field else None
        selected = query_df.select(column, operator, comp_val, prop_path)
        expected_df = sample_dataframe.iloc[[0, 1, 2]]
        assert selected.df.equals(expected_df)
