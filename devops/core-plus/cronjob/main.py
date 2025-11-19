#!/usr/bin/env python3
"""RAFS DDMS Service Account Indexer Trigger Cronjob.

Triggers the SA indexer via RAFS API with OAuth authentication and retry logic.
"""

import logging
import os
import sys
from typing import Optional

import requests
from requests.exceptions import RequestException
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

# Suppress insecure request warnings when verify=False
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Constants
REQUEST_TIMEOUT = 30
OAUTH_TIMEOUT = 10
HTTP_OK = 200

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="{asctime} - {levelname} - {message}",
    style='{',
)
logger = logging.getLogger(__name__)


def validate_environment() -> dict:
    """Validate all required environment variables exist."""
    required_vars = [
        "OAUTH_TOKEN_URL",
        "CLIENT_ID",
        "CLIENT_SECRET",
        "OAUTH_SCOPE",
        "RAFS_URI",
    ]

    config = {}
    for env_var in required_vars:
        env_value = os.getenv(env_var)
        if not env_value:
            logger.error(f"Missing required environment variable: {env_var}")
            sys.exit(1)
        config[env_var] = env_value

    # Optional with default
    config["DATA_PARTITION_ID"] = os.getenv("DATA_PARTITION_ID", "opendes")

    logger.info("Environment variables validated successfully")
    return config


def get_oauth_token(config: dict) -> Optional[str]:
    """Get OAuth access token using client credentials flow."""
    try:
        logger.info(f'Requesting OAuth token from {config["OAUTH_TOKEN_URL"]}')

        payload = {
            "grant_type": "client_credentials",
            "client_id": config["CLIENT_ID"],
            "client_secret": config["CLIENT_SECRET"],
            "scope": config["OAUTH_SCOPE"],
        }

        response = requests.post(
            config["OAUTH_TOKEN_URL"],
            data=payload,
            verify=False,  # noqa: S501
            timeout=OAUTH_TIMEOUT,
        )
        response.raise_for_status()

        token = response.json().get("access_token")
        if not token:
            logger.error("No access token in OAuth response")
            return None

        logger.info("OAuth token obtained successfully")
        return token

    except RequestException as error:
        logger.warning(f"Failed to get OAuth token: {error}")
        raise


@retry(
    wait=wait_fixed(4),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(RuntimeError),
    reraise=True,
)
def trigger_indexer(config: dict, token: str) -> None:
    """Trigger the RAFS SA indexer with retry logic."""
    url = f'{config["RAFS_URI"]}/api/rafs-ddms/dev/trigger-sa-indexer'

    headers = {
        "Authorization": f"Bearer {token}",
        "data-partition-id": config["DATA_PARTITION_ID"],
    }

    logger.info(f"Triggering indexer at {url}")

    try:
        response = requests.get(
            url,
            headers=headers,
            verify=False,  # noqa: S501
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != HTTP_OK:
            logger.warning(
                f"Indexer endpoint returned status {response.status_code}: {response.text}"
            )
            raise RuntimeError(
                f"Expected {HTTP_OK} response, got {response.status_code}"
            )

        logger.info("Indexer triggered successfully")

    except RequestException as error:
        logger.warning(f"Failed to trigger indexer: {error}")
        raise


def main() -> None:
    """Main entry point for the cronjob."""
    try:
        logger.info("Starting RAFS DDMS SA Indexer Trigger Cronjob")

        # Validate environment
        config = validate_environment()

        # Get OAuth token
        token = get_oauth_token(config)
        if not token:
            logger.error("Failed to obtain OAuth token")
            sys.exit(1)

        # Trigger indexer with retry
        trigger_indexer(config, token)

        logger.info("Cronjob completed successfully")
        sys.exit(0)

    except RuntimeError as error:
        logger.error(f"Cronjob failed: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
