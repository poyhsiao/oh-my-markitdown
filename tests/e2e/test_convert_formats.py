"""
E2E smoke tests for the unified return_format parameter across all convert endpoints.

These tests verify that:
1. All convert endpoints default to JSON format
2. markdown and download formats work correctly
3. Invalid return_format values are rejected with HTTP 422
4. Error responses are always returned in JSON regardless of return_format

Endpoints covered:
  - POST /api/v1/convert/file
  - POST /api/v1/convert/url  (Query params)
  - POST /api/v1/convert/youtube  (JSON body)
  - POST /api/v1/convert/audio
  - POST /api/v1/convert/video
  - POST /api/v1/convert/clean-html  (Query url or File upload)
"""

import io
import json
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client():
    """HTTPX async client wired to the FastAPI test app."""
    from api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_HTML = "<html><body><h1>Hello World</h1><p>Test paragraph.</p></body></html>"


def _html_file() -> dict:
    """HTML multipart file for /convert/file (supported format)."""
    return {
        "file": ("test.html", io.BytesIO(SAMPLE_HTML.encode("utf-8")), "text/html")
    }


def _html_upload_file() -> dict:
    """HTML multipart file upload for /convert/clean-html."""
    return {
        "file": ("test.html", io.BytesIO(SAMPLE_HTML.encode("utf-8")), "text/html")
    }


def _audio_file() -> dict:
    """Fake audio multipart file — exercises parameter validation only."""
    return {
        "file": ("test.mp3", io.BytesIO(b"fake audio bytes"), "audio/mpeg")
    }


def _video_file() -> dict:
    """Fake video multipart file — exercises parameter validation only."""
    return {
        "file": ("test.mp4", io.BytesIO(b"fake video bytes"), "video/mp4")
    }


# ---------------------------------------------------------------------------
# POST /api/v1/convert/file
# ---------------------------------------------------------------------------


