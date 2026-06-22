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
from unittest.mock import AsyncMock, patch

import pytest

from app.search.pending_writes import (
    PENDING_WRITES_TTL,
    _pending_key,
    get_pending_ids,
    record_pending_write,
    supplement_with_pending_writes,
)

PARTITION = "opendes"
OTHER_PARTITION = "osdu"
ANALYSIS_FAMILY = "samplesanalysis"
ANALYSIS_TYPE = "routinecoreanalysis"
SCHEMA_VERSION = "1.0.0"

# Example URN: urn://rafsddms-v2/routinecoreanalysisdata/opendes:master-data--SamplesAnalysis:abc:1/opendes:dataset--File.Generic:routinecoreanalysis-uuid/1.0.0
_WPC_ID = "opendes:master-data--SamplesAnalysis:abc:1"
_DATASET_ID = f"opendes:dataset--File.Generic:{ANALYSIS_TYPE}-some-uuid"
_URN = f"urn://rafsddms-v2/{ANALYSIS_TYPE}data/{_WPC_ID}/{_DATASET_ID}/{SCHEMA_VERSION}"

# A second, distinct dataset for the SAME wpc_id (simulates a rapid re-upload /
# a second analysis-type dataset attached to the same record).
_DATASET_ID_2 = f"opendes:dataset--File.Generic:{ANALYSIS_TYPE}-some-other-uuid"
_URN_2 = f"urn://rafsddms-v2/{ANALYSIS_TYPE}data/{_WPC_ID}/{_DATASET_ID_2}/{SCHEMA_VERSION}"

_WELLBORE_A = "opendes:master-data--Wellbore:A:"
_WELLBORE_B = "opendes:master-data--Wellbore:B:"


def _entry(urn=_URN, wpc_id=_WPC_ID, scope=None):
    return json.dumps({"ddms_urn": urn, "wpc_id": wpc_id, "scope": scope or {}})


def _mock_redis():
    redis = AsyncMock()
    redis.hset = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.hgetall = AsyncMock(return_value={})
    return redis


def _patch_redis(redis):
    return patch("app.search.pending_writes._get_redis", return_value=redis)


# --- record_pending_write ---


@pytest.mark.asyncio
async def test_record_pending_write_stores_hash_entry_keyed_by_dataset_id():
    redis = _mock_redis()
    with _patch_redis(redis):
        await record_pending_write(PARTITION, _URN, scope={"wellbore_id": _WELLBORE_A})

    assert redis.hset.await_count == 1
    call = redis.hset.await_args
    assert call.args[0] == _pending_key(PARTITION)
    assert call.args[1] == _DATASET_ID
    stored_payload = json.loads(call.args[2])
    assert stored_payload["ddms_urn"] == _URN
    assert stored_payload["wpc_id"] == _WPC_ID
    assert stored_payload["scope"] == {"wellbore_id": _WELLBORE_A}
    redis.expire.assert_awaited_once_with(_pending_key(PARTITION), PENDING_WRITES_TTL)


@pytest.mark.asyncio
async def test_record_pending_write_defaults_scope_to_empty_dict():
    redis = _mock_redis()
    with _patch_redis(redis):
        await record_pending_write(PARTITION, _URN)

    stored_payload = json.loads(redis.hset.await_args.args[2])
    assert stored_payload["scope"] == {}


@pytest.mark.asyncio
async def test_record_pending_write_noop_when_no_redis():
    with _patch_redis(None):
        await record_pending_write(PARTITION, _URN)  # must not raise


@pytest.mark.asyncio
async def test_record_pending_write_swallows_redis_error():
    redis = _mock_redis()
    redis.hset.side_effect = Exception("Redis down")
    with _patch_redis(redis):
        await record_pending_write(PARTITION, _URN)  # must not raise


@pytest.mark.asyncio
async def test_record_pending_write_skips_unparseable_urn():
    redis = _mock_redis()
    with _patch_redis(redis):
        await record_pending_write(PARTITION, "not-a-valid-urn")  # must not raise
    redis.hset.assert_not_awaited()


