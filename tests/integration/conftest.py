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

import pytest

from client.api import ApiWorker
from tests.integration.config import CONFIG
from tests.integration.data_provider import load_test_data
from tests.integration.helpers import HelperManager


def pytest_addoption(parser: pytest.Parser):
    """Register custom CLI options."""
    parser.addoption("--cloud-provider", type=str, help="OneOf [azure, aws, gc]")
    parser.addoption("--bearer-token", type=str, help="The bearer token for auth")
    parser.addoption("--ddms-base-url", type=str, help="The DDMS base URL")

    parser.addoption("--partition", type=str, help="Data partition")
    parser.addoption("--url-prefix", type=str, help="URL prefix")


def pytest_configure(config: pytest.Config):
    """Extracts configuration from environment variables."""
    CONFIG["CLOUD_PROVIDER"] = config.getoption("--cloud-provider")
    CONFIG["TOKEN"] = config.getoption("--bearer-token")
    CONFIG["DDMS_BASE_URL"] = config.getoption("--ddms-base-url")
    CONFIG["URL_PREFIX"] = config.getoption("--url-prefix")
    CONFIG["DATA_PARTITION"] = config.getoption("--partition")


@pytest.fixture(scope="session")
def api():
    """A fixture to provide api worker."""
    return ApiWorker(CONFIG["DDMS_BASE_URL"], CONFIG["URL_PREFIX"], CONFIG["DATA_PARTITION"], CONFIG["TOKEN"])


@pytest.fixture(scope="session")
def helper(api):
    """A fixture to provide helper."""
    return HelperManager(api)


@pytest.fixture(scope="session")
def tests_data():
    """A fixture to provide dataset to the rock sample analysis tests."""
    yield load_test_data
