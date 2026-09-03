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

from typing import Optional, Union

import pandas as pd
from pydantic import BaseModel

from app.api.routes.data.api import _cast_str_columns, _unwrap_optional
from app.bulk_data_validation.data_validation import DataValidator


class TestUnwrapOptional:
    def test_plain_type_returned_unchanged(self):
        """Verify non-Optional annotation is returned as-is."""
        assert _unwrap_optional(str) is str
        assert _unwrap_optional(int) is int
        assert _unwrap_optional(float) is float

    def test_typing_optional_unwrapped(self):
        """Verify Optional[T] (typing.Union[T, None]) returns inner type."""
        assert _unwrap_optional(Optional[str]) is str
        assert _unwrap_optional(Optional[int]) is int

    def test_typing_union_with_none_unwrapped(self):
        """Verify Union[T, None] returns inner type."""
        assert _unwrap_optional(Union[str, None]) is str

    def test_py311_pipe_union_type_unwrapped(self):
        """Verify Python 3.10+ `T | None` syntax (types.UnionType) is handled.

        `str | None` produces types.UnionType, not typing.Union — the isinstance()
        branch in _unwrap_optional must catch this or str fields written with the
        pipe-union syntax would not receive the dtype=str hint in _read_dataframe.
        """
        assert _unwrap_optional(str | None) is str
        assert _unwrap_optional(int | None) is int

    def test_genuine_multi_member_union_preserved(self):
        """Verify a real union (no NoneType member) is returned unchanged, not collapsed to its first member.

        A prior implementation collapsed any Union to non_none[0], so Union[str, int]
        silently became `str` and Union[float, str] became `float`. That let
        _str_field_names()/_cast_float_columns() mutate genuine union fields as if
        they were single-typed, altering submitted values before validation/storage.
        """
        assert _unwrap_optional(Union[str, int]) == Union[str, int]
        assert _unwrap_optional(Union[float, str]) == Union[float, str]

    def test_optional_multi_member_union_preserved(self):
        """Verify Optional[Union[A, B]] (i.e. Union[A, B, None]) is not collapsed to a single member.

        Only Union[T, None] with exactly one non-None member should unwrap to T.
        """
        assert _unwrap_optional(Optional[Union[str, int]]) == Union[str, int, None]


class TestCastStrColumns:
    class _Model(BaseModel):
        StrField: str
        OptionalStrField: Optional[str] = None
        UnionField: Union[str, int]
        IntField: int

    def test_numeric_str_column_is_cast_and_reports_change(self):
        """Verify a numeric column for a str-typed field is coerced and signalled as changed."""
        df = pd.DataFrame({"StrField": [1, 2], "IntField": [1, 2]})
        changed = _cast_str_columns(df, self._Model)
        assert changed is True
        assert df["StrField"].tolist() == ["1", "2"]

    def test_already_str_column_is_untouched_and_reports_no_change(self):
        """Verify a column already str-typed is left alone and reported as unchanged."""
        df = pd.DataFrame({"StrField": ["1", "2"]})
        changed = _cast_str_columns(df, self._Model)
        assert changed is False
        assert df["StrField"].tolist() == ["1", "2"]

    def test_genuine_union_column_is_not_coerced(self):
        """Verify a genuine Union[str, int] field is left untouched, unlike a plain str field."""
        df = pd.DataFrame({"UnionField": [1, 2]})
        changed = _cast_str_columns(df, self._Model)
        assert changed is False
        assert df["UnionField"].tolist() == [1, 2]


class TestDataValidatorUnwrapAnnotation:
    """Same contract verified for DataValidator._unwrap_annotation."""

    def test_plain_type_returned_unchanged(self):
        """Verify non-Optional annotation is returned as-is."""
        assert DataValidator._unwrap_annotation(str) is str

    def test_typing_optional_unwrapped(self):
        """Verify Optional[T] returns inner type."""
        assert DataValidator._unwrap_annotation(Optional[str]) is str

    def test_py311_pipe_union_type_unwrapped(self):
        """Verify Python 3.10+ `T | None` syntax is handled."""
        assert DataValidator._unwrap_annotation(str | None) is str
