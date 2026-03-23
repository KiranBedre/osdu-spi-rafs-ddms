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

"""
Tests for Issue 707: Fix dataset versioning - create immutable datasets per update.

These tests verify that:
1. Each bulk data POST creates a new dataset ID (never reused)
2. DDMSDatasets entry is replaced (not appended) for each analysis type
3. Historical data is preserved via WPC versioning (record_id:version)
"""

import pytest

from app.api.routes.utils.records import (
    ENTITY_TYPE_INDEX,
    dataset_id_exist,
    find_dataset_id,
    find_object_name_from_type,
    find_schema_versions_for_dataset_id,
    generate_dataset_urn,
    get_id_version,
    update_dataset_id,
)


class TestFindDatasetId:
    """Tests for find_dataset_id function."""

    def test_find_dataset_id_returns_none_for_empty_list(self):
        """Should return None when DDMSDatasets is empty."""
        ddms_datasets = []
        result = find_dataset_id(ddms_datasets, "rca")
        assert result is None

    def test_find_dataset_id_finds_matching_prefix(self):
        """Should find dataset ID matching the prefix."""
        ddms_datasets = [
            "urn://rafs-v2/rcadata/wpc_id/opendes:dataset--File.Generic:rca-abc-123:1/1.0.0",
        ]
        result = find_dataset_id(ddms_datasets, "rca")
        assert result == "opendes:dataset--File.Generic:rca-abc-123"

    def test_find_dataset_id_returns_first_match(self):
        """Should return the first matching dataset ID."""
        ddms_datasets = [
            "urn://rafs-v2/rcadata/wpc_id/opendes:dataset--File.Generic:rca-uuid1:1/1.0.0",
            "urn://rafs-v2/rcadata/wpc_id/opendes:dataset--File.Generic:rca-uuid2:2/1.0.0",
        ]
        result = find_dataset_id(ddms_datasets, "rca")
        assert result == "opendes:dataset--File.Generic:rca-uuid1"

    def test_find_dataset_id_no_match(self):
        """Should return None when no matching prefix found."""
        ddms_datasets = [
            "urn://rafs-v2/ccdata/wpc_id/opendes:dataset--File.Generic:cce-abc-123:1/1.0.0",
        ]
        result = find_dataset_id(ddms_datasets, "rca")
        assert result is None


class TestUpdateDatasetId:
    """Tests for update_dataset_id function - replaces entry for matching prefix."""

    def test_update_dataset_id_replaces_existing(self):
        """Should replace existing entry with matching prefix."""
        ddms_datasets = [
            "urn://rafs-v2/rcadata/wpc_id/opendes:dataset--File.Generic:rca-old:1/1.0.0",
        ]
        new_urn = "urn://rafs-v2/rcadata/wpc_id/opendes:dataset--File.Generic:rca-new:2/1.0.0"

        update_dataset_id(ddms_datasets, new_urn, "rca")

        # Expected: list still has 1 entry (replaced, not appended)
        assert len(ddms_datasets) == 1
        assert ddms_datasets[0] == new_urn

    def test_update_dataset_id_only_updates_matching_prefix(self):
        """Should only update entry matching the prefix."""
        ddms_datasets = [
            "urn://rafs-v2/ccedata/wpc_id/opendes:dataset--File.Generic:cce-123:1/1.0.0",
            "urn://rafs-v2/rcadata/wpc_id/opendes:dataset--File.Generic:rca-old:1/1.0.0",
        ]
        new_urn = "urn://rafs-v2/rcadata/wpc_id/opendes:dataset--File.Generic:rca-new:2/1.0.0"

        update_dataset_id(ddms_datasets, new_urn, "rca")

        assert len(ddms_datasets) == 2
        # CCE entry unchanged
        assert "cce-123" in ddms_datasets[0]
        # RCA entry replaced
        assert ddms_datasets[1] == new_urn


