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

import pytest
from fastapi import HTTPException

from app.api.dependencies.validation import get_search_scope


class TestGetSearchScope:
    def test_valid_scope_values_return_search_scope(self):
        result = get_search_scope(
            basin_id="opendes:master-data--Basin:b-1:",
            field_id="opendes:master-data--Field:f-1:",
            well_id="opendes:master-data--Well:w-1:",
            wellbore_id="opendes:master-data--Wellbore:wb-1:",
        )

        assert result.basin_id == "opendes:master-data--Basin:b-1:"
        assert result.field_id == "opendes:master-data--Field:f-1:"
        assert result.well_id == "opendes:master-data--Well:w-1:"
        assert result.wellbore_id == "opendes:master-data--Wellbore:wb-1:"

    @pytest.mark.parametrize(
        "param_name,param_value",
        [
            ("basin_id", "invalid"),
            ("field_id", "invalid"),
            ("well_id", "invalid"),
            ("wellbore_id", "invalid"),
        ],
    )
    def test_invalid_scope_value_raises_400(self, param_name, param_value):
        kwargs = {
            "basin_id": None,
            "field_id": None,
            "well_id": None,
            "wellbore_id": None,
        }
        kwargs[param_name] = param_value

        with pytest.raises(HTTPException) as exc_info:
            get_search_scope(**kwargs)

        assert exc_info.value.status_code == 400
        assert f"Invalid '{param_name}' format" in exc_info.value.detail

    @pytest.mark.parametrize(
        "param_name,param_value",
        [
            ("basin_id", "opendes:master-data--Well:w-1:"),
            ("field_id", "opendes:master-data--Basin:b-1:"),
            ("well_id", "opendes:master-data--Field:f-1:"),
            ("wellbore_id", "opendes:master-data--Well:w-1:"),
        ],
    )
    def test_wrong_scope_kind_raises_400(self, param_name, param_value):
        kwargs = {
            "basin_id": None,
            "field_id": None,
            "well_id": None,
            "wellbore_id": None,
        }
        kwargs[param_name] = param_value

        with pytest.raises(HTTPException) as exc_info:
            get_search_scope(**kwargs)

        assert exc_info.value.status_code == 400
        assert f"Invalid '{param_name}' format" in exc_info.value.detail
