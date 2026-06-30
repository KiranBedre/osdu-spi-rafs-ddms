#  Copyright 2025 ExxonMobil Technology and Engineering Company
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

"""Regression tests for pagination limits on /search and /search/data endpoints.

Issue-680 introduced a bug where both _build_dynamic_endpoint branches used
get_search_data_pagination_parameters (max 100) instead of
get_search_pagination_parameters (max 1000) for the /search branch.
"""

import inspect
from unittest.mock import MagicMock

import pytest
from fastapi import Depends

from app.api.dependencies.validation import (
    get_search_data_pagination_parameters,
    get_search_pagination_parameters,
)
from app.api.routes.common.dynamic_search import DynamicGenericSearchView


def _get_pagination_dep(endpoint_fn):
    """Return the dependency callable wired to pagination_parameters."""
    sig = inspect.signature(endpoint_fn)
    param = sig.parameters.get("pagination_parameters")
    assert param is not None, "endpoint has no pagination_parameters parameter"
    default = param.default
    assert isinstance(default, type(Depends())), "pagination_parameters default is not a Depends"
    return default.dependency


@pytest.fixture
def view():
    router = MagicMock()
    fetcher = MagicMock()
    filter_dep = MagicMock()
    instance = DynamicGenericSearchView(
        router=router,
        ddms_dataset_ids_fetcher_class=fetcher,
        endpoints_config=[],
    )
    instance._filter_dep = filter_dep
    return instance, filter_dep


class TestDynamicSearchPaginationDependency:

    def test_get_search_uses_1000_limit_dep(self, view):
        instance, filter_dep = view
        endpoint = instance._build_dynamic_endpoint("get_search", lambda r: "rca", filter_dep)
        dep = _get_pagination_dep(endpoint)
        assert dep is get_search_pagination_parameters

    def test_get_search_data_uses_100_limit_dep(self, view):
        instance, filter_dep = view
        endpoint = instance._build_dynamic_endpoint("get_search_data", lambda r: "rca", filter_dep)
        dep = _get_pagination_dep(endpoint)
        assert dep is get_search_data_pagination_parameters

    def test_get_search_dep_is_not_data_dep(self, view):
        instance, filter_dep = view
        endpoint = instance._build_dynamic_endpoint("get_search", lambda r: "rca", filter_dep)
        dep = _get_pagination_dep(endpoint)
        assert dep is not get_search_data_pagination_parameters

    def test_get_search_data_dep_is_not_search_dep(self, view):
        instance, filter_dep = view
        endpoint = instance._build_dynamic_endpoint("get_search_data", lambda r: "rca", filter_dep)
        dep = _get_pagination_dep(endpoint)
        assert dep is not get_search_pagination_parameters


def _get_page_limit_query(fn):
    """Return the Query object for page_limit in a FastAPI dependency function."""
    return inspect.signature(fn).parameters["page_limit"].default


class TestPaginationParamLimits:

    def test_search_pagination_max_is_1000(self):
        assert _get_page_limit_query(get_search_pagination_parameters).le == 1000

    def test_search_pagination_default_is_1000(self):
        assert _get_page_limit_query(get_search_pagination_parameters).default == 1000

    def test_search_data_pagination_max_is_100(self):
        assert _get_page_limit_query(get_search_data_pagination_parameters).le == 100

    def test_search_data_pagination_default_is_100(self):
        assert _get_page_limit_query(get_search_data_pagination_parameters).default == 100

    def test_search_pagination_allows_more_than_100(self):
        assert _get_page_limit_query(get_search_pagination_parameters).le > 100
