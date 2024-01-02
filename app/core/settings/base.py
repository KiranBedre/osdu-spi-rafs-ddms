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
from typing import Literal

from pydantic import BaseSettings


class AppEnvTypes(Enum):
    prod: str = "prod"
    dev: str = "dev"
    test: str = "test"


class BaseAppSettings(BaseSettings):
    app_env: AppEnvTypes = AppEnvTypes.prod

    commit_id: str = None

    commit_message: str = None

    commit_branch: str = None

    build_date: str = None

    cloud_provider: Literal["", "azure", "gcp", "aws", "anthos", "ibm"] = ""

    schema_authority: str = "osdu"

    custom_schema_authority: str = "rafsddms"

    request_timeout: float = 15.0  # request timeout in seconds

    release_version: str = None  # Not the same as version (api version)

    enable_api_v1: bool = False

    class Config:
        env_file = ".env"
