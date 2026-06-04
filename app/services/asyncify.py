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

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from typing import Any, Callable, Optional, TypeVar

TFunc = TypeVar("TFunc", bound=Callable[..., Any])

DEFAULT_MAX_WORKERS = 32
EXTRA_WORKERS = 4


def run_in_threadpool(method: TFunc) -> TFunc:
    """Run the decorated method in a thread pool.

    :param method: The method to decorate
    :type method: TFunc
    :return: The decorated method
    :rtype: TFunc
    """

    @wraps(method)
    def wrapper(
        self: Any,
        *args: Any,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        max_workers: Optional[int] = None,
        **kwargs: Any,
    ) -> Any:
        if loop is None:
            loop = asyncio.get_event_loop()
        if max_workers is None:
            max_workers = min(DEFAULT_MAX_WORKERS, (os.cpu_count() or 1) + EXTRA_WORKERS)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            pfunc = partial(method, self, *args, **kwargs)
            return loop.run_in_executor(executor, pfunc)

    return wrapper
