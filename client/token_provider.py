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
import base64
import json
import os
import threading
import time

import requests
from loguru import logger

EXPIRY_SKEW_SECONDS = 60
REQUEST_TIMEOUT_SECONDS = 30
RETRY_INTERVAL_SECONDS = 15
JWT_SEGMENTS = 3
BASE64_BLOCK = 4


def read_expiry(token: str) -> float:
    """Read the `exp` claim of a JWT without verifying its signature.

    :param token: encoded JWT
    :type token: str
    :return: expiry as a POSIX timestamp, or 0 when it cannot be read
    :rtype: float
    """
    segments = token.split(".") if token else []
    if len(segments) != JWT_SEGMENTS:
        return 0
    payload = segments[1]
    payload += "=" * (-len(payload) % BASE64_BLOCK)
    try:
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except (ValueError, TypeError):
        return 0
    return float(claims.get("exp", 0))


class TokenProvider(object):
    """Supply a bearer token, re-minting it shortly before it expires.

    A CIMPL integration run lasts far longer than the Keycloak access token
    lifetime, so a token captured once at job start leaves every later request
    failing with 401 "Jwt is expired". Callers use the instance itself as the
    token source, so a single provider is shared by all API sub-clients.
    """

    def __init__(  # noqa: S107
        self,
        token: str,
        token_url: str = "",
        client_id: str = "",
        client_secret: str = "",
    ) -> None:
        self._token = token
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._expires_at = read_expiry(token)
        self._blocked_until = 0
        self._lock = threading.Lock()

    def __call__(self) -> str:
        """Return a token that is not about to expire.

        :return: bearer token
        :rtype: str
        """
        if not self._refreshable() or not self._expiring():
            return self._token
        with self._lock:
            if self._expiring():
                self._refresh()
        return self._token

    @classmethod
    def from_env(cls, token: str) -> "TokenProvider":
        """Build a provider from the OIDC settings the CI job exports.

        :param token: token already minted by the CI job
        :type token: str
        :return: provider that refreshes when credentials are available
        :rtype: TokenProvider
        """
        return cls(
            token,
            token_url=os.environ.get("RAFS_OIDC_TOKEN_URL", "").strip(),
            client_id=os.environ.get("RAFS_OIDC_CLIENT_ID", "").strip(),
            client_secret=os.environ.get("RAFS_OIDC_CLIENT_SECRET", "").strip(),
        )

    def _refreshable(self) -> bool:
        return bool(self._token_url and self._client_id and self._client_secret)

    def _expiring(self) -> bool:
        if not self._token:
            return True
        if not self._expires_at:
            return False
        return time.time() >= self._expires_at - EXPIRY_SKEW_SECONDS

    def _refresh(self) -> None:
        if time.time() < self._blocked_until:
            return
        self._blocked_until = time.time() + RETRY_INTERVAL_SECONDS
        try:
            response = requests.post(
                self._token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "scope": "openid",
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as error:
            logger.error("Access token refresh failed: {0}", type(error).__name__)
            return
        self._store(response)

    def _store(self, response: requests.Response) -> None:
        if not response.ok:
            logger.error(f"Access token refresh rejected with {response.status_code}")
            return
        try:
            refreshed = response.json().get("access_token", "")
        except ValueError:
            logger.error("Access token refresh returned a non-JSON body")
            return
        if refreshed:
            self._token = refreshed
            self._expires_at = read_expiry(refreshed)
            logger.info("Refreshed the CIMPL access token before expiry")
