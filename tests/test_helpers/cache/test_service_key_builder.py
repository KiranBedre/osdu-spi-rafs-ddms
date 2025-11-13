#  Copyright 2023 ExxonMobil Technology and Engineering Company

"""Tests for service method cache key builder."""

import hashlib
from unittest.mock import MagicMock, patch

from app.core.helpers.cache.key_builder import key_builder_for_service_methods


class ServiceMethodMock(MagicMock):
    __module__ = "app.services.schema"
    __name__ = "get_schema"


def test_key_builder_for_service_methods_with_string_arg():
    """Test that key builder generates consistent keys for string arguments."""
    func = ServiceMethodMock()
    schema_id = "osdu:wks:master-data--SampleAcquisition:1.0.0"
    prefix = "test-prefix"

    with patch("fastapi_cache.FastAPICache.get_prefix", return_value=prefix):
        # First call with schema_id
        key1 = key_builder_for_service_methods(
            func=func,
            namespace="",
            request=None,  # Service methods don't have request
            response=None,
            args=(None, schema_id),  # (self, schema_id)
            kwargs={}
        )

        # Second call with same schema_id
        key2 = key_builder_for_service_methods(
            func=func,
            namespace="",
            request=None,
            response=None,
            args=(None, schema_id),  # Same args!
            kwargs={}
        )

    # Keys should match for same input
    assert key1 == key2, f"Keys should match for same arguments. Got key1={key1}, key2={key2}"

    # Verify key structure
    func_meta = f"{func.__module__}:{func.__name__}"
    cache_meta = schema_id
    expected_hash = hashlib.sha256(f"{func_meta}:{cache_meta}".encode()).hexdigest()
    expected_key = f"{prefix}::{expected_hash}"

    assert key1 == expected_key, f"Key should match expected format. Got {key1}, expected {expected_key}"


def test_key_builder_for_service_methods_with_list_arg():
    """Test that key builder generates consistent keys for list arguments."""
    class DatasetServiceMock(MagicMock):
        __module__ = "app.services.dataset"
        __name__ = "get_signed_urls"

    func = DatasetServiceMock()
    dataset_ids = ["dataset-1", "dataset-2"]
    prefix = "test-prefix"

    with patch("fastapi_cache.FastAPICache.get_prefix", return_value=prefix):
        # First call
        key1 = key_builder_for_service_methods(
            func=func,
            namespace="",
            request=None,
            response=None,
            args=(None, dataset_ids),  # (self, dataset_ids)
            kwargs={}
        )

        # Second call with same list (same order)
        key2 = key_builder_for_service_methods(
            func=func,
            namespace="",
            request=None,
            response=None,
            args=(None, dataset_ids),
            kwargs={}
        )

        # Third call with same list but different order
        key3 = key_builder_for_service_methods(
            func=func,
            namespace="",
            request=None,
            response=None,
            args=(None, ["dataset-2", "dataset-1"]),  # Reversed order
            kwargs={}
        )

    # Keys with same list should match
    assert key1 == key2, "Keys should match for same list arguments"

    # Keys with different order should match (list is sorted internally)
    assert key1 == key3, "Keys should match for list arguments regardless of order (sorted internally)"


def test_key_builder_for_service_methods_different_args():
    """Test that different arguments produce different cache keys."""
    func = ServiceMethodMock()
    prefix = "test-prefix"

    with patch("fastapi_cache.FastAPICache.get_prefix", return_value=prefix):
        key1 = key_builder_for_service_methods(
            func=func,
            args=(None, "schema-id-1"),
            kwargs={}
        )

        key2 = key_builder_for_service_methods(
            func=func,
            args=(None, "schema-id-2"),  # Different schema_id
            kwargs={}
        )

    # Different arguments should produce different keys
    assert key1 != key2, "Different arguments should produce different cache keys"


def test_key_builder_for_service_methods_with_kwargs():
    """Test that kwargs are included in cache key."""
    func = ServiceMethodMock()
    prefix = "test-prefix"

    with patch("fastapi_cache.FastAPICache.get_prefix", return_value=prefix):
        # Call with kwargs
        key1 = key_builder_for_service_methods(
            func=func,
            args=(None,),
            kwargs={"schema_id": "test-schema", "version": "1.0"}
        )

        # Same kwargs, same order
        key2 = key_builder_for_service_methods(
            func=func,
            args=(None,),
            kwargs={"schema_id": "test-schema", "version": "1.0"}
        )

        # Same kwargs, different order (should still match - sorted internally)
        key3 = key_builder_for_service_methods(
            func=func,
            args=(None,),
            kwargs={"version": "1.0", "schema_id": "test-schema"}
        )

    assert key1 == key2, "Same kwargs should produce same key"
    assert key1 == key3, "Same kwargs in different order should produce same key (sorted internally)"
