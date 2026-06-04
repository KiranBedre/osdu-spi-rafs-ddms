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

import json
from pathlib import Path
from typing import Callable

from filelock import FileLock
from loguru import logger


def _update_worker_counter(counter_file: Path, delta: int) -> int:
    """Atomically update the active worker counter and return the new value.
    Used internally for pytest-xdist cross-worker coordination to determine
    when the last worker has finished and cleanup should be performed.
    :param counter_file: Path to the counter file
    :param delta: Increment (+1 on setup) or decrement (-1 on teardown)
    :return: New counter value after update
    """
    current = int(counter_file.read_text()) if counter_file.is_file() else 0
    new_value = current + delta
    counter_file.write_text(str(new_value))
    return new_value


def begin_cross_worker_session(shared_dir: Path, name: str, setup: Callable[[], dict]) -> dict:
    """Begin a session-scoped resource shared across xdist workers.
    Calls ``setup()`` exactly once across all workers (first worker creates).
    Subsequent workers reuse the persisted state.
    :param shared_dir: Directory shared across all xdist workers
    :param name: Unique name for coordination files
    :param setup: Callable that creates the resource, returns a JSON-serializable dict
    :return: The state dict (created by first worker or loaded by subsequent workers)
    """
    lock = FileLock(str(shared_dir / f"{name}.lock"))
    state_file = shared_dir / f"{name}.state.json"
    counter_file = shared_dir / f"{name}.counter"

    with lock:
        if state_file.is_file():
            state = json.loads(state_file.read_text())
        else:
            state = setup()
            state_file.write_text(json.dumps(state))
        _update_worker_counter(counter_file, delta=1)
    return state


def end_cross_worker_session(shared_dir: Path, name: str, state: dict, teardown: Callable[[dict], None]) -> None:
    """End a session-scoped resource shared across xdist workers.
    Calls ``teardown(state)`` exactly once after the last worker finishes.
    :param shared_dir: Directory shared across all xdist workers (same as begin)
    :param name: Unique name for coordination files (same as begin)
    :param state: The state dict from begin_cross_worker_session
    :param teardown: Callable that destroys the resource, given the state dict
    """
    lock = FileLock(str(shared_dir / f"{name}.lock"))
    state_file = shared_dir / f"{name}.state.json"
    counter_file = shared_dir / f"{name}.counter"

    with lock:
        if _update_worker_counter(counter_file, delta=-1) > 0:
            return
        try:
            teardown(state)
        except Exception as exc:
            logger.warning(f"Teardown failed for '{name}': {exc}")
        state_file.unlink(missing_ok=True)
        counter_file.unlink(missing_ok=True)
