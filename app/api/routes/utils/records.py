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

import re
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
RECORD_TYPE_INDEX = 1
ENTITY_TYPE_INDEX = 2
VERSION_SPLIT_INDEX = 3
VERSION_SPLIT_INDEX_COLON_IN_ID = -1
SCHEMA_VERSION_INDEX = -1
DATASET_ID_INDEX = -2
FULLID_ID_INDEX = 0
FULLID_VERSION_INDEX = 1
DATASET_KIND_PREFIX = "dataset--"

# Blob id
URN_OBJECT_NAME_INDEX = -4
ANALYSIS_TYPE_INDEX = 1
VERSION_INDEX = 2


def get_id_version(full_record_id: str) -> Tuple[str, Optional[int]]:
    """Separately get id and version part from record id.

    :param full_record_id: full record id
    :type full_record_id: str
    :return: tuple of id and version
    :rtype: Tuple[str, Optional[str]]
    """
    logger.debug(f"full record id: {full_record_id}")
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
            parts = dataset_id.split(":")
            if (  # noqa: WPS221
                dataset_id
                and parts[RECORD_TYPE_INDEX].startswith(DATASET_KIND_PREFIX)
                and parts[ENTITY_TYPE_INDEX].startswith(prefix)
            ):
                return ":".join(parts[:VERSION_SPLIT_INDEX])  # noqa: WPS221
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
        try:
            parts = dataset_id.split(":")
            if (  # noqa: WPS221
                dataset_id
                and parts[RECORD_TYPE_INDEX].startswith(DATASET_KIND_PREFIX)
                and parts[ENTITY_TYPE_INDEX].startswith(prefix)
            ):
                ddms_datasets[index] = ddms_urn
                return ddms_datasets
        except IndexError:
            logger.error(f"The dataset id {dataset_id} is invalid")


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


_SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def is_valid_semver(version: str) -> bool:
    return bool(_SEMVER_PATTERN.match(version))


def get_info_from_urn(urn: str) -> dict:
    """Obtain information from the ddms_urn.

    :param urn: the ddms urn
    :type urn: str
    :return: a dictionary with proper information or None
    :rtype: dict
    """
    urn_start = 6  # trims out 'urn://'
    urn_parts = urn[urn_start:].split("/")

    urn_sections = 5

    if len(urn_parts) == urn_sections:
        rafs_version_index = 0
        test_type_index = 1
        samples_analysis_index = 2
        dataset_index = 3
        schema_version_index = 4

        dataset_id = urn_parts[dataset_index]
        # dataset api does not allow retrieve dataset with version
        dataset_id = get_id(dataset_id)
        urn_info = {
            "rafs_version": urn_parts[rafs_version_index],
            "test_type": urn_parts[test_type_index],
            "samples_analysis_id": urn_parts[samples_analysis_index],
            "dataset_id": dataset_id,
            "content_schema_version": urn_parts[schema_version_index],
        }
    else:
        valid_urn_format = "urn://rafs_version/entity_type/wpc_id/dataset_id/content_schema_version"
        logger.warning(f"Skipping this urn: {urn}. Since the right urn format is: '{valid_urn_format}'")
        urn_info = {}

    return urn_info


def get_family_type_from_url(url: str) -> str:
    logger.info("URL:")
    logger.info(url)
    analysis_family_position = 4  # api/rafs/<version>/<analysis_family>/etc.
    return url.split("/")[analysis_family_position]


def generate_blob_urn(
    ddms_id: str,
    wpc_id: str,
    object_name: str,
) -> str:
    """Generate parquet blob urn.

    :param ddms_id: ddms is
    :type ddms_id: str
    :param wpc_id: wpc id
    :type wpc_id: str
    :param object_name: blob object name
    :type object_name: str
    :return: dataset urn
    :rtype: str
    """
    return f"urn://{ddms_id}/{wpc_id}/{object_name}"


def find_object_name_index(ddms_datasets: List[str], object_name: str) -> Optional[int]:
    """Find object name index in ddms datasets.

    :param ddms_datasets: ddms datasets
    :type ddms_datasets: List[str]
    :param object_name: object name
    :type object_name: str
    :return: index of the object name or -1 if not found
    :rtype: Optional[int]
    """
    for index, ddms_dataset in enumerate(ddms_datasets):
        try:
            ddms_dataset_object_name = "/".join(ddms_dataset.split("/")[URN_OBJECT_NAME_INDEX:])
            if ddms_dataset_object_name == object_name:
                return index
        except IndexError:
            logger.error(f"The object name {ddms_dataset_object_name} is invalid")


def find_object_name_from_type(ddms_datasets: List[str], full_analysis_type: str) -> Optional[str]:
    """Find object name from type.

    :param ddms_datasets: ddms datasets
    :type ddms_datasets: List[str]
    :param full_analysis_type: analysis_family/analysis_type/version
    :type full_analysis_type: str
    :return: object name
    :rtype: Optional[str]
    """
    full_analysis_type_parts = full_analysis_type.split("/")
    for ddms_dataset in ddms_datasets:
        object_name_parts = ddms_dataset.split("/")[URN_OBJECT_NAME_INDEX:]

        if full_analysis_type_parts == object_name_parts[:-1]:
            return "/".join(object_name_parts)


def find_schema_versions_for_object_name(ddms_datasets: List[str], object_name: str) -> set:
    """Find schema versions for object name.

    :param ddms_datasets: ddms datasets list
    :type ddms_datasets: List[str]
    :param object_name: object name
    :type object name: str
    :return: set of schema versions
    :rtype: set
    """
    schema_versions = []
    for ddms_dataset in ddms_datasets:
        object_name_parts = ddms_dataset.split("/")[URN_OBJECT_NAME_INDEX:]
        ddms_datasets_object_name = "/".join(object_name_parts)
        if object_name == ddms_datasets_object_name:
            schema_versions.append(object_name_parts[VERSION_INDEX])
    return set(schema_versions)


def get_info_from_blob_urn(urn: str) -> dict:
    """Obtain blob information from the ddms_urn.

    :param urn: the ddms urn
    :type urn: str
    :return: a dictionary with proper information or None
    :rtype: dict
    """
    urn_start = 6  # trims out 'urn://'
    urn_parts = urn[urn_start:].split("/")

    urn_num_sections = 6
    if len(urn_parts) == urn_num_sections:
        rafs_version_index = 0
        wpc_id_index = 1
        analysis_family_index = 2
        analysis_type_index = 3
        schema_version_index = 4
        uuid_index = 5

        urn_info = {
            "rafs_version": urn_parts[rafs_version_index],
            "wpc_id": urn_parts[wpc_id_index],
            "analysis_family": urn_parts[analysis_family_index],
            "analysis_type": urn_parts[analysis_type_index],
            "version": urn_parts[schema_version_index],
            "uuid": urn_parts[uuid_index],
            "blob_id": "/".join(urn_parts[analysis_family_index:]),
        }
    else:
        valid_urn_format = "urn://rafs_version/wpc_id/analysis_family/analysis_type/version/uuid"
        logger.warning(f"Skipping this urn: {urn}. Since the right urn format is: '{valid_urn_format}'")
        urn_info = {}

    return urn_info
