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

from typing import Union

import requests

from client.api_client import APIClient


class AppInfo(APIClient):
    """Client for the /info endpoint (no API version prefix)."""

    INFO_PATH = "/info"

    def __init__(self, host: str, url_prefix: str, data_partition: str, token: str) -> None:
        super().__init__(host, "", url_prefix, data_partition, token)

    def get_info(self, raw: bool = False, **kwargs) -> Union[dict, requests.Response]:
        """Fetch application info.

        :param raw: if True return requests.Response; otherwise return parsed JSON dict
        :return: info dict or Response
        """
        response = self.get(path=self.INFO_PATH, **kwargs)
        return response if raw else response.json()
