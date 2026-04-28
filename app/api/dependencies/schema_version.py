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
from typing import Final

from starlette.responses import Response

from app.exceptions import exceptions

SUPPORTED_MIME_TYPES: Final[tuple] = ("application/json", "application/x-parquet", "*/*")

_DEPRECATED_PARAM_MSG = (
    "Specifying schema version via the Accept header is deprecated. Use ?content_schema_version= instead."
)
_ACCEPT_VERSION_SUNSET = "Sun, 31 May 2026 00:00:00 GMT"  # M27 end of support

_VERSION_REGEX = r"^\d+\.\d+(?:\.\d+)?$"


def validate_version_format(version: str, source: str) -> None:
    if not re.match(_VERSION_REGEX, version):
        reason = "Invalid version format in {0}: '{1}'. Expected format: X.Y.Z (e.g. 1.0.0)".format(
            source,
            version,
        )
        raise exceptions.NotAcceptableException(detail=reason)


def parse_version_from_accept_header(accept_header: str) -> str:
    parts = [part.strip() for part in accept_header.lower().split(";")]
    mime_type = parts[0]

    if mime_type not in SUPPORTED_MIME_TYPES:
        error_title = "Not Acceptable."
        error_details = " ".join(
            [
                f"The requested media type '{mime_type}' is not supported.",
                f"Supported types are: {SUPPORTED_MIME_TYPES}.",
            ],
        )
        raise exceptions.NotAcceptableException(detail=f"{error_title} {error_details}")

    version_match = re.search(r"version=(\d+\.\d+(?:\.\d+)?)", accept_header.lower().strip())

    if not version_match:
        error_title = "No schema version specified or invalid schema format."
        example_detail = "Example: --header 'Accept: */*;version=1.0.0'"
        error_details = f"Check if the schema version is specified in the 'Accept' header. {example_detail}"
        raise exceptions.NotAcceptableException(detail=f"{error_title} {error_details}")

    return version_match.group(1)


def set_deprecation_headers(response: Response) -> None:
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = _ACCEPT_VERSION_SUNSET
    response.headers["X-Deprecation-Notice"] = _DEPRECATED_PARAM_MSG
