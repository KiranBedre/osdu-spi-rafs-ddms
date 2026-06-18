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

from typing import List, Optional, Tuple

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from loguru import logger
from redis.asyncio.client import Redis

from app.api.routes.utils.search import get_valid_ids_from_ddms_datasets
from app.core.config import get_app_settings

PENDING_WRITES_TTL = 120  # seconds; comfortably longer than OSDU indexer lag
_KEY_PREFIX = "rafs:pending_writes"


def _pending_key(data_partition_id: str) -> str:
    return f"{_KEY_PREFIX}:{data_partition_id}"


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
) -> None:
    """Store a recently-written DDMSDataset URN so searches can find it before
    the OSDU indexer has re-indexed the record.

    Silently no-ops when Redis is unavailable or caching is disabled.
    """
    redis = _get_redis()
    if redis is None:
        return
    try:
        key = _pending_key(data_partition_id)
        await redis.sadd(key, ddms_urn)
        await redis.expire(key, PENDING_WRITES_TTL)
    except Exception as exc:  # noqa: B902, WPS329
        logger.debug("record_pending_write: Redis error, skipping: {0}", exc)


async def get_pending_ids(  # noqa: ASYNC910
    data_partition_id: str,
    analysis_family: str,
    analysis_type: str,
    target_schema_version: str,
) -> List[Tuple[str, str]]:
    """Return (dataset_id, wpc_id) tuples from recently-written URNs that
    match the given analysis type and schema version.

    Returns an empty list when Redis is unavailable or caching is disabled.
    """
    redis = _get_redis()
    pending_ids: List[Tuple[str, str]] = []
    if redis is None:
        return pending_ids
    try:
        key = _pending_key(data_partition_id)
        raw_urns = await redis.smembers(key)
        if raw_urns:
            urns = [raw_urn.decode() if isinstance(raw_urn, bytes) else raw_urn for raw_urn in raw_urns]
            pending_ids = get_valid_ids_from_ddms_datasets(
                ddms_datasets=urns,
                analysis_family=analysis_family,
                analysis_type=analysis_type,
                target_schema_version=target_schema_version,
            )
    except Exception as exc:  # noqa: B902, WPS329
        logger.debug("get_pending_ids: Redis error, skipping: {0}", exc)
    return pending_ids


async def supplement_with_pending_writes(  # noqa: WPS211
    result_ids: List[Tuple[str, str]],
    data_partition_id: str,
    analysis_family: str,
    analysis_type: str,
    target_schema_version: str,
) -> List[Tuple[str, str]]:
    """Merge pending-write entries into OSDU Search results.

    Records written recently may not yet appear in the OSDU Search index
    due to indexer lag. This supplements the search results with any
    matching URNs stored in the write-through Redis cache, deduplicating
    by wpc_id so already-indexed records are not repeated.
    """
    pending = await get_pending_ids(
        data_partition_id=data_partition_id,
        analysis_family=analysis_family,
        analysis_type=analysis_type,
        target_schema_version=target_schema_version,
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
