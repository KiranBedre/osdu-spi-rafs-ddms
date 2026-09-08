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

from app.api.routes.data.api import _unwrap_optional
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
