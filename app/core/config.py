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

from functools import lru_cache
from typing import Dict, Optional, Type

from pydantic_settings import BaseSettings

from app.core.settings.app import AppSettings
from app.core.settings.base import AppEnvTypes, BaseAppSettings
from app.core.settings.development import DevAppSettings
from app.core.settings.production import ProdAppSettings
from app.core.settings.test import TestAppSettings
from app.providers.config import get_cloud_provider_config

environments: Dict[AppEnvTypes, Type[AppSettings]] = {
    AppEnvTypes.dev: DevAppSettings,
    AppEnvTypes.prod: ProdAppSettings,
    AppEnvTypes.test: TestAppSettings,
}


@lru_cache
def get_app_settings() -> AppSettings:
    """Prepare base settings for app.

    :return: app config
    :rtype: AppSettings
    """
    app_env = BaseAppSettings().app_env
    config = environments[app_env]
    return config()


@lru_cache
def get_provider_config() -> Optional[BaseSettings]:
    """Prepare settings for provider.

    :return: provider config
    :rtype: Optional[BaseSettings]
    """
    cloud_provider = BaseAppSettings().cloud_provider
    return get_cloud_provider_config(cloud_provider)
