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

from typing import Any, Dict, Optional

from fastapi import HTTPException
from starlette import status


class BadRequestException(HTTPException):
    def __init__(
        self,
        detail: Any = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail, headers=headers)


class InvalidBodyException(BadRequestException):
    pass


class InvalidHeaderException(BadRequestException):
    pass


class InvalidJSONException(InvalidBodyException):
    pass


class InvalidDatasetException(InvalidBodyException):
    pass


class UnprocessableContentException(HTTPException):
    def __init__(
        self,
        detail: Any = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail, headers=headers)


class RecordValidationException(UnprocessableContentException):
    pass


class DataValidationException(UnprocessableContentException):
    def __init__(
        self,
        errors: dict,
        detail: Any = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(detail=detail, headers=headers)
        self.errors = errors


class OsduApiException(HTTPException):
    pass


class NotFoundException(HTTPException):
    def __init__(
        self,
        detail: Any = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail, headers=headers)


class NotAcceptableException(HTTPException):
    def __init__(
        self,
        detail: Any = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail=detail, headers=headers)


class ServiceUnavailableException(HTTPException):
    def __init__(
        self,
        detail: Any = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail, headers=headers)