# --- get_pending_ids ---


@pytest.mark.asyncio
async def test_get_pending_ids_returns_empty_when_no_redis():
    with _patch_redis(None):
        result = await get_pending_ids(PARTITION, ANALYSIS_FAMILY, ANALYSIS_TYPE, SCHEMA_VERSION)
    assert result == []


@pytest.mark.asyncio
async def test_get_pending_ids_returns_empty_when_hash_empty():
    redis = _mock_redis()
    redis.hgetall = AsyncMock(return_value={})
    with _patch_redis(redis):
        result = await get_pending_ids(PARTITION, ANALYSIS_FAMILY, ANALYSIS_TYPE, SCHEMA_VERSION)
    assert result == []


@pytest.mark.asyncio
async def test_get_pending_ids_returns_matching_urn():
    redis = _mock_redis()
    redis.hgetall = AsyncMock(return_value={_DATASET_ID.encode(): _entry().encode()})
    with _patch_redis(redis):
        result = await get_pending_ids(PARTITION, ANALYSIS_FAMILY, ANALYSIS_TYPE, SCHEMA_VERSION)

    assert len(result) == 1
    dataset_id, wpc_id = result[0]
    assert ANALYSIS_TYPE in dataset_id
    assert wpc_id == _WPC_ID


@pytest.mark.asyncio
async def test_get_pending_ids_filters_wrong_analysis_type():
    redis = _mock_redis()
    redis.hgetall = AsyncMock(return_value={_DATASET_ID.encode(): _entry().encode()})
    with _patch_redis(redis):
        result = await get_pending_ids(PARTITION, ANALYSIS_FAMILY, "relativepermeability", SCHEMA_VERSION)
    assert result == []


@pytest.mark.asyncio
async def test_get_pending_ids_filters_wrong_schema_version():
    redis = _mock_redis()
    redis.hgetall = AsyncMock(return_value={_DATASET_ID.encode(): _entry().encode()})
    with _patch_redis(redis):
        result = await get_pending_ids(PARTITION, ANALYSIS_FAMILY, ANALYSIS_TYPE, "2.0.0")
    assert result == []


@pytest.mark.asyncio
async def test_get_pending_ids_skips_malformed_entry():
    redis = _mock_redis()
    redis.hgetall = AsyncMock(return_value={_DATASET_ID.encode(): b"not-json"})
    with _patch_redis(redis):
        result = await get_pending_ids(PARTITION, ANALYSIS_FAMILY, ANALYSIS_TYPE, SCHEMA_VERSION)
    assert result == []  # must not raise, malformed entry is simply skipped


# --- get_pending_ids: scope isolation (closes lead-feedback Issue #1/#2) ---


@pytest.mark.asyncio
@pytest.mark.parametrize("scope_key", ["well_id", "wellbore_id", "field_id", "basin_id"])
async def test_get_pending_ids_excludes_entry_scoped_to_a_different_value(scope_key):
    entry_scope = {scope_key: "scope-A"}
    redis = _mock_redis()
    redis.hgetall = AsyncMock(return_value={_DATASET_ID.encode(): _entry(scope=entry_scope).encode()})
    with _patch_redis(redis):
        result = await get_pending_ids(
            PARTITION,
            ANALYSIS_FAMILY,
            ANALYSIS_TYPE,
            SCHEMA_VERSION,
            scope={scope_key: "scope-B"},
        )
    assert result == []


