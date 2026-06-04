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
from fastapi import FastAPI, Response
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from starlette import status

from app.middleware.tracing_middleware import TracingMiddleware

TEST_ROUTE = "/"


def _make_app() -> FastAPI:
    test_app = FastAPI()
    route = APIRoute(TEST_ROUTE, lambda: Response(content="OK"))
    test_app.router.routes = [route]
    test_app.add_middleware(TracingMiddleware)
    return test_app


def test_tracing_middleware_noop_no_exception():
    """No-op path: request completes 200 with the default no-op tracer provider."""
    test_app = _make_app()
    client = TestClient(test_app)
    response = client.get(TEST_ROUTE)
    assert response.status_code == status.HTTP_200_OK


def test_tracing_middleware_creates_span_with_attributes():
    """Active path: one span is created with correct HTTP attributes."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    original_provider = trace.get_tracer_provider()
    trace.set_tracer_provider(provider)

    try:
        test_app = _make_app()
        client = TestClient(test_app)
        response = client.get(TEST_ROUTE)
        assert response.status_code == status.HTTP_200_OK

        finished_spans = exporter.get_finished_spans()
        assert len(finished_spans) == 1

        span = finished_spans[0]
        assert span.attributes["http.method"] == "GET"
        assert span.attributes["http.route"] == TEST_ROUTE
        assert span.attributes["http.status_code"] == 200
    finally:
        trace.set_tracer_provider(original_provider)
