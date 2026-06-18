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

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.search.pending_writes import (
    PENDING_WRITES_TTL,
    _pending_key,
    get_pending_ids,
    record_pending_write,
    supplement_with_pending_writes,
)

PARTITION = "opendes"
ANALYSIS_FAMILY = "samplesanalysis"
ANALYSIS_TYPE = "routinecoreanalysis"
SCHEMA_VERSION = "1.0.0"

# Example URN: urn://rafsddms-v2/routinecoreanalysisdata/opendes:master-data--SamplesAnalysis:abc:1/opendes:dataset--File.Generic:routinecoreanalysis-uuid/1.0.0
_WPC_ID = "opendes:master-data--SamplesAnalysis:abc:1"
_DATASET_ID = f"opendes:dataset--File.Generic:{ANALYSIS_TYPE}-some-uuid"
_URN = f"urn://rafsddms-v2/{ANALYSIS_TYPE}data/{_WPC_ID}/{_DATASET_ID}/{SCHEMA_VERSION}"


def _mock_redis():
    redis = AsyncMock()
    redis.sadd = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.smembers = AsyncMock(return_value=set())
    return redis


def _patch_redis(redis):
    return patch("app.search.pending_writes._get_redis", return_value=redis)


# --- record_pending_write ---


@pytest.mark.asyncio
async def test_record_pending_write_stores_urn():
    redis = _mock_redis()
    with _patch_redis(redis):
        await record_pending_write(PARTITION, _URN)

    redis.sadd.assert_awaited_once_with(_pending_key(PARTITION), _URN)
    redis.expire.assert_awaited_once_with(_pending_key(PARTITION), PENDING_WRITES_TTL)


@pytest.mark.asyncio
async def test_record_pending_write_noop_when_no_redis():
    with _patch_redis(None):
        await record_pending_write(PARTITION, _URN)  # must not raise


@pytest.mark.asyncio
async def test_record_pending_write_swallows_redis_error():
    redis = _mock_redis()
    redis.sadd.side_effect = Exception("Redis down")
    with _patch_redis(redis):
        await record_pending_write(PARTITION, _URN)  # must not raise


# --- get_pending_ids ---


@pytest.mark.asyncio
async def test_get_pending_ids_returns_empty_when_no_redis():
    with _patch_redis(None):
        result = await get_pending_ids(PARTITION, ANALYSIS_FAMILY, ANALYSIS_TYPE, SCHEMA_VERSION)
    assert result == []


@pytest.mark.asyncio
async def test_get_pending_ids_returns_empty_when_set_empty():
    redis = _mock_redis()
    redis.smembers = AsyncMock(return_value=set())
    with _patch_redis(redis):
        result = await get_pending_ids(PARTITION, ANALYSIS_FAMILY, ANALYSIS_TYPE, SCHEMA_VERSION)
    assert result == []


@pytest.mark.asyncio
async def test_get_pending_ids_returns_matching_urn():
    redis = _mock_redis()
    redis.smembers = AsyncMock(return_value={_URN.encode()})
    with _patch_redis(redis):
        result = await get_pending_ids(PARTITION, ANALYSIS_FAMILY, ANALYSIS_TYPE, SCHEMA_VERSION)

    assert len(result) == 1
    dataset_id, wpc_id = result[0]
    assert ANALYSIS_TYPE in dataset_id
    assert wpc_id == _WPC_ID


@pytest.mark.asyncio
async def test_get_pending_ids_filters_wrong_analysis_type():
    redis = _mock_redis()
    redis.smembers = AsyncMock(return_value={_URN.encode()})
    with _patch_redis(redis):
        result = await get_pending_ids(PARTITION, ANALYSIS_FAMILY, "relativepermeability", SCHEMA_VERSION)
    assert result == []


@pytest.mark.asyncio
async def test_get_pending_ids_filters_wrong_schema_version():
    redis = _mock_redis()
    redis.smembers = AsyncMock(return_value={_URN.encode()})
    with _patch_redis(redis):
        result = await get_pending_ids(PARTITION, ANALYSIS_FAMILY, ANALYSIS_TYPE, "2.0.0")
    assert result == []


# --- supplement_with_pending_writes ---


@pytest.mark.asyncio
async def test_supplement_adds_missing_records():
    redis = _mock_redis()
    redis.smembers = AsyncMock(return_value={_URN.encode()})
    with _patch_redis(redis):
        result = await supplement_with_pending_writes(
            result_ids=[],
            data_partition_id=PARTITION,
            analysis_family=ANALYSIS_FAMILY,
            analysis_type=ANALYSIS_TYPE,
            target_schema_version=SCHEMA_VERSION,
        )
    assert len(result) == 1
    assert result[0][1] == _WPC_ID


@pytest.mark.asyncio
async def test_supplement_deduplicates_already_indexed():
    redis = _mock_redis()
    redis.smembers = AsyncMock(return_value={_URN.encode()})
    existing = [(_DATASET_ID, _WPC_ID)]
    with _patch_redis(redis):
        result = await supplement_with_pending_writes(
            result_ids=existing,
            data_partition_id=PARTITION,
            analysis_family=ANALYSIS_FAMILY,
            analysis_type=ANALYSIS_TYPE,
            target_schema_version=SCHEMA_VERSION,
        )
    assert result == existing  # no duplicate added


@pytest.mark.asyncio
async def test_supplement_passthrough_when_no_pending():
    redis = _mock_redis()
    redis.smembers = AsyncMock(return_value=set())
    existing = [("ds1", "wpc1")]
    with _patch_redis(redis):
        result = await supplement_with_pending_writes(
            result_ids=existing,
            data_partition_id=PARTITION,
            analysis_family=ANALYSIS_FAMILY,
            analysis_type=ANALYSIS_TYPE,
            target_schema_version=SCHEMA_VERSION,
        )
    assert result == existing
