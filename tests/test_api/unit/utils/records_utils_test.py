#  Copyright 2023 ExxonMobil Technology and Engineering Company
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
from starlette import status

from app.api.routes.utils.records import (
    find_object_name_from_type,
    find_object_name_index,
    find_schema_versions_for_object_name,
    generate_blob_urn,
    get_family_type_from_url,
    get_id_version,
)
from app.exceptions.exceptions import UnprocessableContentException

EXPECTED_RECORD_ID = "partition:entity_type:record_id"


def test_get_id_version_with_full_id_():
    record_id, version = get_id_version("partition:entity_type:record_id:1234")

    assert record_id == EXPECTED_RECORD_ID
    assert version == 1234


def test_get_id_version_with_full_id_raises():
    with pytest.raises(UnprocessableContentException) as exc:
        get_id_version("partition:entity_type:record_id:1234s")

    assert exc.value.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert exc.value.detail == "Record id version '1234s' should be numeric"


def test_get_id_version_ending_with_colon():
    record_id, version = get_id_version("partition:entity_type:record_id:")

    assert record_id == EXPECTED_RECORD_ID
    assert version == None


def test_get_id_version_ending_without_colon():
    record_id, version = get_id_version("partition:entity_type:record_id")

    assert record_id == EXPECTED_RECORD_ID
    assert version == None


@pytest.mark.parametrize(
    "url, expected_family",
    [
        ("/api/rafs-ddms/v2/samplesanalysis/wpc_id/", "samplesanalysis"),
        ("/api/rafs-ddms/v2/pvt/wpc_id", "pvt"),
        ("/api/rafs-ddms/dev/devfamily/wpc_id", "devfamily"),
    ],
)
def test_get_family_type_from_url(url, expected_family):
    result = get_family_type_from_url(url)
    assert result == expected_family


@pytest.mark.parametrize(
    "ddms_id, wpc_id, object_name, expected_urn",
    [
        ("rafs", "wpc_id", "samplesanalysis/nmr/1.0.0/1234", "urn://rafs/wpc_id/samplesanalysis/nmr/1.0.0/1234"),
        ("rafs", "wpc_id", "pvt/eos/1.0.1/1234", "urn://rafs/wpc_id/pvt/eos/1.0.1/1234"),
    ],
)
def test_generate_blob_urn(ddms_id, wpc_id, object_name, expected_urn):
    result = generate_blob_urn(ddms_id, wpc_id, object_name)
    assert result == expected_urn


@pytest.mark.parametrize(
    "ddms_datasets, object_name, expected_blob_id",
    [
        (["urn://rafs/wpc_id/samplesanalysis/nmr/1.0.0/1234"], "samplesanalysis/nmr/1.0.0/1234", 0),
        (
            [
                "urn://rafs/wpc_id/samplesanalysis/nmr/1.0.0/4321",
                "urn://rafs/wpc_id/samplesanalysis/nmr/1.0.0/1234",
            ], "samplesanalysis/nmr/1.0.0/1234", 1,
        ),
        (["urn://rafs/wpc_id/samplesanalysis/nmr/1.0.0/1234"], "object_name", None),
        ([], "object", None),
    ],
)
def test_find_object_name_index(ddms_datasets, object_name, expected_blob_id):
    result = find_object_name_index(ddms_datasets, object_name)
    assert result == expected_blob_id


@pytest.mark.parametrize(
    "ddms_datasets, blob_id, expected_versions",
    [
        (
            ["urn://rafs/wpc_id/samplesanalysis/nmr/1.0.0/1234"],
            "samplesanalysis/nmr/1.0.0/1234",
            {"1.0.0"},
        ),
        (
            ["urn://rafs/wpc_id/samplesanalysis/cvd/2.0.0/1234"],
            "samplesanalysis/cvd/2.0.0/1234",
            {"2.0.0"},
        ),
        (["urn://rafs/wpc_id/samplesanalysis/cvd/2.0.0/1234"], "samplesanalysis/nmr/1.0.0/1234", set()),
    ],
)
def test_find_schema_versions_for_object_name(ddms_datasets, blob_id, expected_versions):
    result = find_schema_versions_for_object_name(ddms_datasets, blob_id)
    assert result == expected_versions


@pytest.mark.parametrize(
    "ddms_datasets, full_analysis_type, expected",
    [
        (
            [
                "urn://rafs/wpc1/family/type/1.0/uuid1",
            ],
            "family/type/1.0",
            "family/type/1.0/uuid1",
        ),
        (
            [
                "urn://rafs/wpc1/family/type/1.0/uuid1",
                "urn://rafs/wpc1/family/type/2.0/uuid2",
            ],
            "family/type/2.0",
            "family/type/2.0/uuid2",
        ),
        (
            [
                "urn://rafs/wpc1/family/type/1.0/uuid1",
                "urn://rafs/wpc2/family/type/1.0/uuid2",
            ],
            "family/type/3.0",
            None,
        ),
        (
            [],
            "family/type/1.0",
            None,
        ),
        (
            ["urn://rafs/wpc1/family/other/1.0/uuid1"],
            "family/type/1.0",
            None,
        ),
    ],
)
def test_find_object_name_from_type(ddms_datasets, full_analysis_type, expected):
    assert find_object_name_from_type(ddms_datasets, full_analysis_type) == expected
