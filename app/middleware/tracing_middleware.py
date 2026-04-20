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

from opentelemetry import trace
from opentelemetry.propagate import extract
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware that creates a server span for each incoming HTTP request."""

    async def dispatch(self, request: Request, call_next):
        tracer = trace.get_tracer(__name__)
        ctx = extract(request.headers)
        route = request.scope.get("path", "/")
        with tracer.start_as_current_span(
            route,
            context=ctx,
            kind=trace.SpanKind.SERVER,
        ) as span:
            response = await call_next(request)
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.route", route)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.host", request.url.hostname or "")
            span.set_attribute("http.status_code", response.status_code)
        return response
