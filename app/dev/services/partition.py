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
from app.dev.services.osdu_clients.partition_client import (
    PartitionServiceApiClient,
)
from app.models.schemas.user import User
from app.services.error_handlers import handle_core_services_http_status_error


class PartitionService:

    def __init__(
        self,
        data_partition_id: str,
        settings: AppSettings,
        user: User,
        extra_headers: dict,
    ) -> None:
        self.partition_client = PartitionServiceApiClient(
            settings.service_host_partition,
            data_partition_id=data_partition_id,
            bearer_token=user.access_token,
            extra_headers=extra_headers,
        )

    @handle_core_services_http_status_error(
        expected_codes=[
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        ],
        detail="Failed to verify partition using PartitionService.",
    )
    async def partition_exist(self, partition: str) -> bool:
        """Verifies if the given partition name exist.

        :param partition: partition name
        :type partition: str
        :return: a boolean indicating if the partiion exist
        :rtype: bool
        """
        partitions = await self.partition_client.list_partitions()
        return partition in partitions

    @handle_core_services_http_status_error(
        expected_codes=[
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        ],
        detail="Failed to get partition info using PartitionService.",
    )
    async def get_partition_info(self, partition: str) -> dict:
        """Get the partition info.

        :param partition: partition name
        :type partition: str
        :return: dict with info of the partition
        :rtype: dict
        """
        return await self.partition_client.get_partition(partition)

    @handle_core_services_http_status_error(
        expected_codes=[
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
        ],
        detail="Failed to list partitions fo using PartitionService.",
    )
    async def list_partitions_info(self) -> list:
        """List the partitions.

        :return: the list of partition names
        :rtype: list
        """
        return await self.partition_client.list_partitions()
