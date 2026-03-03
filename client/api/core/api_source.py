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


class APIResource(APIClient):
    """Intermediate class for API resource methods."""

    def __init__(
        self,
        host: str,
        version: str,
        url_prefix: str,
        data_partition: str,
        token: str,
        resource_path: type,
    ) -> None:
        super().__init__(host, version, url_prefix, data_partition, token)
        self.resource_path = resource_path

    def post_record(self, body: list, raw: bool = False, **kwargs) -> Union[dict, requests.Response]:
        """
        :param body: record data
        :param raw: if True return requests.Response; otherwise return parsed JSON dict
        :param kwargs: Additional keyword arguments.
        :return: created record (dict) or Response
        """
        response = self.post(path=self.resource_path.POST, json=body, **kwargs)
        return response if raw else response.json()

    def get_record(self, record_id: str, raw: bool = False, **kwargs) -> Union[dict, requests.Response]:
        """
        :param record_id: record id
        :param raw: if True return requests.Response; otherwise return parsed JSON dict
        :param kwargs: Additional keyword arguments.
        :return: record data (dict) or Response
        """
        response = self.get(path=self.resource_path.GET.format(record_id=record_id), **kwargs)
        return response if raw else response.json()

    def get_record_versions(self, record_id: str, raw: bool = False, **kwargs) -> Union[dict, requests.Response]:
        """Get the versions of a record.

        :param record_id: The ID of the record to retrieve the versions for.
        :param raw: if True return requests.Response; otherwise return parsed JSON dict
        :param kwargs: Additional keyword arguments.
        :return: The versions of the record (dict) or Response
        """
        response = self.get(path=self.resource_path.GET_VERSIONS.format(record_id=record_id), **kwargs)
        return response if raw else response.json()

    def get_record_version(
        self,
        record_id: str,
        version: int,
        raw: bool = False,
        **kwargs,
    ) -> Union[dict, requests.Response]:
        """Get a specific version of a record.

        :param record_id: The ID of the record to retrieve.
        :param version: The version number of the record to retrieve.
        :param raw: if True return requests.Response; otherwise return parsed JSON dict
        :param kwargs: Additional keyword arguments.
        :return: Requested record version (dict) or Response
        """
        response = self.get(path=self.resource_path.GET_VERSION.format(record_id=record_id, version=version), **kwargs)
        return response if raw else response.json()

    def soft_delete_record(self, record_id: str, raw: bool = False, **kwargs) -> Union[None, requests.Response]:
        """Soft delete a record.

        :param record_id: The ID of the record to delete.
        :param raw: if True return requests.Response
        :param kwargs: Additional keyword arguments.
        :return: None or Response
        """
        response = self.delete(path=self.resource_path.DELETE.format(record_id=record_id), **kwargs)
        return response if raw else None