@pytest.mark.asyncio
@pytest.mark.parametrize("scope_key", ["well_id", "wellbore_id", "field_id", "basin_id"])
async def test_get_pending_ids_includes_entry_scoped_to_the_matching_value(scope_key):
    entry_scope = {scope_key: "scope-A"}
    redis = _mock_redis()
    redis.hgetall = AsyncMock(return_value={_DATASET_ID.encode(): _entry(scope=entry_scope).encode()})
    with _patch_redis(redis):
        result = await get_pending_ids(
            PARTITION,
            ANALYSIS_FAMILY,
            ANALYSIS_TYPE,
            SCHEMA_VERSION,
            scope={scope_key: "scope-A"},
        )
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_pending_ids_unscoped_request_still_returns_everything():
    """No regression: an unscoped search (today's default behavior) must still
    return pending entries regardless of their stored scope."""
    redis = _mock_redis()
    redis.hgetall = AsyncMock(
        return_value={_DATASET_ID.encode(): _entry(scope={"wellbore_id": _WELLBORE_A}).encode()},
    )
    with _patch_redis(redis):
        result = await get_pending_ids(PARTITION, ANALYSIS_FAMILY, ANALYSIS_TYPE, SCHEMA_VERSION, scope=None)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_pending_ids_scoped_request_excludes_scopeless_entry():
    """A pending entry with no stored scope must not match a scoped search —
    matching everything would silently re-introduce the scope-leakage bug."""
    redis = _mock_redis()
    redis.hgetall = AsyncMock(return_value={_DATASET_ID.encode(): _entry(scope={}).encode()})
    with _patch_redis(redis):
        result = await get_pending_ids(
            PARTITION,
            ANALYSIS_FAMILY,
            ANALYSIS_TYPE,
            SCHEMA_VERSION,
            scope={"wellbore_id": _WELLBORE_A},
        )
    assert result == []


@pytest.mark.asyncio
async def test_get_pending_ids_entry_missing_one_requested_key_excluded():
    """An entry that only has wellbore_id must not match a search additionally
    scoped to a basin_id it has no value for."""
    redis = _mock_redis()
    redis.hgetall = AsyncMock(
        return_value={_DATASET_ID.encode(): _entry(scope={"wellbore_id": _WELLBORE_A}).encode()},
    )
    with _patch_redis(redis):
        result = await get_pending_ids(
            PARTITION,
            ANALYSIS_FAMILY,
            ANALYSIS_TYPE,
            SCHEMA_VERSION,
            scope={"wellbore_id": _WELLBORE_A, "basin_id": "basin-1"},
        )
    assert result == []


@pytest.mark.asyncio
async def test_get_pending_ids_entry_with_subset_of_requested_keys_matches():
    """An entry need not carry all four scope keys — only the ones present in
    the request must match."""
    redis = _mock_redis()
    redis.hgetall = AsyncMock(
        return_value={_DATASET_ID.encode(): _entry(scope={"wellbore_id": _WELLBORE_A}).encode()},
    )
    with _patch_redis(redis):
        result = await get_pending_ids(
            PARTITION,
            ANALYSIS_FAMILY,
            ANALYSIS_TYPE,
            SCHEMA_VERSION,
            scope={"wellbore_id": _WELLBORE_A},
        )
    assert len(result) == 1


# --- get_pending_ids: partition isolation (auditor's flagged gap) ---


@pytest.mark.asyncio
async def test_get_pending_ids_partition_isolation():
    redis = _mock_redis()

    async def hgetall_side_effect(key):
        if key == _pending_key(PARTITION):
            return {_DATASET_ID.encode(): _entry().encode()}
        return {}

    redis.hgetall = AsyncMock(side_effect=hgetall_side_effect)
    with _patch_redis(redis):
        result = await get_pending_ids(OTHER_PARTITION, ANALYSIS_FAMILY, ANALYSIS_TYPE, SCHEMA_VERSION)
    assert result == []


# --- dataset-keying / TTL-race (closes lead-feedback Issue #3 + auditor's flagged race) ---


