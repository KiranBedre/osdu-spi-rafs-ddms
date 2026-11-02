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

"""Issue-850: Search Data V2 cache key must discriminate on the Accept header.

The unit suite replaces the cache decorator with a pass-through (tests/conftest.py),
so the endpoint built by DynamicGenericSearchView is the same function the real
decorator receives. Building its key proves JSON and Parquet requests for the same
URL no longer share a cache entry; the deployed-cache behaviour is covered by the
integration suite.
"""

from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import Request

from app.api.routes.common.dynamic_search import DynamicGenericSearchView
from app.core.helpers.cache.key_builder import key_builder_using_token

SEARCH_DATA_PATH = "/api/rafs-ddms/v2/samplesanalysis/rca/search/data"


def _search_request(accept=None, query="content_schema_version=1.0.0"):
    headers = [
        (b"authorization", b"Bearer token"),
        (b"data-partition-id", b"opendes"),
    ]
    if accept is not None:
        headers.append((b"accept", accept.encode()))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "http",
            "server": ("testserver", 80),
            "root_path": "",
            "path": SEARCH_DATA_PATH,
            "raw_path": SEARCH_DATA_PATH.encode(),
            "query_string": query.encode(),
            "headers": headers,
        },
    )


@pytest.fixture
def search_data_endpoint():
    view = DynamicGenericSearchView(
        router=MagicMock(),
        ddms_dataset_ids_fetcher_class=MagicMock(),
        endpoints_config=[],
    )
    return view._build_dynamic_endpoint("get_search_data", lambda req: "rca", MagicMock())


def _build_key(endpoint, accept):
    with patch("fastapi_cache.FastAPICache.get_prefix", return_value="rafs"):
        return key_builder_using_token(
            endpoint,
            "",
            request=_search_request(accept=accept),
            response=None,
            args=(),
            kwargs={},
        )


def test_search_data_cache_key_distinguishes_json_and_parquet(search_data_endpoint):
    json_key = _build_key(search_data_endpoint, "application/json")
    parquet_key = _build_key(search_data_endpoint, "application/x-parquet")

    assert json_key != parquet_key


def test_search_data_cache_key_is_stable_for_identical_accept(search_data_endpoint):
    assert _build_key(search_data_endpoint, "application/json") == _build_key(
        search_data_endpoint,
        "application/json",
    )
