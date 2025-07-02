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

import io
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber

from app.providers.dependencies.aws.blob_loader import (
    CREDENTIALS_CACHE,
    AWSBlobLoader,
)

TEST_BUCKET = "test-bucket"
TEST_KEY = "opendes/abc/123"
TEST_BLOB_URL = f"https://{TEST_BUCKET}.s3.us-east-1.amazonaws.com/{TEST_KEY}?Param=p"
TEST_BLOB = b"blob"


class TestBlobLoader:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.s3_client = boto3.client("s3")
        self.stubber = Stubber(self.s3_client)
        self.stubber.activate()

        self.blob_loader = AWSBlobLoader(self.s3_client)

    def teardown_method(self):
        self.stubber.deactivate()

    @pytest.mark.asyncio
    async def test_aws_blob_loader_without_s3_client(self):
        expired_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        CREDENTIALS_CACHE["expiration"] = expired_time
        mock_s3_client = MagicMock()

        with patch("app.providers.dependencies.aws.blob_loader.datetime") as mock_datetime, \
                patch("app.providers.dependencies.aws.blob_loader.refresh_credentials") as mock_refresh_credentials:
            mock_datetime.now.return_value = datetime.now(timezone.utc)
            mock_refresh_credentials.return_value = None
            CREDENTIALS_CACHE["s3_client"] = mock_s3_client

            loader = AWSBlobLoader()

            mock_refresh_credentials.assert_called_once()

            assert loader.s3_client == mock_s3_client

    @pytest.mark.asyncio
    async def test_upload_blob(self):
        expected_params = {
            "Bucket": TEST_BUCKET,
            "Key": TEST_KEY,
            "Body": TEST_BLOB,
        }
        put_response = {
            "ETag": "6805f2cfc46c0f04559748bb039d69ae",
            "VersionId": "Bvq0EDKxOcXLJXNo_Lkz37eM3R4pfzyQ",
            "ResponseMetadata": {
                "RequestId": "abc123",
                "HTTPStatusCode": 200,
                "HostId": "abc123",
            },
        }
        self.stubber.add_response("put_object", put_response, expected_params)
        upload_response = await self.blob_loader.upload_blob(TEST_BLOB_URL, TEST_BLOB)

        assert upload_response == put_response

    @pytest.mark.asyncio
    async def test_download_blob(self):
        expected_message = {
            "message": "blob",
        }

        encoded_message = json.dumps(expected_message).encode()
        raw_stream = StreamingBody(
            io.BytesIO(encoded_message),
            len(encoded_message),
        )
        get_response = {
            "Body": raw_stream,
        }
        self.stubber.add_response("get_object", get_response)
        download_response = await self.blob_loader.download_blob(TEST_BLOB_URL)
        assert download_response == encoded_message
