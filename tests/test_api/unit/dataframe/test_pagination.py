#  Copyright 2026 ExxonMobil Technology and Engineering Company
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

"""Unit tests for app.dataframe.pagination.slice_dataframe (Issue-819/820)."""

import pandas as pd
import pytest

from app.dataframe.pagination import reject_aggregation_with_pagination, slice_dataframe
from app.exceptions import exceptions


def _make_df(n_rows: int) -> pd.DataFrame:
    return pd.DataFrame({"id": list(range(n_rows)), "value": [f"v{i}" for i in range(n_rows)]})


class TestSliceDataframe:
    def test_slice_dataframe_no_limit(self):
        """No row_limit returns all rows from row_offset, and the correct total."""
        df = _make_df(20)
        sliced, total = slice_dataframe(df, row_offset=5, row_limit=None)

        assert total == 20
        assert len(sliced) == 15
        assert sliced["id"].tolist() == list(range(5, 20))

    def test_slice_dataframe_with_limit(self):
        """100-row df, limit=10 -> 10 rows, total=100."""
        df = _make_df(100)
        sliced, total = slice_dataframe(df, row_offset=0, row_limit=10)

        assert total == 100
        assert len(sliced) == 10
        assert sliced["id"].tolist() == list(range(10))

    def test_slice_dataframe_with_offset(self):
        """100-row df, offset=50, limit=10 -> rows 50-59, total=100."""
        df = _make_df(100)
        sliced, total = slice_dataframe(df, row_offset=50, row_limit=10)

        assert total == 100
        assert sliced["id"].tolist() == list(range(50, 60))

    def test_slice_dataframe_offset_exceeds_total(self):
        """offset=10 on a 5-row df -> empty result, total still reflects the source."""
        df = _make_df(5)
        sliced, total = slice_dataframe(df, row_offset=10, row_limit=None)

        assert total == 5
        assert sliced.empty

    def test_slice_dataframe_exact_limit(self):
        """Boundary at the last row: limit exactly reaches the end of the df."""
        df = _make_df(10)
        sliced, total = slice_dataframe(df, row_offset=5, row_limit=5)

        assert total == 10
        assert sliced["id"].tolist() == [5, 6, 7, 8, 9]

    def test_slice_dataframe_resets_index(self):
        """Sliced result always has a fresh RangeIndex, regardless of row_offset."""
        df = _make_df(10)
        sliced, _total = slice_dataframe(df, row_offset=5, row_limit=3)

        assert sliced.index.tolist() == [0, 1, 2]

    def test_slice_dataframe_zero_offset_zero_limit_identity(self):
        """row_offset=0, row_limit=None is the backward-compatible identity case."""
        df = _make_df(10)
        sliced, total = slice_dataframe(df, row_offset=0, row_limit=None)

        assert total == 10
        assert sliced["id"].tolist() == df["id"].tolist()

    def test_slice_dataframe_empty_input(self):
        """Slicing an empty dataframe returns an empty result and total=0."""
        df = pd.DataFrame({"id": [], "value": []})
        sliced, total = slice_dataframe(df, row_offset=0, row_limit=10)

        assert total == 0
        assert sliced.empty

    @pytest.mark.parametrize(
        ("row_limit", "expected_ids"),
        [(1, [8]), (100, [8, 9]), (10000, [8, 9])],
    )
    def test_slice_dataframe_limit_larger_than_remaining(self, row_limit, expected_ids):
        """row_limit beyond the remaining rows just returns what's left, no error."""
        df = _make_df(10)
        sliced, total = slice_dataframe(df, row_offset=8, row_limit=row_limit)

        assert total == 10
        assert sliced["id"].tolist() == expected_ids


@pytest.mark.parametrize(
    ("pagination_active", "aggregation_active"),
    [(False, False), (True, False), (False, True)],
)
def test_reject_aggregation_with_pagination_allows_non_conflicting(pagination_active, aggregation_active):
    reject_aggregation_with_pagination(pagination_active, aggregation_active)


def test_reject_aggregation_with_pagination_raises_422():
    with pytest.raises(exceptions.UnprocessableContentException) as exc_info:
        reject_aggregation_with_pagination(True, True)

    assert "columns_aggregation" in exc_info.value.detail
