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

import pytest

from app.api.dependencies.validation import validate_kind
from app.exceptions.exceptions import RecordValidationException
from app.models.domain.osdu.base import (
    MASTER_DATA_KIND_BASES,
    SAMPLE_KIND_BASE,
    SAMPLESANALYSIS_KIND_BASE,
)

VALID_KIND_BASES = [SAMPLE_KIND_BASE]


def test_validate_kind_supported_entity_canonical_version():
    validate_kind(f"{SAMPLE_KIND_BASE}:2.0.0", VALID_KIND_BASES)


def test_validate_kind_supported_entity_new_version():
    validate_kind(f"{SAMPLE_KIND_BASE}:3.0.0", VALID_KIND_BASES)


def test_validate_kind_supported_entity_patch_version():
    validate_kind(f"{SAMPLE_KIND_BASE}:1.2.3", VALID_KIND_BASES)


def test_validate_kind_supported_entity_zero_major():
    validate_kind(f"{SAMPLE_KIND_BASE}:0.0.0", VALID_KIND_BASES)


def test_validate_kind_unsupported_entity_type_raises():
    with pytest.raises(RecordValidationException) as exc_info:
        validate_kind(f"{SAMPLE_KIND_BASE.rsplit('--', 1)[0]}--Unknown:1.0.0", VALID_KIND_BASES)
    assert "not supported in RAFS-DDMS" in str(exc_info.value.detail)


def test_validate_kind_invalid_semver_non_numeric_raises():
    with pytest.raises(RecordValidationException) as exc_info:
        validate_kind(f"{SAMPLE_KIND_BASE}:1.a.0", VALID_KIND_BASES)
    assert "invalid version" in str(exc_info.value.detail)


def test_validate_kind_invalid_semver_missing_patch_raises():
    with pytest.raises(RecordValidationException) as exc_info:
        validate_kind(f"{SAMPLE_KIND_BASE}:1.0", VALID_KIND_BASES)
    assert "invalid version" in str(exc_info.value.detail)


def test_validate_kind_invalid_semver_extra_segment_raises():
    with pytest.raises(RecordValidationException) as exc_info:
        validate_kind(f"{SAMPLE_KIND_BASE}:1.0.0.0", VALID_KIND_BASES)
    assert "invalid version" in str(exc_info.value.detail)


def test_validate_kind_invalid_semver_prerelease_raises():
    with pytest.raises(RecordValidationException) as exc_info:
        validate_kind(f"{SAMPLE_KIND_BASE}:1.0.0-alpha", VALID_KIND_BASES)
    assert "invalid version" in str(exc_info.value.detail)


def test_validate_kind_malformed_too_few_parts_raises():
    with pytest.raises(RecordValidationException) as exc_info:
        validate_kind("malformed-kind", VALID_KIND_BASES)
    assert "not supported in RAFS-DDMS" in str(exc_info.value.detail)


def test_validate_kind_wrong_authority_raises():
    wrong_authority_kind = f"wrongauth:wks:master-data--Sample:1.0.0"
    with pytest.raises(RecordValidationException) as exc_info:
        validate_kind(wrong_authority_kind, VALID_KIND_BASES)
    assert "not supported in RAFS-DDMS" in str(exc_info.value.detail)


@pytest.mark.parametrize("kind_base", list(MASTER_DATA_KIND_BASES))
def test_validate_kind_all_master_data_bases_accepted(kind_base):
    validate_kind(f"{kind_base}:1.0.0", list(MASTER_DATA_KIND_BASES))


def test_validate_kind_samplesanalysis_accepted():
    validate_kind(f"{SAMPLESANALYSIS_KIND_BASE}:2.5.1", [SAMPLESANALYSIS_KIND_BASE])
