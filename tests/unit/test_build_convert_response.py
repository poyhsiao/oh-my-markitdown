"""
Unit tests for build_convert_response() in api/response.py.

These tests follow the TDD (RED → GREEN) cycle and cover all three
return_format values: json, markdown, download.
"""

import pytest
from fastapi.responses import JSONResponse, Response

from api.response import build_convert_response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_CONTENT = "# Hello\n\nWorld content here."
SAMPLE_METADATA = {
    "source": "test.pdf",
    "format": "markdown",
    "processing_time": 0.42,
}


# ---------------------------------------------------------------------------
# JSON format (default)
# ---------------------------------------------------------------------------


class TestBuildConvertResponseJson:
    """Tests for return_format='json' (default)."""

    def test_returns_json_response_type(self):
        response = build_convert_response(
            content=SAMPLE_CONTENT,
            metadata=SAMPLE_METADATA,
        )
        assert isinstance(response, JSONResponse)

    def test_default_format_is_json(self):
        """Calling without return_format should use json."""
        response = build_convert_response(
            content=SAMPLE_CONTENT,
            metadata=SAMPLE_METADATA,
        )
        assert isinstance(response, JSONResponse)

    def test_json_body_has_success_true(self):
        import json

        response = build_convert_response(
            content=SAMPLE_CONTENT,
            metadata=SAMPLE_METADATA,
        )
        body = json.loads(response.body)
        assert body["success"] is True

    def test_json_body_has_data_content(self):
        import json

        response = build_convert_response(
            content=SAMPLE_CONTENT,
            metadata=SAMPLE_METADATA,
        )
        body = json.loads(response.body)
        assert body["data"]["content"] == SAMPLE_CONTENT

    def test_json_body_has_data_metadata(self):
        import json

        response = build_convert_response(
            content=SAMPLE_CONTENT,
            metadata=SAMPLE_METADATA,
        )
        body = json.loads(response.body)
        assert body["data"]["metadata"] == SAMPLE_METADATA

    def test_json_body_has_request_id(self):
        import json

        response = build_convert_response(
            content=SAMPLE_CONTENT,
            metadata=SAMPLE_METADATA,
            request_id="req-test123",
        )
        body = json.loads(response.body)
        assert body["request_id"] == "req-test123"

    def test_json_body_request_id_auto_generated_when_not_provided(self):
        import json

        response = build_convert_response(
            content=SAMPLE_CONTENT,
            metadata=SAMPLE_METADATA,
        )
        body = json.loads(response.body)
        assert "request_id" in body
        assert body["request_id"] is not None

    def test_json_with_explicit_return_format(self):
        import json

        response = build_convert_response(
            content=SAMPLE_CONTENT,
            metadata=SAMPLE_METADATA,
            return_format="json",
        )
        body = json.loads(response.body)
        assert body["success"] is True


# ---------------------------------------------------------------------------
# Markdown format
# ---------------------------------------------------------------------------


class TestBuildConvertResponseMarkdown:
    """Tests for return_format='markdown'."""

    def test_returns_plain_response_type(self):
        response = build_convert_response(
            content=SAMPLE_CONTENT,
            metadata=SAMPLE_METADATA,
            return_format="markdown",
        )
        # Must NOT be JSONResponse
        assert not isinstance(response, JSONResponse)
        assert isinstance(response, Response)

    def test_content_type_is_text_markdown(self):
        response = build_convert_response(
            content=SAMPLE_CONTENT,
            metadata=SAMPLE_METADATA,
            return_format="markdown",
        )
        assert "text/markdown" in response.media_type

    def test_body_is_raw_markdown_utf8(self):
        response = build_convert_response(
            content=SAMPLE_CONTENT,
            metadata=SAMPLE_METADATA,
            return_format="markdown",
        )
        assert response.body == SAMPLE_CONTENT.encode("utf-8")

    def test_no_content_disposition_header(self):
        response = build_convert_response(
            content=SAMPLE_CONTENT,
            metadata=SAMPLE_METADATA,
            return_format="markdown",
        )
        # Should not have attachment header
        assert "content-disposition" not in {
            k.lower() for k in response.headers.keys()
        }

    def test_unicode_content_encoded_correctly(self):
        unicode_content = "# 繁體中文\n\n測試內容。"
        response = build_convert_response(
            content=unicode_content,
            metadata={},
            return_format="markdown",
        )
        assert response.body == unicode_content.encode("utf-8")


# ---------------------------------------------------------------------------
# Download format
# ---------------------------------------------------------------------------


class TestBuildConvertResponseDownload:
    """Tests for return_format='download'."""

    def test_returns_response_type(self):
        response = build_convert_response(
            content=SAMPLE_CONTENT,
            metadata=SAMPLE_METADATA,
            return_format="download",
        )
        assert isinstance(response, Response)
        assert not isinstance(response, JSONResponse)

    def test_content_type_is_text_markdown(self):
        response = build_convert_response(
            content=SAMPLE_CONTENT,
            metadata=SAMPLE_METADATA,
            return_format="download",
        )
        assert "text/markdown" in response.media_type

    def test_has_content_disposition_attachment(self):
        response = build_convert_response(
            content=SAMPLE_CONTENT,
            metadata=SAMPLE_METADATA,
            return_format="download",
        )
        disposition = response.headers.get("content-disposition", "")
        assert "attachment" in disposition

    def test_content_disposition_contains_default_filename(self):
        response = build_convert_response(
            content=SAMPLE_CONTENT,
            metadata=SAMPLE_METADATA,
            return_format="download",
        )
        disposition = response.headers.get("content-disposition", "")
        assert "output.md" in disposition

    def test_content_disposition_contains_custom_filename(self):
        response = build_convert_response(
            content=SAMPLE_CONTENT,
            metadata=SAMPLE_METADATA,
            return_format="download",
            filename="my_document.md",
        )
        disposition = response.headers.get("content-disposition", "")
        assert "my_document.md" in disposition

    def test_body_is_raw_markdown_utf8(self):
        response = build_convert_response(
            content=SAMPLE_CONTENT,
            metadata=SAMPLE_METADATA,
            return_format="download",
        )
        assert response.body == SAMPLE_CONTENT.encode("utf-8")

    def test_unicode_content_in_download(self):
        unicode_content = "# 日本語\n\nテスト内容。"
        response = build_convert_response(
            content=unicode_content,
            metadata={},
            return_format="download",
        )
        assert response.body == unicode_content.encode("utf-8")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestBuildConvertResponseEdgeCases:
    """Edge-case coverage."""

    def test_empty_metadata_produces_valid_json(self):
        import json

        response = build_convert_response(content="# Hi", metadata={})
        body = json.loads(response.body)
        assert body["data"]["metadata"] == {}

    def test_empty_content_string(self):
        import json

        response = build_convert_response(content="", metadata={})
        body = json.loads(response.body)
        assert body["data"]["content"] == ""

    def test_metadata_with_nested_values(self):
        import json

        meta = {
            "segments": [{"start": 0.0, "end": 2.5, "text": "hello"}],
            "duration": 10.0,
        }
        response = build_convert_response(content="# Hi", metadata=meta)
        body = json.loads(response.body)
        assert body["data"]["metadata"]["segments"][0]["text"] == "hello"
