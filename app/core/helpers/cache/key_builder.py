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

import hashlib
from typing import Callable, Optional

from starlette.requests import Request
from starlette.responses import Response


def key_builder_using_token(
    func: Callable,
    namespace: Optional[str] = "",
    request: Optional[Request] = None,
    response: Optional[Response] = None,
    args: Optional[tuple] = None,
    kwargs: Optional[dict] = None,
) -> str:
    """Key builder for authorized requests."""
    from fastapi_cache import FastAPICache

    func_meta = f"{func.__module__}:{func.__name__}"
    prefix = f"{FastAPICache.get_prefix()}:{namespace}"

    token = request.headers.get("authorization")
    data_partition_id = request.headers.get("data-partition-id")
    content_type = request.headers.get("content-type")
    url = request.url
    query_params = request.query_params.multi_items()
    query_meta = f"{data_partition_id}:{token}:{url}:{query_params}:{content_type}"

    hash_key = hashlib.sha256(
        f"{func_meta}:{query_meta}".encode(),
    ).hexdigest()

    return f"{prefix}:{hash_key}"


def _build_args_string(args: Optional[tuple]) -> str:
    """Build stable string representation from positional arguments.

    :param args: Positional arguments (args[0] is 'self', skipped)
    :return: String representation of arguments
    """
    if not args or len(args) <= 1:
        return ""

    args_list = []
    for arg in args[1:]:
        if isinstance(arg, list):
            args_list.append(str(sorted(arg)))
        else:
            args_list.append(str(arg))
    return ":".join(args_list)


def _build_kwargs_string(kwargs: Optional[dict]) -> str:
    """Build stable string representation from keyword arguments.

    :param kwargs: Keyword arguments dictionary
    :return: String representation of kwargs
    """
    if not kwargs:
        return ""

    return ":".join(f"{kwarg_key}={kwarg_value}" for kwarg_key, kwarg_value in sorted(kwargs.items()))


def key_builder_for_service_methods(
    func: Callable,
    namespace: Optional[str] = "",
    request: Optional[Request] = None,
    response: Optional[Response] = None,
    args: Optional[tuple] = None,
    kwargs: Optional[dict] = None,
) -> str:
    """Key builder for service methods that don't have request parameter.

    This key builder generates cache keys based on function arguments instead
    of request headers. It's designed for service layer methods like
    SchemaService.get_schema(schema_id) or DatasetService.get_signed_urls(dataset_ids).

    The cache key is generated from:
    - Function module and name
    - Function arguments (excluding 'self')
    - Function keyword arguments

    :param func: The function being cached
    :param namespace: Cache namespace (optional)
    :param request: HTTP request (ignored for service methods)
    :param response: HTTP response (ignored)
    :param args: Positional arguments passed to the function
    :param kwargs: Keyword arguments passed to the function
    :return: Cache key as string
    """
    from fastapi_cache import FastAPICache

    func_meta = f"{func.__module__}:{func.__name__}"
    prefix = f"{FastAPICache.get_prefix()}:{namespace}"

    args_str = _build_args_string(args)
    kwargs_str = _build_kwargs_string(kwargs)

    cache_meta = f"{args_str}:{kwargs_str}" if kwargs_str else args_str

    hash_key = hashlib.sha256(
        f"{func_meta}:{cache_meta}".encode(),
    ).hexdigest()

    return f"{prefix}:{hash_key}"
