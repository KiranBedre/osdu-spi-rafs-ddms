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

import logging

from app.core.settings.app import AppSettings


class TestAppSettings(AppSettings):
    debug: bool = True
    app_name: str = "Test Rock and Sample Fluid DDMS"
    logging_level: int = logging.DEBUG
    service_host_search: str = "http://test-url"
    service_host_storage: str = "http://test-url"
    service_host_dataset: str = "http://test-url"
    enable_api_v1: bool = True
