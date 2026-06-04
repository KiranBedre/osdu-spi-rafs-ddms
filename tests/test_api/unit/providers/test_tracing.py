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

import sys
import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# ---------------------------------------------------------------------------
# Module-level stubs for project deps not available in lightweight test envs.
# In CI all deps are installed so sys.modules already has the real modules
# and setdefault is a no-op.
# ---------------------------------------------------------------------------
_CACHE_STUB = MagicMock()
_CACHE_STUB.init_cache = AsyncMock()
_CACHE_STUB.clear_cache = AsyncMock()

_PANDAS_STUB = MagicMock()
_PANDAS_STUB.init_pandas = AsyncMock()

_SETTINGS_STUB = MagicMock()
_SETTINGS_STUB.AppSettings = MagicMock

for _mod_name, _mod_stub in (
    ("fastapi_cache", MagicMock()),
    ("fastapi_cache.backends", MagicMock()),
    ("fastapi_cache.decorator", MagicMock()),
    ("pydantic_settings", MagicMock()),
    ("app.core.helpers.cache_helper", _CACHE_STUB),
    ("app.core.helpers.pandas_conf", _PANDAS_STUB),
    ("app.core.settings.app", _SETTINGS_STUB),
    ("app.core.settings.base", MagicMock()),
):
    sys.modules.setdefault(_mod_name, _mod_stub)

from app.core.events import create_start_app_handler  # noqa: E402
from app.providers.helpers.tracing import initialize_tracer, restart_otel_span_processors  # noqa: E402


# ---------------------------------------------------------------------------
# Stub BatchSpanProcessor subclass used to simulate the post-fork state where
# the export thread is dead.  Bypasses the real __init__ so no background
# thread is started, then exposes exactly the public attributes accessed by
# restart_otel_span_processors() (as they exist in opentelemetry-sdk==1.28.2).
# ---------------------------------------------------------------------------
class _FakeBatchSpanProcessor(BatchSpanProcessor):
    def __new__(cls, dead_thread):  # noqa: WPS110
        return object.__new__(cls)

    def __init__(self, dead_thread):
        self.worker_thread = dead_thread  # SDK 1.28 (0.49b2) uses public names
        self.done = False

    def worker(self):
        pass

    def shutdown(self, timeout_millis=30_000):
        """No-op shutdown — stub has no real exporter or background thread to clean up."""
        pass  # noqa: WPS420


# ---------------------------------------------------------------------------
# initialize_tracer
# ---------------------------------------------------------------------------


def test_initialize_tracer_noop_when_no_endpoint():
    """initialize_tracer with no endpoint must not change the active tracer provider."""
    settings = MagicMock()
    settings.otel_exporter_otlp_endpoint = None

    provider_before = trace.get_tracer_provider()
    initialize_tracer(settings)
    provider_after = trace.get_tracer_provider()

    assert provider_after is provider_before


def test_initialize_tracer_always_sets_provider():
    """initialize_tracer must set up a fresh TracerProvider even when one is already registered.

    Each uvicorn worker creates its own TracerProvider so the HTTP connection pool
    of OTLPSpanExporter is not shared across forked processes.  The idempotency guard
    is intentionally absent: every worker must own an independent export pipeline.
    """
    settings = MagicMock()
    settings.otel_exporter_otlp_endpoint = "http://localhost:4318"
    settings.otel_service_name = "test-service"

    existing_provider = TracerProvider()
    with patch("opentelemetry.trace.get_tracer_provider", return_value=existing_provider):
        with patch("opentelemetry.trace.set_tracer_provider") as mock_set:
            with patch("opentelemetry.instrumentation.httpx.HTTPXClientInstrumentor.instrument"):
                initialize_tracer(settings)
                mock_set.assert_called_once()
                new_provider = mock_set.call_args[0][0]
                assert new_provider is not existing_provider


def test_initialize_tracer_sets_provider_when_not_configured():
    """initialize_tracer must register a TracerProvider when none is active."""
    settings = MagicMock()
    settings.otel_exporter_otlp_endpoint = "http://localhost:4318"
    settings.otel_service_name = "test-service"

    proxy = trace.ProxyTracerProvider()
    with patch("opentelemetry.trace.get_tracer_provider", return_value=proxy):
        with patch("opentelemetry.trace.set_tracer_provider") as mock_set:
            with patch("opentelemetry.instrumentation.httpx.HTTPXClientInstrumentor.instrument"):
                initialize_tracer(settings)
                mock_set.assert_called_once()
                provider_arg = mock_set.call_args[0][0]
                assert isinstance(provider_arg, TracerProvider)


