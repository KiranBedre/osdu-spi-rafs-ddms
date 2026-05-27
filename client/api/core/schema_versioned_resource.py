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

from typing import Optional

from client.api.core.api_source import APIResource
from tests.integration.config import SchemaVersions


class SchemaVersionedAPIResource(APIResource):
    """API resource that supports schema versioning via query parameter."""

    SCHEMA_VERSION_PARAM: str = "content_schema_version"

    def _merge_params(self, kwargs: dict, schema_version: Optional[str] = SchemaVersions.DEFAULT) -> dict:
        """Build final request params with schema version default.

        :param kwargs: Request kwargs (may contain a ``params`` dict)
        :param schema_version: Schema version to inject; ``None`` to skip
        :return: ``kwargs`` with merged ``params``
        """
        defaults = {}
        if schema_version is not None:
            defaults[self.SCHEMA_VERSION_PARAM] = schema_version

        kwargs["params"] = {**defaults, **(kwargs.get("params") or {})}
        return kwargs