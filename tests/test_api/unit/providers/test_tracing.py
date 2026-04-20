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

from unittest.mock import MagicMock

from opentelemetry import trace

from app.providers.helpers.tracing import initialize_tracer


def test_initialize_tracer_noop_when_no_endpoint():
    """initialize_tracer with no endpoint must not change the active tracer provider."""
    settings = MagicMock()
    settings.otel_exporter_otlp_endpoint = None

    provider_before = trace.get_tracer_provider()
    initialize_tracer(settings)
    provider_after = trace.get_tracer_provider()

    assert provider_after is provider_before
