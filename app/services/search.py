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

from typing import List, Optional

from starlette import status

from app.core.settings.app import AppSettings
from app.models.schemas.user import User
from app.services.base import ISearchService
from app.services.error_handlers import handle_core_services_http_status_error
from app.services.osdu_clients.search_client import SearchServiceApiClient

QUERY_LIMIT = 1000


class SearchService(ISearchService):

    def __init__(
        self,
        data_partition_id: str,
        settings: AppSettings,
        user: User,
        extra_headers: dict,
    ) -> None:
        self.search_client = SearchServiceApiClient(
            settings.service_host_search,
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
        detail="Failed to query records using SearchService.",
    )
    async def find_records(
        self,
        kind: Optional[str] = "*:*:*:*",
        query: Optional[str] = "*",
        limit: Optional[int] = QUERY_LIMIT,
        **kwargs,
    ) -> List[dict]:
        """Find records.

        :param kind: kinf of record, defaults to "*:*:*:*"
        :type kind: str, optional
        :param query: query, defaults to "*"
        :type query: str, optional
        :param limit: limit, defaults to None
        :type limit: int, optional
        :return: records
        :rtype: List[dict]
        """
        return await self.search_client.query_with_cursor({
            **{
                "kind": kind,
                "query": query,
                "limit": limit,
            }, **kwargs,
        })
