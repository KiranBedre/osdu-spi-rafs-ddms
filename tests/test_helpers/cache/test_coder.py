#  Copyright 2023 ExxonMobil Technology and Engineering Company
#
import base64
import json

import pytest
from fastapi_cache.coder import JsonCoder
from starlette.responses import Response

from app.core.helpers.cache.coder import ResponseCoder
from app.resources.mime_types import SupportedMimeTypes


@pytest.mark.parametrize(
    "media_type,encode_fn",
    [
        (SupportedMimeTypes.JSON.mime_type, JsonCoder.encode),
        ("application/any", lambda body: base64.b64encode(body).decode("ascii")),
    ],
)
def test_response_coder_encode(media_type, encode_fn):
    response = Response(
        content="content",
        media_type=media_type,
    )
    encoded_content = encode_fn(response.body)
    test_result = json.dumps(
        {
            "encoded_content": encoded_content,
            "media_type": media_type,
        }
    )

    expected_result = ResponseCoder.encode(response)

    assert test_result == expected_result


@pytest.mark.parametrize(
    "value_to_decode,decode_fn",
    [
        (
            {
                "encoded_content": '"content"',
                "media_type": SupportedMimeTypes.JSON.mime_type,
            },
            JsonCoder.decode,
        ),
        (
            {
                "encoded_content": base64.b64encode(b"content").decode("ascii"),
                "media_type": "application/any",
            },
            base64.b64decode,
        ),
    ],
)
def test_response_coder_decode(value_to_decode, decode_fn):
    encoded_content = value_to_decode.get("encoded_content")
    media_type = value_to_decode.get("media_type")
    test_result = Response(
        content=decode_fn(encoded_content),
        media_type=media_type,
    )

    expected_result = ResponseCoder.decode(json.dumps(value_to_decode))

    assert test_result.body == expected_result.body
    assert test_result.media_type == expected_result.media_type