class TestConvertFileFormat:
    """E2E tests for return_format on /api/v1/convert/file."""

    @pytest.mark.asyncio
    async def test_default_returns_json(self, client):
        response = await client.post(
            "/api/v1/convert/file",
            files=_html_file(),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "content" in body["data"]
        assert "request_id" in body

    @pytest.mark.asyncio
    async def test_json_explicit_returns_json(self, client):
        response = await client.post(
            "/api/v1/convert/file",
            files=_html_file(),
            params={"return_format": "json"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        body = response.json()
        assert body["success"] is True

    @pytest.mark.asyncio
    async def test_markdown_returns_text_markdown(self, client):
        response = await client.post(
            "/api/v1/convert/file",
            files=_html_file(),
            params={"return_format": "markdown"},
        )
        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]
        assert response.content  # non-empty body

    @pytest.mark.asyncio
    async def test_download_has_attachment_header(self, client):
        response = await client.post(
            "/api/v1/convert/file",
            files=_html_file(),
            params={"return_format": "download"},
        )
        assert response.status_code == 200
        assert "attachment" in response.headers.get("content-disposition", "")

    @pytest.mark.asyncio
    async def test_invalid_format_returns_422(self, client):
        response = await client.post(
            "/api/v1/convert/file",
            files=_html_file(),
            params={"return_format": "xml"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/convert/clean-html
# ---------------------------------------------------------------------------


class TestConvertCleanHtmlFormat:
    """E2E tests for return_format on /api/v1/convert/clean-html.

    The endpoint accepts either a `url` Query param or a file upload.
    We use file upload to avoid real HTTP requests.
    """

    @pytest.mark.asyncio
    async def test_default_returns_json(self, client):
        response = await client.post(
            "/api/v1/convert/clean-html",
            files=_html_upload_file(),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "content" in body["data"]

    @pytest.mark.asyncio
    async def test_markdown_format(self, client):
        response = await client.post(
            "/api/v1/convert/clean-html",
            files=_html_upload_file(),
            params={"return_format": "markdown"},
        )
        assert response.status_code == 200
        assert "text/markdown" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_download_format(self, client):
        response = await client.post(
            "/api/v1/convert/clean-html",
            files=_html_upload_file(),
            params={"return_format": "download"},
        )
        assert response.status_code == 200
        assert "attachment" in response.headers.get("content-disposition", "")

    @pytest.mark.asyncio
    async def test_invalid_format_returns_422(self, client):
        response = await client.post(
            "/api/v1/convert/clean-html",
            files=_html_upload_file(),
            params={"return_format": "pdf"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/convert/url  (url is a Query param, not JSON body)
# ---------------------------------------------------------------------------


class TestConvertUrlFormat:
    """E2E tests for return_format on /api/v1/convert/url.

    Note: The `url` parameter is a Query param (not JSON body).
    We only test parameter validation here; real URL fetching is not in scope.
    """

    @pytest.mark.asyncio
    async def test_invalid_format_returns_422(self, client):
        """Invalid return_format is rejected before the URL is fetched."""
        response = await client.post(
            "/api/v1/convert/url",
            params={
                "url": "https://example.com",
                "return_format": "binary",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_valid_formats_pass_validation(self, client):
        """All three valid return_format values must pass param validation.

        The endpoint may fail for network reasons (not a test server), but it
        must NOT return 422 (which would indicate format validation failed).
        """
        for fmt in ("json", "markdown", "download"):
            response = await client.post(
                "/api/v1/convert/url",
                params={
                    "url": "https://example.com",
                    "return_format": fmt,
                },
            )
            assert response.status_code != 422, (
                f"return_format='{fmt}' was rejected by parameter validation"
            )


# ---------------------------------------------------------------------------
# POST /api/v1/convert/audio
# ---------------------------------------------------------------------------


class TestConvertAudioFormat:
    """E2E tests for return_format on /api/v1/convert/audio."""

    @pytest.mark.asyncio
    async def test_invalid_format_returns_422(self, client):
        response = await client.post(
            "/api/v1/convert/audio",
            files=_audio_file(),
            params={"return_format": "csv"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_valid_formats_pass_validation(self, client):
        for fmt in ("json", "markdown", "download"):
            response = await client.post(
                "/api/v1/convert/audio",
                files=_audio_file(),
                params={"return_format": fmt},
            )
            assert response.status_code != 422, (
                f"return_format='{fmt}' was rejected by parameter validation"
            )


# ---------------------------------------------------------------------------
# POST /api/v1/convert/video
# ---------------------------------------------------------------------------


class TestConvertVideoFormat:
    """E2E tests for return_format on /api/v1/convert/video."""

    @pytest.mark.asyncio
    async def test_invalid_format_returns_422(self, client):
        response = await client.post(
            "/api/v1/convert/video",
            files=_video_file(),
            params={"return_format": "html"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_valid_formats_pass_validation(self, client):
        for fmt in ("json", "markdown", "download"):
            response = await client.post(
                "/api/v1/convert/video",
                files=_video_file(),
                params={"return_format": fmt},
            )
            assert response.status_code != 422, (
                f"return_format='{fmt}' was rejected by parameter validation"
            )


# ---------------------------------------------------------------------------
# POST /api/v1/convert/youtube  (JSON body: {"url": "..."})
# ---------------------------------------------------------------------------


class TestConvertYoutubeFormat:
    """E2E tests for return_format on /api/v1/convert/youtube.

    Note: The `url` parameter is a Query param (not JSON body).
    """

    @pytest.mark.asyncio
    async def test_invalid_format_returns_422(self, client):
        response = await client.post(
            "/api/v1/convert/youtube",
            params={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "return_format": "text",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_valid_formats_pass_validation(self, client):
        for fmt in ("json", "markdown", "download"):
            response = await client.post(
                "/api/v1/convert/youtube",
                params={
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "return_format": fmt,
                },
            )
            assert response.status_code != 422, (
                f"return_format='{fmt}' was rejected by parameter validation"
            )


# ---------------------------------------------------------------------------
# Error responses are always JSON
# ---------------------------------------------------------------------------


class TestErrorResponseAlwaysJson:
    """Verify that server-side errors still return JSON regardless of return_format."""

    @pytest.mark.asyncio
    async def test_missing_file_returns_json_error(self, client):
        """POST without file should return a JSON 422, not raw text."""
        response = await client.post(
            "/api/v1/convert/file",
            params={"return_format": "markdown"},
        )
        assert response.status_code in (400, 422)
        # Must be parseable as JSON
        body = response.json()
        assert body is not None

    @pytest.mark.asyncio
    async def test_clean_html_no_input_returns_json_error(self, client):
        """Sending clean-html with no file/url should return a JSON error."""
        response = await client.post(
            "/api/v1/convert/clean-html",
            params={"return_format": "markdown"},
        )
        assert response.status_code in (400, 422)
        body = response.json()
        assert body is not None
