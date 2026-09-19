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

import importlib
import warnings

from starlette import status
from starlette.exceptions import StarletteDeprecationWarning

import app.core.http_status as http_status_module


def test_http_422_unprocessable_uses_current_starlette_constant():
    importlib.reload(http_status_module)
    assert http_status_module.HTTP_422_UNPROCESSABLE == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_http_422_unprocessable_falls_back_when_starlette_lacks_constant():
    """Issue #768 lead feedback: an AttributeError at import time on a Starlette
    build predating HTTP_422_UNPROCESSABLE_CONTENT must not happen. The module
    must fall back to HTTP_422_UNPROCESSABLE_ENTITY instead of crashing.
    """
    original = status.HTTP_422_UNPROCESSABLE_CONTENT
    del status.HTTP_422_UNPROCESSABLE_CONTENT
    try:
        with warnings.catch_warnings():
            # HTTP_422_UNPROCESSABLE_ENTITY is itself deprecated in starlette;
            # the module's own fallback branch reads it during this reload,
            # which is the exact behavior this test asserts.
            warnings.simplefilter("ignore", StarletteDeprecationWarning)
            importlib.reload(http_status_module)
            fallback_value = status.HTTP_422_UNPROCESSABLE_ENTITY
        assert http_status_module.HTTP_422_UNPROCESSABLE == fallback_value
    finally:
        status.HTTP_422_UNPROCESSABLE_CONTENT = original
        importlib.reload(http_status_module)
