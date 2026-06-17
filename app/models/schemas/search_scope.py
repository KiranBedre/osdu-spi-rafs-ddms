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

from typing import Dict, Optional


class SearchScope:
    """Optional search scoping keys shared across analysis types."""

    __slots__ = ("basin_id", "field_id", "well_id", "wellbore_id")

    def __init__(
        self,
        basin_id: Optional[str] = None,
        field_id: Optional[str] = None,
        well_id: Optional[str] = None,
        wellbore_id: Optional[str] = None,
    ) -> None:
        self.basin_id = basin_id
        self.field_id = field_id
        self.well_id = well_id
        self.wellbore_id = wellbore_id

    def to_query_dict(self) -> Dict[str, str]:
        """Return the non-empty scope values as a plain dict."""
        scope_items = {
            "basin_id": self.basin_id,
            "field_id": self.field_id,
            "well_id": self.well_id,
            "wellbore_id": self.wellbore_id,
        }
        return {key: value for key, value in scope_items.items() if value}
