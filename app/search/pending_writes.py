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

import json
from typing import Dict, List, Optional, Tuple

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from loguru import logger
from redis.asyncio.client import Redis

from app.api.routes.utils.records import get_info_from_blob_urn, get_info_from_urn
from app.api.routes.utils.search import get_valid_ids_from_ddms_datasets
from app.core.config import get_app_settings

PENDING_WRITES_TTL = 120  # seconds; comfortably longer than OSDU indexer lag
_KEY_PREFIX = "rafs:pending_writes"


def _pending_key(data_partition_id: str) -> str:
    return f"{_KEY_PREFIX}:{data_partition_id}"


def _parse_pending_urn(ddms_urn: str) -> Tuple[Optional[str], Optional[str]]:
    """Derive (dataset_id, wpc_id) from a DDMSDataset URN in one parse.

    Reuses the URN parsing already used on the read path
    (`app/api/routes/utils/records.py`) instead of inventing a new format-specific
    parser. Supports both the non-blob ddms_urn format (dataset_id segment) and the
    blob_urn format (blob_id, which already encodes wpc_id/analysis_family/analysis_type).
    """
    if get_app_settings().use_blob_storage:
        urn_info = get_info_from_blob_urn(ddms_urn)
        dataset_key, wpc_key = "blob_id", "wpc_id"
    else:
        urn_info = get_info_from_urn(ddms_urn)
        dataset_key, wpc_key = "dataset_id", "samples_analysis_id"
    if not urn_info:
        return None, None
    return urn_info.get(dataset_key), urn_info.get(wpc_key)


def _scope_matches(entry_scope: Dict[str, str], requested_scope: Dict[str, str]) -> bool:
    """A pending entry matches a requested scope if, for every scope key present in
    the request, the entry's stored value for that key is present and equal.

    A pending entry need not carry all four scope keys — e.g. a record may legitimately
    lack a basin_id while still correctly matching a wellbore_id-scoped search. An
    unscoped request (empty dict) always matches, preserving today's default behavior.
    """
    for scope_key, requested_value in requested_scope.items():
        if entry_scope.get(scope_key) != requested_value:
            return False
    return True


def _get_redis() -> Optional[Redis]:
    """Return the Redis client from the FastAPI cache backend, or None."""
    settings = get_app_settings()
    if not settings.cache_enable:
        return None
    try:  # noqa: WPS229
        backend = FastAPICache.get_backend()
        if isinstance(backend, RedisBackend):
            return backend.redis
    except Exception as exc:  # noqa: B902, WPS329
        logger.debug("_get_redis: cache backend unavailable: {0}", exc)
    return None


async def record_pending_write(  # noqa: ASYNC910
    data_partition_id: str,
    ddms_urn: str,
    scope: Optional[Dict[str, str]] = None,
) -> None:
    """Store a recently-written DDMSDataset URN so searches can find it before
    the OSDU indexer has re-indexed the record.

    Stored as a Hash field keyed by the URN's own dataset_id (rather than a flat
    Set of bare URN strings) so that two distinct datasets — or a stale vs. fresh
    URN from a rapid re-upload of the same wpc_id — cannot silently shadow one
    another in a Set's unordered iteration; an overwrite by the same dataset_id key
    is itself a legitimate "this dataset was re-uploaded" case, not an ambiguous one.

    `scope` carries the record's own Well/Wellbore/Field/Basin identifiers (the same
    shape as `SearchScope.to_query_dict()`) so reads can filter pending entries by
    the scope of the search that is asking for them. Silently no-ops when Redis is
    unavailable or caching is disabled.
    """
    redis = _get_redis()
    if redis is None:
        return  # noqa: ASYNC910
    dataset_id, wpc_id = _parse_pending_urn(ddms_urn)
    if not dataset_id or not wpc_id:
        logger.debug("record_pending_write: could not parse URN, skipping: {0}", ddms_urn)
        return  # noqa: ASYNC910
    try:
        key = _pending_key(data_partition_id)
        payload = json.dumps({"ddms_urn": ddms_urn, "wpc_id": wpc_id, "scope": scope or {}})
        await redis.hset(key, dataset_id, payload)
        await redis.expire(key, PENDING_WRITES_TTL)
    except Exception as exc:  # noqa: B902, WPS329
        logger.debug("record_pending_write: Redis error, skipping: {0}", exc)


