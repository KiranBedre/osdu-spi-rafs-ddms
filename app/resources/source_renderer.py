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
import zipfile
from io import BytesIO
from typing import List, NamedTuple

from fastapi import Response, status
from fastapi.responses import JSONResponse, StreamingResponse

from app.resources import common_headers
from app.resources.mime_types import SupportedMimeTypes


class DatasetSourceFile(NamedTuple):
    dataset_id: str
    mime_type: str
    content: bytes  # noqa: WPS110


class FileSourceRenderer(object):

    def __init__(self, data_source_files: List[DatasetSourceFile]) -> None:
        self.data_source_files = data_source_files

    async def render_source_data(self) -> Response:
        if len(self.data_source_files) > 1:
            response = self._create_zip_response(self.data_source_files)
        elif len(self.data_source_files) == 1:
            response = self._create_single_file_response(
                self.data_source_files[0],
            )
        else:
            response = JSONResponse(
                {"message": "entity has no source data"},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return response

    def _create_zip_response(self, data_source_files: List[DatasetSourceFile]) -> Response:
        response_file = BytesIO()
        with zipfile.ZipFile(
            response_file,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
        ) as zp:
            for dsf in data_source_files:
                guessed_extension = mimetypes.guess_extension(dsf.mime_type)
                zp.writestr(
                    f"{dsf.dataset_id}{guessed_extension}",
                    dsf.content,
                )
        extension = SupportedMimeTypes.ZIP.file_extension
        return StreamingResponse(
            iter([response_file.getvalue()]),
            media_type=SupportedMimeTypes.ZIP.mime_type,
            headers={
                f"{common_headers.CONTENT_DISPOSITION}":
                f"{common_headers.ATTACHMENT};filename=datasets{extension}",
            },
        )

    def _create_single_file_response(self, dsf: DatasetSourceFile) -> Response:
        response_file = BytesIO()
        response_file.write(dsf.content)
        extension = mimetypes.guess_extension(dsf.mime_type)

        return StreamingResponse(
            iter([response_file.getvalue()]),
            media_type=dsf.mime_type,

            headers={
                f"{common_headers.CONTENT_DISPOSITION}":
                f'{common_headers.ATTACHMENT};filename="{dsf.dataset_id}{extension}"',
            },
        )
