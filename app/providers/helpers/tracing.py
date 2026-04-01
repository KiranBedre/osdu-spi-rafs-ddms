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


MAX_EXPORT_TIMEOUT_MS = 2000


def initialize_tracer(settings) -> None:
    """Initialize OpenTelemetry tracer. No-op when endpoint is not configured."""
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
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
    processor = BatchSpanProcessor(exporter, max_export_timeout_millis=MAX_EXPORT_TIMEOUT_MS)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    set_global_textmap(B3MultiFormat())
    HTTPXClientInstrumentor().instrument()