async def get_pending_ids(  # noqa: WPS211
    data_partition_id: str,
    analysis_family: str,
    analysis_type: str,
    target_schema_version: str,
    scope: Optional[Dict[str, str]] = None,
) -> List[Tuple[str, str]]:
    """Return (dataset_id, wpc_id) tuples from recently-written URNs that
    match the given analysis type, schema version, and scope.

    `scope` is matched against each stored entry's own scope: an entry matches if,
    for every key present in `scope`, the entry's stored value for that key is equal.
    An entry missing a requested key is excluded — a scope-less stored entry only
    matches an unscoped (`scope=None`/`{}`) request. Passing no scope returns every
    pending entry that matches the analysis type/version, same as before this change.

    Returns an empty list when Redis is unavailable or caching is disabled.
    """
    redis = _get_redis()
    pending_ids: List[Tuple[str, str]] = []
    if redis is None:
        return pending_ids  # noqa: ASYNC910
    requested_scope = scope or {}
    try:
        key = _pending_key(data_partition_id)
        raw_entries = await redis.hgetall(key)
        urns = _filter_scoped_urns(raw_entries, requested_scope)
        if urns:
            pending_ids = get_valid_ids_from_ddms_datasets(
                ddms_datasets=urns,
                analysis_family=analysis_family,
                analysis_type=analysis_type,
                target_schema_version=target_schema_version,
            )
    except Exception as exc:  # noqa: B902, WPS329
        logger.debug("get_pending_ids: Redis error, skipping: {0}", exc)
    return pending_ids  # noqa: ASYNC910


def _filter_scoped_urns(raw_entries: Dict, requested_scope: Dict[str, str]) -> List[str]:
    """Decode raw Hash entries and return the URNs of those matching the requested scope."""
    urns: List[str] = []
    for raw_payload in raw_entries.values():
        payload = raw_payload.decode() if isinstance(raw_payload, bytes) else raw_payload
        try:
            entry = json.loads(payload)
        except (TypeError, ValueError) as exc:
            logger.debug("get_pending_ids: could not decode pending entry, skipping: {0}", exc)
            continue
        if _scope_matches(entry.get("scope") or {}, requested_scope):
            urns.append(entry["ddms_urn"])
    return urns


async def supplement_with_pending_writes(  # noqa: WPS211
    result_ids: List[Tuple[str, str]],
    data_partition_id: str,
    analysis_family: str,
    analysis_type: str,
    target_schema_version: str,
    scope: Optional[Dict[str, str]] = None,
) -> List[Tuple[str, str]]:
    """Merge pending-write entries into OSDU Search results.

    Records written recently may not yet appear in the OSDU Search index
    due to indexer lag. This supplements the search results with any
    matching URNs stored in the write-through Redis cache, deduplicating
    by wpc_id so already-indexed records are not repeated.

    `scope` must be the same scope already resolved for the caller's Search query
    (e.g. `SearchScope.to_query_dict()`) so a pending write cannot leak into a search
    scoped to a different Well/Wellbore/Field/Basin.
    """
    pending = await get_pending_ids(
        data_partition_id=data_partition_id,
        analysis_family=analysis_family,
        analysis_type=analysis_type,
        target_schema_version=target_schema_version,
        scope=scope,
    )
    if not pending:
        return result_ids

    known_wpc_ids = {wpc_id for _, wpc_id in result_ids}
    merged = list(result_ids)
    for dataset_id, wpc_id in pending:
        if wpc_id not in known_wpc_ids:
            merged.append((dataset_id, wpc_id))
            known_wpc_ids.add(wpc_id)

    logger.debug(
        "supplement_with_pending_writes: added {0} pending entries for {1}/{2}.",
        len(merged) - len(result_ids),
        analysis_family,
        analysis_type,
    )
    return merged
