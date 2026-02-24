import pytest

from app.api.routes.utils.records import (
    generate_dataset_urn,
    update_dataset_id,
)
from tests.test_api.api_version import API_VERSION

TEST_DATA_PARTITION_ID = "partition"
TEST_DDMS_ID = "rafs"
TEST_WPC_TYPE = "RockSampleAnalysis"
TEST_ENTITY_TYPE = "routine-core-analysis"
TEST_ENTITY_ID = "123"
TEST_SCHEMA_VERSION = "1.0.0"


def generate_test_id(
    data_partition_id=TEST_DATA_PARTITION_ID,
    wpc_type=TEST_WPC_TYPE,
):
    return f"{data_partition_id}:work-product-component--{wpc_type}:{wpc_type}_test"


def generate_test_dataset_record_id(
    data_partition_id=TEST_DATA_PARTITION_ID,
    entity_type=TEST_ENTITY_TYPE,
    entity_id=TEST_ENTITY_ID,
):
    return f"{data_partition_id}:dataset--File.Generic:{entity_type}-{entity_id}:1234"


TEST_RECORD_ID = generate_test_id()
TEST_DATASET_RECORD_ID = generate_test_dataset_record_id()


def generate_test_ddms_urn(
    ddms_id=TEST_DDMS_ID,
    api_version=API_VERSION,
    entity_type=f"{TEST_ENTITY_TYPE}data",
    wpc_id=TEST_RECORD_ID,
    dataset_id=TEST_DATASET_RECORD_ID,
    content_schema_version=TEST_SCHEMA_VERSION,
):
    return generate_dataset_urn(ddms_id, api_version, entity_type, wpc_id, dataset_id, content_schema_version)


TEST_DDMS_DATASET_URN = generate_test_ddms_urn()
ORIGINAL_DDMS_DATASETS = [TEST_DDMS_DATASET_URN]


@pytest.mark.asyncio
async def test_update_empty_ddms_dataset():
    ddms_datasets = update_dataset_id([], "", "")
    assert not ddms_datasets


@pytest.mark.asyncio
async def test_update_same_ddms_dataset():
    ddms_datasets = update_dataset_id(ORIGINAL_DDMS_DATASETS, TEST_DDMS_DATASET_URN, TEST_ENTITY_TYPE)
    assert ORIGINAL_DDMS_DATASETS == ddms_datasets


@pytest.mark.asyncio
async def test_update_different_entity_ddms_dataset():
    wpc_type = "ConstantCompositionExpansion"
    entity_type = "constant-composition-expansion"
    wpc_id = generate_test_id(wpc_type=wpc_type)
    dataset_id = generate_test_dataset_record_id(entity_type=entity_type)
    ddms_dataset_urn = generate_test_ddms_urn(
        entity_type=f"{entity_type}data",
        wpc_id=wpc_id,
        dataset_id=dataset_id,
    )
    original_ddms_datasets = [*ORIGINAL_DDMS_DATASETS, ddms_dataset_urn]

    ddms_datasets = update_dataset_id(original_ddms_datasets, ddms_dataset_urn, entity_type)
    assert TEST_DDMS_DATASET_URN in ddms_datasets
    assert ddms_dataset_urn in ddms_datasets

    ddms_datasets = update_dataset_id(original_ddms_datasets, TEST_DDMS_DATASET_URN, TEST_ENTITY_TYPE)
    assert TEST_DDMS_DATASET_URN in ddms_datasets
    assert ddms_dataset_urn in ddms_datasets