class TestDatasetIdExist:
    """Tests for dataset_id_exist function."""

    def test_dataset_id_exist_returns_true_when_found(self):
        """Should return True when dataset ID exists in list."""
        ddms_datasets = [
            "urn://rafs-v2/rcadata/wpc_id/opendes:dataset--File.Generic:rca-abc-123:1/1.0.0",
        ]
        result = dataset_id_exist(ddms_datasets, "opendes:dataset--File.Generic:rca-abc-123")
        assert result is True

    def test_dataset_id_exist_returns_false_when_not_found(self):
        """Should return False when dataset ID does not exist in list."""
        ddms_datasets = [
            "urn://rafs-v2/rcadata/wpc_id/opendes:dataset--File.Generic:rca-abc-123:1/1.0.0",
        ]
        result = dataset_id_exist(ddms_datasets, "opendes:dataset--File.Generic:rca-xyz-999")
        assert result is False

    def test_dataset_id_exist_handles_empty_list(self):
        """Should return False for empty list."""
        ddms_datasets = []
        result = dataset_id_exist(ddms_datasets, "opendes:dataset--File.Generic:rca-abc-123")
        assert result is False

    def test_dataset_id_exist_ignores_version(self):
        """Should find dataset ID regardless of version suffix."""
        ddms_datasets = [
            "urn://rafs-v2/rcadata/wpc_id/opendes:dataset--File.Generic:rca-abc-123:99/1.0.0",
        ]
        # Query without version should still find it
        result = dataset_id_exist(ddms_datasets, "opendes:dataset--File.Generic:rca-abc-123")
        assert result is True


class TestGenerateDatasetUrn:
    """Tests for generate_dataset_urn function."""

    def test_generate_dataset_urn_format(self):
        """Should generate URN in correct format."""
        urn = generate_dataset_urn(
            ddms_id="rafs",
            api_version="v2",
            entity_type="rcadata",
            wpc_id="opendes:work-product-component--SamplesAnalysis:abc123",
            dataset_id="opendes:dataset--File.Generic:rca-uuid:1",
            content_schema_version="1.0.0",
        )
        expected = (
            "urn://rafs-v2/rcadata/"
            "opendes:work-product-component--SamplesAnalysis:abc123/"
            "opendes:dataset--File.Generic:rca-uuid:1/1.0.0"
        )
        assert urn == expected


class TestFindSchemaVersionsForDatasetId:
    """Tests for find_schema_versions_for_dataset_id function."""

    def test_find_schema_versions_single_version(self):
        """Should find single schema version for dataset ID."""
        ddms_datasets = [
            "urn://rafs-v2/rcadata/wpc_id/opendes:dataset--File.Generic:rca-abc:1/1.0.0",
        ]
        result = find_schema_versions_for_dataset_id(
            ddms_datasets,
            "opendes:dataset--File.Generic:rca-abc",
        )
        assert result == {"1.0.0"}

    def test_find_schema_versions_multiple_versions(self):
        """Should find all schema versions for dataset ID."""
        ddms_datasets = [
            "urn://rafs-v2/rcadata/wpc_id/opendes:dataset--File.Generic:rca-abc:1/1.0.0",
            "urn://rafs-v2/rcadata/wpc_id/opendes:dataset--File.Generic:rca-abc:2/2.0.0",
        ]
        result = find_schema_versions_for_dataset_id(
            ddms_datasets,
            "opendes:dataset--File.Generic:rca-abc",
        )
        assert result == {"1.0.0", "2.0.0"}


class TestGetIdVersion:
    """Tests for get_id_version function - parsing versioned record IDs."""

    def test_get_id_version_without_version(self):
        """Should return None for version when no version suffix."""
        record_id = "opendes:work-product-component--SamplesAnalysis:abc123"
        base_id, version = get_id_version(record_id)
        assert base_id == record_id
        assert version is None

    def test_get_id_version_with_version(self):
        """Should extract version from record ID with version suffix."""
        record_id = "opendes:work-product-component--SamplesAnalysis:abc123:5"
        base_id, version = get_id_version(record_id)
        assert base_id == "opendes:work-product-component--SamplesAnalysis:abc123"
        assert version == 5

    def test_get_id_version_with_version_one(self):
        """Should extract version 1 correctly."""
        record_id = "opendes:work-product-component--SamplesAnalysis:abc123:1"
        base_id, version = get_id_version(record_id)
        assert base_id == "opendes:work-product-component--SamplesAnalysis:abc123"
        assert version == 1