def test_initialize_tracer_tolerates_httpx_already_instrumented():
    """initialize_tracer must not raise when HTTPX is already instrumented."""
    settings = MagicMock()
    settings.otel_exporter_otlp_endpoint = "http://localhost:4318"
    settings.otel_service_name = "test-service"

    proxy = trace.ProxyTracerProvider()
    with patch("opentelemetry.trace.get_tracer_provider", return_value=proxy):
        with patch("opentelemetry.trace.set_tracer_provider"):
            with patch(
                "opentelemetry.instrumentation.httpx.HTTPXClientInstrumentor.instrument",
                side_effect=RuntimeError("already instrumented"),
            ):
                initialize_tracer(settings)  # must not raise


# ---------------------------------------------------------------------------
# restart_otel_span_processors
# ---------------------------------------------------------------------------


def test_restart_returns_false_when_no_sdk_provider():
    """restart_otel_span_processors must return False when no TracerProvider is active."""
    proxy = trace.ProxyTracerProvider()
    with patch("opentelemetry.trace.get_tracer_provider", return_value=proxy):
        assert restart_otel_span_processors() is False


def test_restart_returns_false_when_thread_alive():
    """restart_otel_span_processors must return False when the export thread is still running."""
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)

    with patch("opentelemetry.trace.get_tracer_provider", return_value=provider):
        assert restart_otel_span_processors() is False


def test_restart_returns_true_and_starts_thread_when_dead():
    """restart_otel_span_processors must restart a dead export thread and return True."""
    dead = threading.Thread(target=lambda: None, daemon=True)
    dead.start()
    dead.join(2)
    assert not dead.is_alive(), "precondition: thread must be dead before test"

    stub = _FakeBatchSpanProcessor(dead)
    provider = TracerProvider()
    # Place the stub directly as the active processor (no _span_processors attr → else branch).
    provider._active_span_processor = stub

    try:
        with patch("opentelemetry.trace.get_tracer_provider", return_value=provider):
            result = restart_otel_span_processors()

        assert result is True
        assert stub.worker_thread is not dead, "expected a new thread object to be assigned"
        assert stub.worker_thread.name == "OtelBatchSpanProcessorDaemon"
    finally:
        provider.shutdown()


def test_restart_returns_false_on_sdk_internal_error():
    """restart_otel_span_processors must return False (not raise) on unexpected SDK errors."""
    provider = TracerProvider()
    # Restore the attribute before shutdown so the SDK atexit handler can clean up cleanly.
    # We pop it only for the duration of the call under test.
    saved = provider.__dict__.pop("_active_span_processor", None)
    try:
        with patch("opentelemetry.trace.get_tracer_provider", return_value=provider):
            assert restart_otel_span_processors() is False
    finally:
        if saved is not None:
            provider._active_span_processor = saved
        provider.shutdown()


# ---------------------------------------------------------------------------
# events.py startup branching
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_startup_initializes_when_restart_returns_false(monkeypatch):
    """initialize_tracer is called in every worker when restart_otel_span_processors returns False.

    This covers both the agent-mode case (agent set up a TracerProvider in the master
    before fork; each worker must create its own fresh provider so the HTTP connection
    pool of OTLPSpanExporter is not shared across processes) and the no-agent case
    (no provider at all).
    """
    settings = MagicMock()
    settings.__iter__ = MagicMock(return_value=iter([]))

    with patch("app.core.events.restart_otel_span_processors", return_value=False):
        with patch("app.core.events.initialize_tracer") as mock_init:
            with patch("app.core.events.init_cache", new_callable=AsyncMock), patch(
                "app.core.events.init_pandas", new_callable=AsyncMock
            ):
                handler = create_start_app_handler(MagicMock(), settings)
                await handler()

    mock_init.assert_called_once_with(settings)


@pytest.mark.asyncio
async def test_startup_skips_init_when_restart_succeeds():
    """initialize_tracer is NOT called when restart_otel_span_processors returns True.

    When a live export thread already exists in this process (thread was restarted
    successfully) there is no need to create a new TracerProvider.
    """
    settings = MagicMock()
    settings.__iter__ = MagicMock(return_value=iter([]))

    with patch("app.core.events.restart_otel_span_processors", return_value=True):
        with patch("app.core.events.initialize_tracer") as mock_init:
            with patch("app.core.events.init_cache", new_callable=AsyncMock), patch(
                "app.core.events.init_pandas", new_callable=AsyncMock
            ):
                handler = create_start_app_handler(MagicMock(), settings)
                await handler()

    mock_init.assert_not_called()
