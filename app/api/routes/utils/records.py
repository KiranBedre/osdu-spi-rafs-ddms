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

from typing import List, NamedTuple, Optional, Tuple

from loguru import logger

from app.exceptions.exceptions import UnprocessableContentException


class RecordKeys(NamedTuple):
    MIMETYPE_ID = "EncodingFormatTypeID"
    FILE_NAME = "Name"
    FILE_SOURCE_INFO = "FileSourceInfo"
    DATASET_PROPERTIES = "DatasetProperties"
    RESOURCE_ID = "ResourceID"


ID_PART_INDEX = 2
ENTITY_TYPE_INDEX = 2
VERSION_SPLIT_INDEX = 3
VERSION_SPLIT_INDEX_COLON_IN_ID = -1
SCHEMA_VERSION_INDEX = -1
DATASET_ID_INDEX = -2
FULLID_ID_INDEX = 0
FULLID_VERSION_INDEX = 1


def get_id_version(full_record_id: str) -> Tuple[str, Optional[int]]:
    """Separately get id and version part from record id.

    :param full_record_id: full record id
    :type full_record_id: str
    :return: tuple of id and version
    :rtype: Tuple[str, Optional[str]]
    """
    splitted_id = full_record_id.split(":")
    if len(splitted_id) > VERSION_SPLIT_INDEX:  # this means that there is a ":" in id
        record_id, version = (
            ":".join(splitted_id[:VERSION_SPLIT_INDEX_COLON_IN_ID]),
            ":".join(splitted_id[VERSION_SPLIT_INDEX_COLON_IN_ID:]),
        )  # noqa: WPS221
    else:
        record_id, version = (
            ":".join(splitted_id[:VERSION_SPLIT_INDEX]),
            ":".join(splitted_id[VERSION_SPLIT_INDEX:]),
        )  # noqa: WPS221
    try:
        if version:
            version = int(version)
        else:
            version = None
    except ValueError:
        raise UnprocessableContentException(detail=f"Record id version '{version}' should be numeric")

    return record_id, version


def get_id(full_record_id: str) -> str:
    """Get id from record id.

    :param full_record_id: full record id
    :type full_record_id: str
    :return: id without version
    :rtype: str
    """
    record_id, _ = get_id_version(full_record_id)
    return record_id


def get_id_part(full_record_id: str) -> str:
    """Get id part from record id.

    :param full_record_id: full record id
    :type full_record_id: str
    :return: id part
    :rtype: str
    """
    id_parts = get_id(full_record_id).split(":")
    return id_parts[ID_PART_INDEX]


def find_dataset_id(ddms_datasets: List[str], prefix: str) -> Optional[str]:
    """Find dataset id.

    :param ddms_datasets: ddms datasets
    :type ddms_datasets: List[str]
    :param prefix: prefix
    :type prefix: str
    :return: dataset id
    :rtype: Optional[str]
    """
    for ddms_dataset in ddms_datasets:
        dataset_id = ddms_dataset.split("/")[DATASET_ID_INDEX]
        try:
            if dataset_id and dataset_id.split(":")[ENTITY_TYPE_INDEX].startswith(prefix):  # noqa: WPS221
                return ":".join(dataset_id.split(":")[:VERSION_SPLIT_INDEX])  # noqa: WPS221
        except IndexError:
            logger.error(f"The dataset id {dataset_id} is invalid")


def update_dataset_id(ddms_datasets: List[str], ddms_urn: str, prefix: str) -> List[str]:
    """Update dataset id.

    :param ddms_datasets: ddms datasets
    :type ddms_datasets: List[str]
    :param ddms_urn: ddms urn
    :type ddms_urn: str
    :param prefix: prefix
    :type prefix: str
    :return: updated ddms datasets
    :rtype: List[str]
    """
    for index, ddms_dataset in enumerate(ddms_datasets):
        dataset_id = ddms_dataset.split("/")[DATASET_ID_INDEX]
        if dataset_id and dataset_id.split(":")[ENTITY_TYPE_INDEX].startswith(prefix):  # noqa: WPS221
            ddms_datasets[index] = ddms_urn
            return ddms_datasets