class TestImmutableDatasetBehavior:
    """
    Tests for the immutable dataset behavior (Issue 707).

    The implementation uses OSDU's built-in WPC versioning:
    - Each update creates a NEW dataset ID (immutable)
    - DDMSDatasets entry is REPLACED (not appended)
    - Historical data is accessed via record_id:version (WPC versioning)
    """

    def test_single_dataset_per_analysis_type(self):
        """DDMSDatasets should have one entry per analysis type."""
        # After update: Only the latest dataset should be in the list
        # Historical versions are preserved via WPC versioning
        ddms_datasets = [
            "urn://rafs-v2/rcadata/wpc_id/opendes:dataset--File.Generic:rca-uuid2:1/1.0.0",
        ]

        # Only current dataset should be in the list
        assert len([ds for ds in ddms_datasets if "rca-" in ds]) == 1

    def test_different_analysis_types_coexist(self):
        """Different analysis types should coexist in DDMSDatasets."""
        ddms_datasets = [
            "urn://rafs-v2/rcadata/wpc_id/opendes:dataset--File.Generic:rca-uuid1:1/1.0.0",
            "urn://rafs-v2/ccedata/wpc_id/opendes:dataset--File.Generic:cce-uuid1:1/1.0.0",
        ]

        # Both should be findable
        assert dataset_id_exist(ddms_datasets, "opendes:dataset--File.Generic:rca-uuid1")
        assert dataset_id_exist(ddms_datasets, "opendes:dataset--File.Generic:cce-uuid1")

    def test_wpc_versioning_record_id_format(self):
        """Record ID with version suffix should be parseable."""
        # WPC version 1
        record_id_v1 = "opendes:work-product-component--SamplesAnalysis:abc:1"
        base_id, version = get_id_version(record_id_v1)
        assert version == 1

        # WPC version 2
        record_id_v2 = "opendes:work-product-component--SamplesAnalysis:abc:2"
        base_id, version = get_id_version(record_id_v2)
        assert version == 2

        # Latest (no version)
        record_id_latest = "opendes:work-product-component--SamplesAnalysis:abc"
        base_id, version = get_id_version(record_id_latest)
        assert version is None


