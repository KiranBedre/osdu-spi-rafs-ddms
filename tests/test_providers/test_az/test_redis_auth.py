#  Copyright 2026 Microsoft Corporation
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

"""Unit tests for Azure Redis authentication utilities."""

import base64
import json

import pytest

from app.providers.dependencies.az.redis_auth import extract_oid_from_token


class TestRedisAuthUtilities:
    """Test cases for Redis auth utility functions."""

    @pytest.fixture
    def mock_token_with_oid(self):
        """Create a mock JWT token with OID claim."""
        header = {"alg": "RS256", "typ": "JWT"}
        payload = {"oid": "12345678-1234-1234-1234-123456789abc", "exp": 9999999999}

        # Encode header and payload as base64
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        signature = base64.urlsafe_b64encode(b"mock_signature").decode().rstrip(
            "="
        )

        return f"{header_b64}.{payload_b64}.{signature}"

    def test_extract_oid_from_valid_token(self, mock_token_with_oid):
        """Test extracting OID from valid JWT token."""
        oid = extract_oid_from_token(mock_token_with_oid)
        assert oid == "12345678-1234-1234-1234-123456789abc"

    def test_extract_oid_from_token_without_oid(self):
        """Test extracting OID from token without OID claim returns None."""
        # Token without OID claim
        header = {"alg": "RS256", "typ": "JWT"}
        payload = {"sub": "subject", "exp": 9999999999}

        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        token_no_oid = f"{header_b64}.{payload_b64}.signature"

        oid = extract_oid_from_token(token_no_oid)
        assert oid is None

    def test_extract_oid_from_invalid_token(self):
        """Test extracting OID from malformed token returns None.

        PyJWT handles all token validation (format, base64, JSON parsing).
        Any invalid token will raise jwt.DecodeError, which we catch and return None.
        """
        invalid_token = "not.a.valid.jwt.token"
        oid = extract_oid_from_token(invalid_token)
        assert oid is None
