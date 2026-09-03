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

from unittest.mock import MagicMock

import pytest

from app.api.routes.utils.search import get_valid_ids_from_ddms_datasets

# Sample valid URNs
ANALYSIS_TYPE_EXAMPLE = "constantcompositionexpansion"
WPC_ID_EXAMPLE = "opendes:work-product-component--SamplesAnalysis:WPC"
VERSION_EXAMPLE = "1.0.0"
UUID_EXAMPLE = "98d5ccda-1333-42dc-8457-d2e188d094e1"
DATASET_ID_EXAMPLE = f"opendes:dataset--File.Generic:{ANALYSIS_TYPE_EXAMPLE}-{UUID_EXAMPLE}"
BLOB_ID_EXAMPLE = f"samplesanalysis/{ANALYSIS_TYPE_EXAMPLE}/{VERSION_EXAMPLE}/{UUID_EXAMPLE}"
VALID_BLOB_URN = f"urn://rafs/{WPC_ID_EXAMPLE}/{BLOB_ID_EXAMPLE}"
VALID_DATASET_URN = f"urn://rafs-v2/{ANALYSIS_TYPE_EXAMPLE}data/{WPC_ID_EXAMPLE}/{DATASET_ID_EXAMPLE}/{VERSION_EXAMPLE}"


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.use_blob_storage = True
    return settings


@pytest.fixture
def ddms_datasets():
    """Fixture to provide sample URNs."""
    return [
        VALID_BLOB_URN,
        VALID_DATASET_URN,
        "urn://invalid/urn",  # Invalid URN
    ]


def test_get_valid_ids_blob_storage_enabled(mock_settings, ddms_datasets, monkeypatch):
    """Test get_valid_ids_from_ddms_datasets with blob storage enabled."""
    monkeypatch.setattr("app.api.routes.utils.search.get_app_settings", lambda: mock_settings)

    analysis_family = "samplesanalysis"
    result = get_valid_ids_from_ddms_datasets(
        ddms_datasets=ddms_datasets,
        analysis_family=analysis_family,
        analysis_type=ANALYSIS_TYPE_EXAMPLE,
        target_schema_version=VERSION_EXAMPLE,
    )

    assert result == [(BLOB_ID_EXAMPLE, WPC_ID_EXAMPLE)]


def test_get_valid_ids_blob_storage_disabled(ddms_datasets):
    """Test get_valid_ids_from_ddms_datasets with blob storage disabled."""

    result = get_valid_ids_from_ddms_datasets(
        ddms_datasets=ddms_datasets,
        analysis_family="not_used",  # Not used when blob storage is disabled
        analysis_type=ANALYSIS_TYPE_EXAMPLE,
        target_schema_version=VERSION_EXAMPLE,
    )

    assert result == [(DATASET_ID_EXAMPLE, WPC_ID_EXAMPLE)]


def test_get_valid_ids_no_valid_urns():
    """Test get_valid_ids_from_ddms_datasets with no valid URNs."""

    ddms_datasets = ["urn://invalid/urn", "urn://another/invalid/urn"]
    analysis_family = "samplesanalysis"
    analysis_type = "constantcompositionexpansion"
    target_schema_version = "1.0.0"

    result = get_valid_ids_from_ddms_datasets(
        ddms_datasets=ddms_datasets,
        analysis_family=analysis_family,
        analysis_type=analysis_type,
        target_schema_version=target_schema_version,
    )

    assert result == []


def test_get_valid_ids_selects_only_the_requested_schema_version():
    """A WPC record's DDMSDatasets can accumulate datasets from more than one
    schema version (e.g. a record that received both a v1.0.0 and a v1.1.0
    upload). Regression guard for a search flake where the response for a
    v1.1.0 query appeared to include v1.0.0 content: this asserts RAFS's own
    dataset selection logic picks exactly the dataset matching the requested
    target_schema_version, never both.
    """
    analysis_type = "relativepermeability"
    wpc_id = "opendes:work-product-component--SamplesAnalysis:WPC"
    dataset_id_v1 = f"opendes:dataset--File.Generic:{analysis_type}-{UUID_EXAMPLE}"
    dataset_id_v1_1_uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    dataset_id_v1_1 = f"opendes:dataset--File.Generic:{analysis_type}-{dataset_id_v1_1_uuid}"

    ddms_datasets = [
        f"urn://rafs-v2/{analysis_type}data/{wpc_id}/{dataset_id_v1}/1.0.0",
        f"urn://rafs-v2/{analysis_type}data/{wpc_id}/{dataset_id_v1_1}/1.1.0",
    ]

    result_v1 = get_valid_ids_from_ddms_datasets(
        ddms_datasets=ddms_datasets,
        analysis_family="samplesanalysis",
        analysis_type=analysis_type,
        target_schema_version="1.0.0",
    )
    result_v1_1 = get_valid_ids_from_ddms_datasets(
        ddms_datasets=ddms_datasets,
        analysis_family="samplesanalysis",
        analysis_type=analysis_type,
        target_schema_version="1.1.0",
    )

    assert result_v1 == [(dataset_id_v1, wpc_id)]
    assert result_v1_1 == [(dataset_id_v1_1, wpc_id)]
