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


import logging  # noqa: WPS433
import threading

MAX_EXPORT_TIMEOUT_MS = 2000

_logger = logging.getLogger(__name__)


def _restart_processor(processor, bsp_class) -> bool:
    """Restart a single dead BatchSpanProcessor export thread.

    Requires opentelemetry-sdk ≥ 1.27 (0.48b0) where BatchSpanProcessor exposes
    ``worker_thread``, ``done``, and ``worker`` as public instance attributes.

    :param processor: span processor candidate
    :param bsp_class: BatchSpanProcessor class used for the isinstance check
    :return: True if the thread was dead and has been restarted, False otherwise
    :rtype: bool
    """
    if not isinstance(processor, bsp_class):
        return False
    if processor.worker_thread.is_alive():
        return False
    processor.done = False
    new_thread = threading.Thread(
        target=processor.worker,
        daemon=True,
        name="OtelBatchSpanProcessorDaemon",
    )
    new_thread.start()
    processor.worker_thread = new_thread
    return True


def restart_otel_span_processors() -> bool:
    """Restart dead BatchSpanProcessor export threads in forked uvicorn workers.

    When uvicorn forks workers, the background export thread of BatchSpanProcessor
    is not inherited by the child process.  This function detects dead threads and
    restarts them so spans are actually exported.

    SDK-internal fields are accessed by necessity; guarded with try/except so
    any SDK-internal change degrades gracefully instead of crashing the worker.

    :return: True if at least one thread was restarted, False otherwise
    :rtype: bool
    """
    from opentelemetry import trace  # noqa: WPS433
    from opentelemetry.sdk.trace import TracerProvider  # noqa: WPS433
    from opentelemetry.sdk.trace.export import BatchSpanProcessor  # noqa: WPS433

    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        return False

    try:  # noqa: WPS229
        restarted = False
        span_processor = provider._active_span_processor  # noqa: WPS437
        candidates = (
            list(span_processor._span_processors)  # noqa: WPS437
            if getattr(span_processor, "_span_processors", None) is not None  # noqa: WPS421
            else [span_processor]
        )
        for processor in candidates:
            if _restart_processor(processor, BatchSpanProcessor):
                restarted = True
        return restarted
    except Exception:  # noqa: WPS329
        _logger.warning("Failed to restart OTEL span processor thread; tracing may be degraded", exc_info=True)
        return False


def initialize_tracer(settings) -> None:
    """Initialize OpenTelemetry tracer. No-op when endpoint is not configured or already set."""
    if not settings.otel_exporter_otlp_endpoint:
        return

    from opentelemetry import trace  # noqa: WPS433
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # noqa: WPS433
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor  # noqa: WPS433
    from opentelemetry.propagate import set_global_textmap  # noqa: WPS433
    from opentelemetry.propagators.b3 import B3MultiFormat  # noqa: WPS433
    from opentelemetry.sdk.resources import Resource  # noqa: WPS433
    from opentelemetry.sdk.trace import TracerProvider  # noqa: WPS433
    from opentelemetry.sdk.trace.export import BatchSpanProcessor  # noqa: WPS433

    resource = Resource.create({"service.name": settings.otel_service_name})
    traces_endpoint = "{0}/v1/traces".format(settings.otel_exporter_otlp_endpoint.rstrip("/"))
    exporter = OTLPSpanExporter(endpoint=traces_endpoint)
    processor = BatchSpanProcessor(exporter, export_timeout_millis=MAX_EXPORT_TIMEOUT_MS)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    set_global_textmap(B3MultiFormat())
    try:
        HTTPXClientInstrumentor().instrument()
    except RuntimeError:
        _logger.debug("HTTPXClientInstrumentor already instrumented; skipping")
