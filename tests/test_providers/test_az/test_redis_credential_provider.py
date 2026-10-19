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

"""Unit tests for Azure Redis credential provider."""

import base64
import json
from unittest.mock import Mock, patch

import pytest
from azure.core.credentials import AccessToken

from app.providers.dependencies.az.redis_credential_provider import AzureRedisCredentialProvider


class TestAzureRedisCredentialProvider:
    """Test cases for AzureRedisCredentialProvider class."""

    @pytest.fixture
    def mock_token_with_oid(self):
        """Create a mock JWT token with OID claim."""
        header = {"alg": "RS256", "typ": "JWT"}
        payload = {"oid": "test-oid-12345", "exp": 9999999999}

        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        # PyJWT >=2.15 requires valid base64url padding on the crypto segment
        signature = base64.urlsafe_b64encode(b"mock_signature").decode().rstrip("=")

        return f"{header_b64}.{payload_b64}.{signature}"

    def test_get_credentials_returns_username_and_token(self, mock_token_with_oid):
        """Test that get_credentials returns (username, token) tuple."""
        with patch("app.providers.dependencies.az.redis_credential_provider.DefaultAzureCredential") as mock_cred_class:
            mock_credential = Mock()
            mock_credential.get_token = Mock(return_value=AccessToken(token=mock_token_with_oid, expires_on=9999999999))
            mock_credential.close = Mock()
            mock_cred_class.return_value = mock_credential

            provider = AzureRedisCredentialProvider()
            result = provider.get_credentials()

            assert result is not None
            username, token = result
            assert username == "test-oid-12345"
            assert token == mock_token_with_oid

    def test_get_credentials_can_be_called_multiple_times(self, mock_token_with_oid):
        """Test that get_credentials can be called multiple times (for token refresh)."""
        with patch("app.providers.dependencies.az.redis_credential_provider.DefaultAzureCredential") as mock_cred_class:
            mock_credential = Mock()
            mock_credential.get_token = Mock(return_value=AccessToken(token=mock_token_with_oid, expires_on=9999999999))
            mock_credential.close = Mock()
            mock_cred_class.return_value = mock_credential

            provider = AzureRedisCredentialProvider()

            # First call
            result1 = provider.get_credentials()
            assert result1 is not None

            # Second call (simulating refresh)
            result2 = provider.get_credentials()
            assert result2 is not None

            # Both should return the same format
            assert len(result1) == 2
            assert len(result2) == 2

    def test_get_credentials_raises_on_failure(self):
        """Test that get_credentials raises exception when auth fails."""
        with patch("app.providers.dependencies.az.redis_credential_provider.DefaultAzureCredential") as mock_cred_class:
            mock_credential = Mock()
            mock_credential.get_token = Mock(side_effect=Exception("Auth failed"))
            mock_credential.close = Mock()
            mock_cred_class.return_value = mock_credential

            provider = AzureRedisCredentialProvider()

            with pytest.raises(Exception, match="Unable to obtain Azure Entra credentials"):
                provider.get_credentials()

    def test_get_credentials_raises_on_missing_oid(self):
        """Test that get_credentials raises exception when token has no OID."""
        # Token without OID claim
        payload = {"sub": "subject", "exp": 9999999999}
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        token_no_oid = f"header.{payload_b64}.signature"

        with patch("app.providers.dependencies.az.redis_credential_provider.DefaultAzureCredential") as mock_cred_class:
            mock_credential = Mock()
            mock_credential.get_token = Mock(return_value=AccessToken(token=token_no_oid, expires_on=9999999999))
            mock_credential.close = Mock()
            mock_cred_class.return_value = mock_credential

            provider = AzureRedisCredentialProvider()

            with pytest.raises(Exception, match="Unable to obtain Azure Entra credentials"):
                provider.get_credentials()

    def test_del_closes_credential(self, mock_token_with_oid):
        """Test that __del__ closes the credential."""
        with patch("app.providers.dependencies.az.redis_credential_provider.DefaultAzureCredential") as mock_cred_class:
            mock_credential = Mock()
            mock_credential.get_token = Mock(return_value=AccessToken(token=mock_token_with_oid, expires_on=9999999999))
            mock_credential.close = Mock()
            mock_cred_class.return_value = mock_credential

            provider = AzureRedisCredentialProvider()
            provider.get_credentials()

            # Manually trigger cleanup
            provider.__del__()
            mock_credential.close.assert_called_once()
