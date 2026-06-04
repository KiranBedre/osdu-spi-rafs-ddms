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

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.exceptions.exceptions import UnsupportedMediaTypeException
from app.models.schemas.errors import UnsupportedMediaTypeResponse


async def unsupported_media_type_error_handler(  # noqa: ASYNC124
    _: Request,
    exc: UnsupportedMediaTypeException,
) -> JSONResponse:
    return JSONResponse(  # noqa: ASYNC910
        UnsupportedMediaTypeResponse(reason=exc.detail).dict(),
        status_code=exc.status_code,
    )
