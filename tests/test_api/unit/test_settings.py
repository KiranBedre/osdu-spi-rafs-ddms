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

"""Unit tests for settings loading across dev/test/prod environments."""

import pytest

from app.core.config import get_app_settings
from app.core.settings.base import AppEnvTypes
from app.core.settings.development import DevAppSettings
from app.core.settings.production import ProdAppSettings
from app.core.settings.test import TestAppSettings as SettingsTestEnv


def test_dev_app_settings_overrides():
    settings = DevAppSettings()
    assert settings.debug is True
    assert settings.app_name == "Dev Rock and Sample Fluid DDMS"


def test_test_app_settings_overrides():
    settings = SettingsTestEnv()
    assert settings.debug is True
    assert settings.local_dev_mode is True
    assert settings.enable_gc_collect is False


def test_prod_app_settings_extra_ignore_survives_subclass_config():
    """Issue #768 lead feedback: ProdAppSettings sets model_config with only
    env_file, not repeating extra="ignore" from BaseAppSettings. Pydantic v2
    merges model_config across the MRO, so the override must not drop it.
    """
    assert ProdAppSettings.model_config.get("extra") == "ignore"


def test_prod_app_settings_ignores_unknown_env_vars(monkeypatch):
    monkeypatch.setenv("SOME_UNRELATED_ENV_VAR_FOR_TEST_768", "anything")

    # Must not raise despite the unknown var being present in the environment.
    ProdAppSettings()


@pytest.mark.parametrize(
    "app_env,expected_settings_cls",
    [
        (AppEnvTypes.dev, DevAppSettings),
        (AppEnvTypes.test, SettingsTestEnv),
        (AppEnvTypes.prod, ProdAppSettings),
    ],
)
def test_get_app_settings_selects_class_for_app_env(monkeypatch, app_env, expected_settings_cls):
    monkeypatch.setenv("APP_ENV", app_env.value)
    get_app_settings.cache_clear()
    try:
        settings = get_app_settings()
        assert isinstance(settings, expected_settings_cls)
    finally:
        get_app_settings.cache_clear()
