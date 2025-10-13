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

from dataclasses import dataclass


@dataclass
class MimeType(object):
    mime_type: str
    file_extension: str
    alternative_types: list = None

    def is_match(self, mime_type):
        return mime_type == self.mime_type or mime_type in self.alternative_types

    def is_extension_match(self, extension):
        return extension == self.file_extension


class SupportedMimeTypes(object):
    PARQUET = MimeType("application/x-parquet", ".parquet", ["application/parquet"])
    JSON = MimeType("application/json", ".json")
    ZIP = MimeType("application/zip", ".zip", ["application/x-zip-compressed"])
    BIN = MimeType("application/octet-stream", ".bin")
    XLSX = MimeType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx")

    mime_types = [
        PARQUET,
        JSON,
        ZIP,
        BIN,
        XLSX,
    ]

    @classmethod
    def find_by_extension(cls, extension):
        for mime_type in cls.mime_types:
            if mime_type.is_extension_match(extension):
                return mime_type
        return None

    @classmethod
    def find_by_mime_type(cls, mime_type):
        for mime_type_obj in cls.mime_types:
            if mime_type_obj.is_match(mime_type):
                return mime_type_obj
        return None
