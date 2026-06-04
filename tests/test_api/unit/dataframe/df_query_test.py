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

from app.dataframe.query import PandasDFQueryBase


@pytest.fixture
def sample_dataframe():
    # Create a sample DataFrame for testing
    data = {
        "TextColumn": ["Row1", "Row2", "Row3", "Row4"],
        "IntColumn": [25, 30, 35, 40],
        "FloatColumn": [1.0, 2.0, 3.0, 4.0],
        "ObjectColumn": [
            {"number": 1.0, "text": "InnerText1"},
            {"number": 2.0, "text": "InnerText2"},
            {"number": 3.0, "text": "InnerText3"},
            {"number": 4.0, "text": "InnerText4"},
        ],
        "ArrayColumn": [[0], [0, 1], [0, 1, 2], [0, 1, 2, 3]],
    }
    return pd.DataFrame(data)


class TestPandasDFQueryBase:
    def test_project(self, sample_dataframe):
        query_df = PandasDFQueryBase(sample_dataframe)
        projected = query_df.project(["TextColumn", "FloatColumn"])
        expected_columns = ["TextColumn", "FloatColumn"]
        assert list(projected.df.columns) == expected_columns

    def test_project_all(self, sample_dataframe):
        query_df = PandasDFQueryBase(sample_dataframe)
        projected = query_df.project()
        assert list(projected.df.columns) == list(sample_dataframe.columns)

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
        query_df = PandasDFQueryBase(sample_dataframe)
        selected = query_df.select(column, operator, comp_val, field)
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
        query_df = PandasDFQueryBase(sample_dataframe)
        selected = query_df.select(column, operator, comp_val, field)
        expected_df = sample_dataframe.iloc[[2, 3]]
        assert selected.df.equals(expected_df)

    @pytest.mark.parametrize(
        "column,operator,comp_val,field",
        [
            ("TextColumn", "=", "Row3", None),
            ("IntColumn", "=", 35, None),
            ("FloatColumn", "=", 3.0, None),
            ("ObjectColumn", "=", 3.0, "number"),
            ("ObjectColumn", "=", "InnerText3", "text"),
        ],
    )
    def test_select_eq(self, column, operator, comp_val, field, sample_dataframe):
        query_df = PandasDFQueryBase(sample_dataframe)
        selected = query_df.select(column, operator, comp_val, field)
        expected_df = sample_dataframe.iloc[[2]]
        assert selected.df.equals(expected_df)

    @pytest.mark.parametrize(
        "column,operator,comp_val,field",
        [
            ("TextColumn", "!=", "Row4", None),
            ("IntColumn", "!=", 40, None),
            ("FloatColumn", "!=", 4.0, None),
            ("ObjectColumn", "!=", 4.0, "number"),
            ("ObjectColumn", "!=", "InnerText4", "text"),
        ],
    )
    def test_select_neq(self, column, operator, comp_val, field, sample_dataframe):
        query_df = PandasDFQueryBase(sample_dataframe)
        selected = query_df.select(column, operator, comp_val, field)
        expected_df = sample_dataframe.iloc[[0, 1, 2]]
        assert selected.df.equals(expected_df)

    @pytest.mark.parametrize(
        "column,aggregator_funcs,field, results",
        [
            ("IntColumn", ["mean", "max", "min", "sum"], None, [32.5, 40, 25, 130]),
            ("FloatColumn", ["mean", "max", "min", "sum"], None, [2.5, 4.0, 1.0, 10.0]),
            ("TextColumn", ["count"], None, [4]),
            ("ObjectColumn", ["mean", "max", "min", "sum"], "number", [2.5, 4.0, 1.0, 10.0]),
            ("ObjectColumn", ["count"], "text", [4]),
        ],
    )
    def test_aggregate(self, column, aggregator_funcs, field, results, sample_dataframe):
        query = PandasDFQueryBase(sample_dataframe)
        for index, aggregate_func in enumerate(aggregator_funcs):
            aggregated = query.aggregate(column, aggregate_func, field)
            assert aggregated.df.columns == [column]
            assert aggregated.df.iloc[0][column] == results[index]
