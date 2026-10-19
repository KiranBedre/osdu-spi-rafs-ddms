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

"""Shared utilities for Azure Redis Entra ID authentication."""

from typing import Optional

import jwt
from loguru import logger


def extract_oid_from_token(token: str) -> Optional[str]:
    """Extract the OID (Object ID) claim from a JWT token.

    Uses PyJWT to decode the token without verification since the token
    is already validated by Azure Identity SDK.

    :param str token: The JWT access token
    :return: The OID claim value if found, None otherwise
    :rtype: Optional[str]
    """
    try:
        # Decode without verification - token is already validated by Azure Identity
        # algorithms required by PyJWT >=2.14 even when verify_signature is False
        decoded = jwt.decode(
            token,
            options={"verify_signature": False},
            algorithms=["RS256"],
        )
        oid = decoded.get("oid")

        if not oid:
            logger.warning("No OID claim found in JWT token")

        return oid
    except jwt.DecodeError as exc:
        logger.warning(f"Failed to decode JWT token: {exc}")
        return None
    except Exception as exc:  # noqa: B902
        logger.warning(f"Unexpected error extracting OID from token: {exc}")
        return None
