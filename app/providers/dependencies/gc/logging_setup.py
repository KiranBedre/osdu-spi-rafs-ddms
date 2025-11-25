# Copyright 2024 Google LLC
# Copyright 2024 EPAM Systems
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
import logging
import sys

from loguru import logger

from app.core.helpers.app_filter_logging import AppFilterLogging

# Log level thresholds (from logging module)
_ERROR_LEVEL = logging.ERROR  # 40
_WARNING_LEVEL = logging.WARNING  # 30
_INFO_LEVEL = logging.INFO  # 20


class StructuredLogHandler(logging.StreamHandler):
    """Custom Log Handler to emit logs in a structured JSON format for GKE."""

    def emit(self, record):
        log_entry = {
            "message": record.getMessage(),
            "severity": record.levelname,
        }
        log_json = json.dumps(log_entry)
        self.stream.write(f"{log_json}\n")


def setup_logging():
    """Configure logging for Google Cloud (GKE).

    Uses structured JSON logs to stdout which GKE automatically
    picks up and sends to Cloud Logging with proper severity levels.
    """
    # Integrate Loguru with structured log format
    logger.configure(handlers=[{"sink": log_to_gc, "format": "{message}"}])

    # Initialize root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Set up structured logging to stdout (GKE collects this)
    structured_handler = StructuredLogHandler(stream=sys.stdout)
    structured_handler.setLevel(logging.DEBUG)
    structured_handler.addFilter(AppFilterLogging())

    root_logger.addHandler(structured_handler)
    root_logger.propagate = False


def log_to_gc(message):
    """Loguru integration for Google Cloud Logging."""
    record = message.record
    level_no = record["level"].no
    if level_no >= _ERROR_LEVEL:
        logging.error(record["message"])
    elif level_no >= _WARNING_LEVEL:
        logging.warning(record["message"])
    elif level_no >= _INFO_LEVEL:
        logging.info(record["message"])
    else:
        logging.debug(record["message"])