def generate_dataset_urn(
    ddms_id: str,
    api_version: str,
    entity_type: str,
    wpc_id: str,
    dataset_id: str,
    content_schema_version: str,
) -> str:
    """Generate dataset urn.

    :param ddms_id: ddms is
    :type ddms_id: str
    :param api_version: api version
    :type api_version: str
    :param entity_type: entity type
    :type entity_type: str
    :param wpc_id: wpc id
    :type wpc_id: str
    :param dataset_id: dataset id
    :type dataset_id: str
    :param content_schema_version: schema version
    :type content_schema_version: str
    :return: dataset urn
    :rtype: str
    """
    return f"urn://{ddms_id}-{api_version}/{entity_type}/{wpc_id}/{dataset_id}/{content_schema_version}"


def dataset_id_exist(ddms_datasets: List[str], dataset_id: str) -> bool:
    """Checks if given dataset id exist in ddms_datasets list.

    :param ddms_datasets: ddms datasets list
    :type ddms_datasets: List[str]
    :param dataset_id: dataset id
    :type dataset_id: str
    :return: True if dataset exist in list
    :rtype: bool
    """
    for ddms_dataset in ddms_datasets:
        full_dataset_id = ddms_dataset.split("/")[DATASET_ID_INDEX]
        ddms_dataset_id, _ = get_id_version(full_dataset_id)
        if dataset_id == ddms_dataset_id:
            return True
    return False


def find_schema_versions_for_dataset_id(ddms_datasets: List[str], dataset_id: str) -> set:
    """Find schema versions for dataset id.

    :param ddms_datasets: ddms datasets list
    :type ddms_datasets: List[str]
    :param dataset_id: dataset id
    :type dataset_id: str
    :return: set of schema versions
    :rtype: set
    """
    schema_versions = []
    for ddms_dataset in ddms_datasets:
        urn_parts = ddms_dataset.split("/")
        full_dataset_id = urn_parts[DATASET_ID_INDEX]
        ddms_dataset_id, _ = get_id_version(full_dataset_id)
        if dataset_id == ddms_dataset_id:
            schema_versions.append(urn_parts[SCHEMA_VERSION_INDEX])
    return set(schema_versions)


def parse_kind(kind: str) -> dict:
    """Returns a dictionary of the kind parts.

    :param kind: an OSDU record kind
    :type kind: str
    :return: a dictionary with the named parts of the kind
    :rtype: dict
    """
    kind_parts = kind.split(":")
    if len(kind_parts) != 4:
        raise ValueError(f"Malformed kind: {kind}. Kind should be of the form `authority:source:entity_type:version`")
    authority_index = 0
    source_index = 1
    entity_type_index = 2
    version_index = 3
    return {
        "authority": kind_parts[authority_index],
        "source": kind_parts[source_index],
        "entity_type": kind_parts[entity_type_index],
        "version": kind_parts[version_index],
    }


def get_info_from_urn(urn: str) -> dict:
    """Obtain information from the ddms_urn.

    :param urn: the ddms urn
    :type urn: str
    :raises ValueError: if the urn is malformed
    :return: a dictionary with proper information
    :rtype: dict
    """
    urn_start = 6  # trims out 'urn://'
    urn_parts = urn[urn_start:].split("/")

    urn_sections = 5
    if len(urn_parts) != urn_sections:
        raise ValueError(
            f"Malformed URN: {urn}. Should be of the form 'urn://rafs_version/entity_type/wpc_id/dataset_id/content_schema_version'",  # noqa: E501
        )

    rafs_version_index = 0
    test_type_index = 1
    samples_analysis_index = 2
    dataset_index = 3
    schema_version_index = 4

    dataset_id = urn_parts[dataset_index]
    # dataset api does not allow retrieve dataset with version
    dataset_id = get_id(dataset_id)
    return {
        "rafs_version": urn_parts[rafs_version_index],
        "test_type": urn_parts[test_type_index],
        "samples_analysis_id": urn_parts[samples_analysis_index],
        "dataset_id": dataset_id,
        "content_schema_version": urn_parts[schema_version_index],
    }
