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

from typing import Union

from pydantic import BaseSettings
from pydantic.types import conint


class RedisCacheConfig(BaseSettings):
    """Config with settings for redis instance."""
    redis_hostname: str = "localhost"

    redis_password: str = None

    redis_port: int = 6380

    redis_database: Union[str, int] = 0

    redis_ssl: bool = True

    redis_index_database: conint(gt=-1, lt=1) = 0  # only at 'db = 0' can be created the index

    class Config:
        env_file = ".env"
