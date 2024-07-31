#  Copyright 2024 ExxonMobil Technology and Engineering Company
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
import random
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from app.dev.search.analysis_type_ids_fetcher import (
    OsduAnalysisTypeIdsFetcher,
    RedisAnalysisTypeIdsFetcher,
)
from app.resources.paths import SAMPLESANALYSIS_TYPE_MAPPING

ANALYSIS_TYPE = random.choice(list(SAMPLESANALYSIS_TYPE_MAPPING.keys()))


@pytest.fixture
def analysis_type():
    return ANALYSIS_TYPE


@pytest.fixture
def urn(analysis_type):
    samples_analysis_id = "opendes:work-product-component--SamplesAnalysis:SA_ID"
    dataset_id = f"opendes:dataset--File.Generic:{analysis_type}-1:1"
    return f"urn://rafs-v2/{analysis_type}data/{samples_analysis_id}/{dataset_id}/1.0.0"


@pytest.fixture
def mock_search_service(urn):
    service = AsyncMock()
    service.find_records.side_effect = [
        {
            "results": [{"data": {"DDMSDatasets": [urn]}}],
        }, {},
    ]
    return service


@pytest.fixture
def mock_redis_client(urn):
    redis_client = Mock()
    ft_mock = AsyncMock()
    redis_client.ft.return_value = ft_mock
    json_str = json.dumps({"DDMSDatasets": urn, "ACLOwners": "owners_group", "ACLViewers": "viewers_group"})
    ft_mock.search.side_effect = [MagicMock(docs=[MagicMock(json=json_str)]), MagicMock()]
    return redis_client


@pytest.fixture
def mock_entitlements_service():
    service = AsyncMock()
    service.get_data_groups.return_value = ["owners_group", "viewers_group"]
    return service


@pytest.fixture
def osdu_fetcher(mock_search_service):
    return OsduAnalysisTypeIdsFetcher(mock_search_service)


@pytest.fixture
def redis_fetcher(mock_redis_client, mock_entitlements_service):
    return RedisAnalysisTypeIdsFetcher(mock_redis_client, mock_entitlements_service)


class TestOsduAnalysisTypeIdsFetcher:
    @pytest.mark.asyncio
    async def test_get_ids(self, osdu_fetcher, analysis_type):
        data_partition_id = "test_partition"
        target_schema_version = "1.0.0"
        wks_parameters = None

        result = await osdu_fetcher.get_ids(data_partition_id, analysis_type, target_schema_version, wks_parameters)

        samples_analysis_id = "opendes:work-product-component--SamplesAnalysis:SA_ID"
        dataset_id = f"opendes:dataset--File.Generic:{analysis_type}-1"
        assert result == [(dataset_id, samples_analysis_id)]


class TestRedisAnalysisTypeIdsFetcher:
    @pytest.mark.asyncio
    async def test_get_ids(self, redis_fetcher, analysis_type):
        data_partition_id = "test_partition"
        target_schema_version = "1.0.0"
        wks_parameters = None

        result = await redis_fetcher.get_ids(data_partition_id, analysis_type, target_schema_version, wks_parameters)

        samples_analysis_id = "opendes:work-product-component--SamplesAnalysis:SA_ID"
        dataset_id = f"opendes:dataset--File.Generic:{analysis_type}-1"
        assert result == [(dataset_id, samples_analysis_id)]