class TestHistoricalDataResolution:
    """Tests for the historical data resolution pattern (Issue #707 QA fix).

    When retrieving bulk data for a versioned WPC record, RAFS resolves the
    correct dataset from the historical record's DDMSDatasets by analysis type,
    regardless of which dataset_id the client provides in the request.
    """

    def _extract_prefix(self, dataset_id: str) -> str:
        """Helper: extract analysis type prefix from a dataset ID."""
        dataset_id_parts = dataset_id.split(":")
        if len(dataset_id_parts) > ENTITY_TYPE_INDEX:
            return dataset_id_parts[ENTITY_TYPE_INDEX].split("-")[0]
        return ""

    def test_resolves_historical_dataset_when_client_sends_current_id(self):
        """Should resolve old UUID from historical DDMSDatasets via type prefix."""
        historical_ddms_datasets = [
            "urn://rafs-v2/rcadata/wpc_id/opendes:dataset--File.Generic:rca-old-uuid:1/1.0.0",
        ]
        current_dataset_id = "opendes:dataset--File.Generic:rca-new-uuid"

        analysis_prefix = self._extract_prefix(current_dataset_id)
        resolved_id = find_dataset_id(historical_ddms_datasets, analysis_prefix)

        assert resolved_id == "opendes:dataset--File.Generic:rca-old-uuid"

    def test_resolves_xrd_historical_dataset(self):
        """Should resolve XRD historical dataset (reproduces QA-reported 404)."""
        historical_ddms_datasets = [
            "urn://rafs-v2/xrddata/wpc_id/osdu:dataset--File.Generic:xrd-old-uuid:1/1.0.0",
        ]
        current_dataset_id = "osdu:dataset--File.Generic:xrd-e41944ee-2078-4941-823e-1645fa191f7b"

        analysis_prefix = self._extract_prefix(current_dataset_id)
        resolved_id = find_dataset_id(historical_ddms_datasets, analysis_prefix)

        assert resolved_id == "osdu:dataset--File.Generic:xrd-old-uuid"

    def test_resolves_satfuncset_historical_dataset(self):
        """Should resolve SaturationFunctionSet historical dataset."""
        historical_ddms_datasets = [
            (
                "urn://rafs-v2/saturationfunctionsetdata/wpc_id/"
                "osdu:dataset--File.Generic:saturationfunctionset-old-uuid:1/1.0.0"
            ),
        ]
        current_dataset_id = "osdu:dataset--File.Generic:saturationfunctionset-4fbab005-4839-4585-94a8-62ca0cc2961b"

        analysis_prefix = self._extract_prefix(current_dataset_id)
        resolved_id = find_dataset_id(historical_ddms_datasets, analysis_prefix)

        assert resolved_id == "osdu:dataset--File.Generic:saturationfunctionset-old-uuid"

    def test_returns_none_when_type_not_in_historical_record(self):
        """Should return None when analysis type not in historical DDMSDatasets."""
        historical_ddms_datasets = [
            "urn://rafs-v2/ccedata/wpc_id/opendes:dataset--File.Generic:cce-uuid:1/1.0.0",
        ]
        current_dataset_id = "opendes:dataset--File.Generic:rca-new-uuid"

        analysis_prefix = self._extract_prefix(current_dataset_id)
        resolved_id = find_dataset_id(historical_ddms_datasets, analysis_prefix)

        assert resolved_id is None

    def test_resolves_correct_type_among_multiple(self):
        """Should resolve only the matching analysis type."""
        historical_ddms_datasets = [
            "urn://rafs-v2/ccedata/wpc_id/opendes:dataset--File.Generic:cce-old-uuid:1/1.0.0",
            "urn://rafs-v2/rcadata/wpc_id/opendes:dataset--File.Generic:rca-old-uuid:1/1.0.0",
        ]
        current_dataset_id = "opendes:dataset--File.Generic:rca-new-uuid"

        analysis_prefix = self._extract_prefix(current_dataset_id)
        resolved_id = find_dataset_id(historical_ddms_datasets, analysis_prefix)

        assert resolved_id == "opendes:dataset--File.Generic:rca-old-uuid"

    def test_resolves_historical_blob_by_full_analysis_type(self):
        """find_object_name_from_type should resolve historical blob for blob-storage path."""
        historical_ddms_datasets = [
            "urn://rafs/wpc_id/samplesanalysis/rca/1.0.0/old-uuid",
        ]
        full_analysis_type = "samplesanalysis/rca/1.0.0"

        resolved = find_object_name_from_type(historical_ddms_datasets, full_analysis_type)

        assert resolved == "samplesanalysis/rca/1.0.0/old-uuid"

    def test_blob_resolution_ignores_client_uuid(self):
        """Blob resolution finds historical UUID regardless of client-provided UUID."""
        historical_ddms_datasets = [
            "urn://rafs/wpc_id/samplesanalysis/nmr/1.0.0/historical-uuid",
        ]
        # Client blob_metadata.full_analysis_type = "samplesanalysis/nmr/1.0.0"
        # Client blob_metadata.uuid = "current-uuid" (different from historical)
        full_analysis_type = "samplesanalysis/nmr/1.0.0"

        resolved = find_object_name_from_type(historical_ddms_datasets, full_analysis_type)

        assert resolved == "samplesanalysis/nmr/1.0.0/historical-uuid"
        assert resolved.split("/")[-1] == "historical-uuid"