@pytest.mark.asyncio
async def test_get_pending_ids_two_datasets_for_same_wpc_id_both_survive():
    """Two record_pending_write calls for the same wpc_id with different dataset_ids
    (e.g. a rapid re-upload, or two distinct datasets attached to one record) must
    both be retrievable — neither silently dropped via non-deterministic Set/merge
    iteration. This is the regression test for the auditor's TTL-race finding: the
    old flat-Set storage kept both URNs in one Set, and supplement_with_pending_writes'
    wpc_id-based dedup against already-indexed result_ids made which dataset_id
    survived the merge step non-deterministic (smembers() has no defined order).
    The Hash-based storage below keys each dataset by its own dataset_id, so both
    coexist deterministically with no ambiguity."""
    redis = _mock_redis()
    redis.hgetall = AsyncMock(
        return_value={
            _DATASET_ID.encode(): _entry(urn=_URN, wpc_id=_WPC_ID).encode(),
            _DATASET_ID_2.encode(): _entry(urn=_URN_2, wpc_id=_WPC_ID).encode(),
        },
    )
    with _patch_redis(redis):
        result = await get_pending_ids(PARTITION, ANALYSIS_FAMILY, ANALYSIS_TYPE, SCHEMA_VERSION)

    dataset_ids = {dataset_id for dataset_id, _ in result}
    assert dataset_ids == {_DATASET_ID, _DATASET_ID_2}


@pytest.mark.asyncio
async def test_record_pending_write_same_dataset_id_overwrites_deterministically():
    """A second record_pending_write call for the SAME dataset_id (re-upload of the
    exact same dataset) must overwrite the prior entry, not create ambiguity — this
    is HSET's natural semantics and is the intended behavior, not a race."""
    redis = _mock_redis()
    with _patch_redis(redis):
        await record_pending_write(PARTITION, _URN, scope={"wellbore_id": _WELLBORE_A})
        await record_pending_write(PARTITION, _URN, scope={"wellbore_id": _WELLBORE_B})

    assert redis.hset.await_count == 2
    # Both calls target the same Hash field (dataset_id) — HSET overwrite means the
    # final read sees only the most recent payload, deterministically.
    assert redis.hset.await_args_list[0].args[1] == _DATASET_ID
    assert redis.hset.await_args_list[1].args[1] == _DATASET_ID


# --- supplement_with_pending_writes ---


@pytest.mark.asyncio
async def test_supplement_adds_missing_records():
    redis = _mock_redis()
    redis.hgetall = AsyncMock(return_value={_DATASET_ID.encode(): _entry().encode()})
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
    redis.hgetall = AsyncMock(return_value={_DATASET_ID.encode(): _entry().encode()})
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
    redis.hgetall = AsyncMock(return_value={})
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


@pytest.mark.asyncio
async def test_supplement_excludes_pending_entry_outside_requested_scope():
    """End-to-end scope-leakage regression: a pending write recorded for
    wellbore-A must not appear in a search scoped to wellbore-B."""
    redis = _mock_redis()
    redis.hgetall = AsyncMock(
        return_value={_DATASET_ID.encode(): _entry(scope={"wellbore_id": _WELLBORE_A}).encode()},
    )
    with _patch_redis(redis):
        result = await supplement_with_pending_writes(
            result_ids=[],
            data_partition_id=PARTITION,
            analysis_family=ANALYSIS_FAMILY,
            analysis_type=ANALYSIS_TYPE,
            target_schema_version=SCHEMA_VERSION,
            scope={"wellbore_id": _WELLBORE_B},
        )
    assert result == []


@pytest.mark.asyncio
async def test_supplement_includes_pending_entry_inside_requested_scope():
    redis = _mock_redis()
    redis.hgetall = AsyncMock(
        return_value={_DATASET_ID.encode(): _entry(scope={"wellbore_id": _WELLBORE_A}).encode()},
    )
    with _patch_redis(redis):
        result = await supplement_with_pending_writes(
            result_ids=[],
            data_partition_id=PARTITION,
            analysis_family=ANALYSIS_FAMILY,
            analysis_type=ANALYSIS_TYPE,
            target_schema_version=SCHEMA_VERSION,
            scope={"wellbore_id": _WELLBORE_A},
        )
    assert len(result) == 1
