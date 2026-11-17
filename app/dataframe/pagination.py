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

"""Row-level pagination helper shared by get_data_v2 (#819) and search/data (#820).

Deliberately Pandas-only (`iloc`) — no DuckDB. See the Issue-819/820 plan's
"Lead Feedback Resolution" for why DuckDB was dropped from this iteration:
everything is already materialized into a DataFrame by the time pagination
runs, so DuckDB would add indirection without predicate pushdown or memory
savings.
"""

from typing import Optional, Tuple

import pandas as pd

from app.exceptions import exceptions

AGGREGATION_PAGINATION_CONFLICT = "row_limit/row_offset cannot be combined with columns_aggregation."


def slice_dataframe(
    df: pd.DataFrame,
    row_offset: int,
    row_limit: Optional[int],
) -> Tuple[pd.DataFrame, int]:
    """Slice a DataFrame to a row window using plain Pandas `iloc`.

    :param df: the source dataframe (already filtered/concatenated by the caller)
    :type df: pd.DataFrame
    :param row_offset: number of rows to skip before the returned window
    :type row_offset: int
    :param row_limit: maximum number of rows to return, or None for "all
        remaining rows from row_offset"
    :type row_limit: Optional[int]
    :return: a tuple of (sliced dataframe with a fresh RangeIndex, total row
        count of `df` before slicing)
    :rtype: Tuple[pd.DataFrame, int]
    """
    total = len(df)
    if row_limit is None:
        return df.iloc[row_offset:].reset_index(drop=True), total
    return df.iloc[row_offset : row_offset + row_limit].reset_index(drop=True), total


def reject_aggregation_with_pagination(pagination_active: bool, aggregation_active: bool) -> None:
    """Raise 422 when row pagination is combined with `columns_aggregation`.

    Aggregation collapses to a single row indexed by the aggregation function
    name (e.g. "count"); `slice_dataframe`'s `reset_index(drop=True)` would
    silently clobber that label, or drop the row entirely for any
    `row_offset > 0`. Shared by the Dataset Service and Blob Storage paths so
    both backends expose the same semantics.

    :param pagination_active: True when row_limit is set or row_offset > 0
    :type pagination_active: bool
    :param aggregation_active: True when the request carries a valid columns_aggregation
    :type aggregation_active: bool
    :raises UnprocessableContentException: when both are requested
    """
    if pagination_active and aggregation_active:
        raise exceptions.UnprocessableContentException(detail=AGGREGATION_PAGINATION_CONFLICT)
