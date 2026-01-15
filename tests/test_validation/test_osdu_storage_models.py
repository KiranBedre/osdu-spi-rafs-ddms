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

"""Tests for OSDU storage models validation (#669)."""

import pytest
from pydantic import ValidationError

from app.models.schemas.osdu_storage import Acl, Legal


class TestAclExtraFieldsRejected:
    """Test that Acl model rejects extra fields."""

    def test_acl_valid_fields_accepted(self):
        """Test that valid Acl fields are accepted."""
        acl = Acl(viewers=["user@example.com"], owners=["owner@example.com"])
        assert acl.viewers == ["user@example.com"]
        assert acl.owners == ["owner@example.com"]

    def test_acl_extra_fields_rejected(self):
        """Test that extra fields in Acl are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Acl(
                viewers=["user@example.com"],
                owners=["owner@example.com"],
                fakeField="this should be rejected",
            )
        assert "extra fields not permitted" in str(exc_info.value)

    def test_acl_multiple_extra_fields_rejected(self):
        """Test that multiple extra fields in Acl are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Acl(
                viewers=["user@example.com"],
                owners=["owner@example.com"],
                fakeField1="rejected",
                fakeField2="also rejected",
            )
        assert "extra fields not permitted" in str(exc_info.value)


class TestLegalExtraFieldsRejected:
    """Test that Legal model rejects extra fields."""

    def test_legal_valid_fields_accepted(self):
        """Test that valid Legal fields are accepted."""
        legal = Legal(
            legaltags=["tag1"],
            otherRelevantDataCountries=["US"],
            status="compliant",
        )
        assert legal.legaltags == ["tag1"]
        assert legal.otherRelevantDataCountries == ["US"]
        assert legal.status == "compliant"

    def test_legal_valid_without_optional_status(self):
        """Test that Legal is valid without optional status field."""
        legal = Legal(
            legaltags=["tag1"],
            otherRelevantDataCountries=["US"],
        )
        assert legal.legaltags == ["tag1"]
        assert legal.status is None

    def test_legal_extra_fields_rejected(self):
        """Test that extra fields in Legal are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Legal(
                legaltags=["tag1"],
                otherRelevantDataCountries=["US"],
                madeUpField="this should be rejected",
            )
        assert "extra fields not permitted" in str(exc_info.value)

    def test_legal_multiple_extra_fields_rejected(self):
        """Test that multiple extra fields in Legal are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Legal(
                legaltags=["tag1"],
                otherRelevantDataCountries=["US"],
                status="compliant",
                madeUpField1="rejected",
                madeUpField2="also rejected",
            )
        assert "extra fields not permitted" in str(exc_info.value)
