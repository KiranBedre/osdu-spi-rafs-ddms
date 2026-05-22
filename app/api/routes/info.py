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

from fastapi import APIRouter

from app.core.config import get_app_settings
from app.models.schemas.info import InfoResponse

router = APIRouter()
settings = get_app_settings()


@router.get("/info", response_model=InfoResponse, include_in_schema=True)
def get_info() -> InfoResponse:
    """Get application info.

    :return: application info
    :rtype: InfoResponse
    """
    return InfoResponse.construct(
        name=settings.app_name,
        app_version=settings.app_version,
        build_time=settings.build_date,
        branch=settings.commit_branch,
        commit_id=settings.commit_id,
        commit_message=settings.commit_message,
        release_version=settings.release_version,
    )
