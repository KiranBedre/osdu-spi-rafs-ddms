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


from app.api.routes.utils.mimetypes import get_mime_type
from app.resources.mime_types import SupportedMimeTypes


def test_get_mime_type_prefers_encoding_format_type_id():
    dataset_record = {
        "id": "dp1:dataset--File.Generic:test-id",
        "data": {
            "EncodingFormatTypeID": "dp1:reference-data--EncodingFormatType:text/csv:",
            "Name": "report.xlsx",
        },
    }

    mime_type = get_mime_type(dataset_record)

    assert mime_type == "text/csv"


def test_get_mime_type_guesses_from_file_name():
    dataset_record = {
        "id": "dp1:dataset--File.Generic:test-id",
        "data": {
            "Name": "report.xlsx",
        },
    }

    mime_type = get_mime_type(dataset_record)

    assert mime_type == SupportedMimeTypes.XLSX.mime_type


def test_get_mime_type_falls_back_to_bin_when_unknown():
    dataset_record = {
        "id": "dp1:dataset--File.Generic:test-id",
        "data": {
            "Name": "report.unknown_extension",
        },
    }

    mime_type = get_mime_type(dataset_record)

    assert mime_type == SupportedMimeTypes.BIN.mime_type
