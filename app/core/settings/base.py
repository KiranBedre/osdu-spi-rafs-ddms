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

from enum import Enum
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvTypes(Enum):
    prod: str = "prod"
    dev: str = "dev"
    test: str = "test"


class BaseAppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: AppEnvTypes = AppEnvTypes.prod

    commit_id: Optional[str] = None

    commit_message: Optional[str] = None

    commit_branch: Optional[str] = None

    build_date: Optional[str] = None

    cloud_provider: Literal["", "azure", "gc", "aws", "anthos", "ibm"] = ""

    schema_authority: str = "osdu"

    custom_schema_authority: str = "rafsddms"

    request_timeout: float = 15.0  # request timeout in seconds

    release_version: Optional[str] = None  # Not the same as version (api version)

    otel_exporter_otlp_endpoint: Optional[str] = None

    otel_service_name: str = "rafs-ddms"
