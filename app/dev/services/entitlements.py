#  Copyright 2024 ExxonMobil Technology and Engineering Company
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

from starlette import status

from app.core.settings.app import AppSettings
from app.dev.services.osdu_clients.entitlements_client import (
    EntitlementsServiceApiClient,
)
from app.models.schemas.user import User
from app.services.error_handlers import handle_core_services_http_status_error


class EntitlementsService:

    def __init__(
        self,
        data_partition_id: str,
        settings: AppSettings,
        user: User,
        extra_headers: dict,
    ) -> None:
        self.entitlements_client = EntitlementsServiceApiClient(
            settings.service_host_entitlements,
            data_partition_id=data_partition_id,
            bearer_token=user.access_token,
            extra_headers=extra_headers,
        )

    @handle_core_services_http_status_error(
        expected_codes=[
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ],
        detail="Failed to get groups using EntitlementsService.",
    )
    async def get_groups(self) -> dict:
        """Get groups.

        :return: dictionary with groups information
        :rtype: dict
        """
        return await self.entitlements_client.get_groups()

    @handle_core_services_http_status_error(
        expected_codes=[
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ],
        detail="Failed to get data groups using EntitlementsService.",
    )
    async def get_data_groups(self) -> list:
        """Get data groups.

        :return: a set with data groups
        :rtype: list
        """
        groups_response = await self.entitlements_client.get_groups()
        groups = groups_response.get("groups", [])
        return [group.get("email") for group in groups if group.get("name").startswith("data")]
