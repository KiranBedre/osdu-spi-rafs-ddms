#  Copyright 2023 ExxonMobil Technology and Engineering Company
#
import hashlib
from unittest.mock import MagicMock, patch

from app.core.helpers.cache.key_builder import key_builder_using_token


class FuncMock(MagicMock):
    __module__ = "module"
    __name__ = "name"


def test_key_builder_using_token():
    query_params_items = [("key", "value")]
    data_partition_id = "test-data-partition-id"
    token = "test-token"
    url = "https://test_url"
    content_type = "application/test-content-type"
    accept = "application/json"
    prefix = "prefix"

    function = FuncMock()
    request = MagicMock()
    query_params = MagicMock()
    query_params.multi_items.return_value = query_params_items
    request.query_params = query_params
    request.headers = {
        "authorization": token,
        "data-partition-id": data_partition_id,
        "content-type": content_type,
        "accept": accept,
    }
    request.url = url

    func_meta = f"{function.__module__}:{function.__name__}"
    query_meta = f"{data_partition_id}:{token}:{url}:{query_params_items}:{content_type}:{accept}"
    hash_key = hashlib.sha256(
        f"{func_meta}:{query_meta}".encode(),
    ).hexdigest()
    test_key = f"{prefix}::{hash_key}"

    with patch(
        "fastapi_cache.FastAPICache.get_prefix",
        return_value=prefix,
    ):
        expected_key = key_builder_using_token(
            func=function,
            request=request,
        )

    assert test_key == expected_key


def _build_key_with_accept(accept, include_accept_header=True):
    function = FuncMock()
    request = MagicMock()
    query_params = MagicMock()
    query_params.multi_items.return_value = [("key", "value")]
    request.query_params = query_params
    headers = {
        "authorization": "test-token",
        "data-partition-id": "test-data-partition-id",
        "content-type": "application/test-content-type",
    }
    if include_accept_header:
        headers["accept"] = accept
    request.headers = headers
    request.url = "https://test_url"

    with patch("fastapi_cache.FastAPICache.get_prefix", return_value="prefix"):
        return key_builder_using_token(func=function, request=request)


def test_key_builder_using_token_differs_by_accept_media_type():
    json_key = _build_key_with_accept("application/json")
    parquet_key = _build_key_with_accept("application/x-parquet")

    assert json_key != parquet_key


def test_key_builder_using_token_is_stable_for_identical_accept():
    assert _build_key_with_accept("application/json") == _build_key_with_accept("application/json")


def test_key_builder_using_token_differs_by_accept_version_parameter():
    first_key = _build_key_with_accept("*/*;version=1.0.0")
    second_key = _build_key_with_accept("*/*;version=2.0.0")

    assert first_key != second_key


def test_key_builder_using_token_differs_by_accept_order():
    assert _build_key_with_accept("application/json, application/x-parquet") != _build_key_with_accept(
        "application/x-parquet, application/json",
    )


def test_key_builder_using_token_differs_by_accept_q_value():
    assert _build_key_with_accept("application/json;q=0.9") != _build_key_with_accept("application/json;q=0.1")


def test_key_builder_using_token_normalizes_accept_case_and_whitespace():
    assert _build_key_with_accept("Application/JSON , application/x-parquet ; q=0.5") == _build_key_with_accept(
        "application/json,application/x-parquet;q=0.5",
    )


def test_key_builder_using_token_absent_accept_equals_empty_accept():
    absent_key = _build_key_with_accept(None, include_accept_header=False)

    assert absent_key == _build_key_with_accept("")
    assert absent_key == _build_key_with_accept("   ")
    assert absent_key != _build_key_with_accept("application/json")
