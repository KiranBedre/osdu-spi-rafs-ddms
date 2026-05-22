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

import mimetypes
from typing import Optional
from urllib.parse import unquote

from app.api.routes.utils.records import RecordKeys, get_id_part
from app.resources.mime_types import SupportedMimeTypes


def init_mimetypes():
    """Init mimetypes.

    Workaround since distroless image lacks some types so we need to add
    them.
    """
    mimetypes.add_type(type=SupportedMimeTypes.XLSX.mime_type, ext=SupportedMimeTypes.XLSX.file_extension)


async def get_mime_type(dataset_record: dict) -> Optional[str]:
    """Get mime type of dataset record.

    :param dataset_record: dataset record
    :type dataset_record: dict
    :return: mime type
    :rtype: str
    """
    await init_mimetypes()

    # get mime type from EncodingFormatTypeID
    mimetype_id = unquote(dataset_record["data"].get(RecordKeys.MIMETYPE_ID, ""))

    # fallback for EncodingFormatTypeID
    file_source_info = (
        dataset_record["data"]
        .get(
            RecordKeys.DATASET_PROPERTIES,
            {},
        )
        .get(RecordKeys.FILE_SOURCE_INFO, {})
    )
    mimetype_id = mimetype_id or unquote(file_source_info.get(RecordKeys.MIMETYPE_ID, ""))

    # if non of previuos work guess with file name or file id
    file_name = dataset_record["data"].get(RecordKeys.FILE_NAME, "") or file_source_info.get(RecordKeys.FILE_NAME, "")
    guessed_mime_type = mimetypes.guess_type(file_name)[0] or mimetypes.guess_type(dataset_record["id"])[0]

    return get_id_part(mimetype_id) if mimetype_id else guessed_mime_type or SupportedMimeTypes.BIN.mime_type
