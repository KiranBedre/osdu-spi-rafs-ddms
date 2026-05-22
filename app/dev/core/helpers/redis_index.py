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

from loguru import logger
from redis.asyncio.client import Redis
from redis.commands.search.field import TagField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.exceptions import ResponseError

from app.core.config import get_app_settings
from app.providers.dependencies.redis_factory import get_redis_factory

SAMPLESANALYSIS_IX = "idx:{partition}-samplesanalyses"
SAMPLESANALYSIS_IX_PREFIX = "{partition}-samplesanalysis:"


async def get_redis_client() -> Redis:
    """Get Redis client for index operations.

    Uses provider-specific factory if available, otherwise defaults to base factory.
    Provider resolution happens at runtime based on CLOUD_PROVIDER setting.

    :return: Connected Redis client
    :rtype: Redis
    """
    settings = get_app_settings()
    factory = get_redis_factory(settings, use_index_database=True)
    return await factory.create_client()


def build_samplesanalysis_schema():
    return (  # noqa: WPS227
        TagField("$.SamplesAnalysisID", as_name="SamplesAnalysisID"),
        TagField("$.ACLViewers", as_name="ACLViewers"),
        TagField("$.ACLOwners", as_name="ACLOwners"),
        TagField("$.DDMSDatasets", as_name="DDMSDatasets"),
        TagField("$.SampleIDs", as_name="SampleIDs"),
        TagField("$.SampleTypeIDs", as_name="SampleTypeIDs"),
        TagField("$.ParentSamplesAnalysesReports", as_name="ParentSamplesAnalysesReports"),
        TagField("$.SampleAnalysisTypeIDs", as_name="SampleAnalysisTypeIDs"),
        TagField("$.WellboreIDs", as_name="WellboreIDs"),
        TagField("$.WellboreNames", as_name="WellboreNames"),
        TagField("$.BasinIDs", as_name="BasinIDs"),
        TagField("$.BasinNames", as_name="BasinNames"),
        TagField("$.FieldIDs", as_name="FieldIDs"),
        TagField("$.FieldNames", as_name="FieldNames"),
    )


async def create_samplesanalysis_index(redis_client: Redis, partition: str):
    schema = build_samplesanalysis_schema()
    definition = IndexDefinition(
        prefix=[SAMPLESANALYSIS_IX_PREFIX.format(partition=partition)],
        index_type=IndexType.JSON,
    )
    await redis_client.ft(
        SAMPLESANALYSIS_IX.format(partition=partition),
    ).create_index(
        fields=schema,
        definition=definition,
    )


async def init_samplesanalysis_index(partition: str):
    redis_client = await get_redis_client()
    try:
        index_info = await redis_client.ft(SAMPLESANALYSIS_IX.format(partition=partition)).info()
        logger.debug(index_info)
    except ResponseError as exc:
        exc_msg = str(exc)
        warn_msg = f"Initializing index: {exc_msg}"
        logger.warning(warn_msg)
        await create_samplesanalysis_index(redis_client, partition)


async def is_index_initialized(index_name: str) -> bool:
    redis_client = await get_redis_client()
    try:
        initialized = bool(await redis_client.ft(index_name).info())
    except ResponseError:
        initialized = False
    return initialized
