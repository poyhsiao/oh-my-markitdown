# Unified Return Format Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Standardize all `/api/v1/convert/*` endpoints to support `json` (default) | `markdown` | `download` via a unified `return_format` parameter backed by a shared helper.

**Architecture:** Add `build_convert_response()` to `api/response.py` as the single source of truth for all three output modes. Each endpoint is updated to call this helper with its own `content` string and `metadata` dict. TDD: unit tests for the helper are written first, then endpoint-level integration tests, then e2e smoke tests.

**Tech Stack:** Python 3.11+, FastAPI, pytest, pytest-asyncio, httpx (ASGI transport)

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `api/response.py` | Add `build_convert_response()` helper |
| Modify | `api/main.py` | Update 7 convert endpoints |
| Create | `tests/unit/test_build_convert_response.py` | Unit tests for the new helper |
| Modify | `tests/api/test_endpoints.py` | Integration tests for convert endpoints |
| Modify | `tests/e2e/test_audio_transcribe.py` | E2E tests updated for new envelope |
| Create | `tests/e2e/test_convert_formats.py` | E2E smoke tests for all 3 return formats |
| Modify | `docs/superpowers/specs/2026-04-11-unified-return-format-design.md` | Already exists — no change needed |

---

## Task 1: Add `build_convert_response()` to `api/response.py`

**Files:**
- Modify: `api/response.py`
- Test: `tests/unit/test_build_convert_response.py`

### Step 1.1 — Write the failing unit tests

Create `tests/unit/test_build_convert_response.py`:

```python
"""Unit tests for build_convert_response() helper — TDD RED phase."""
import pytest
from fastapi.responses import JSONResponse, Response


class TestBuildConvertResponseJson:
    """Tests for return_format='json' (default)."""

    def test_returns_json_response_by_default(self):
        from api.response import build_convert_response, set_request_id
        set_request_id("test-001")
        result = build_convert_response(
            content="# Hello",
            metadata={"source": "test.pdf"},
        )
        assert isinstance(result, JSONResponse)

    def test_json_envelope_has_success_true(self):
        from api.response import build_convert_response, set_request_id
        import json
        set_request_id("test-002")
        result = build_convert_response(content="# Hello", metadata={})
        body = json.loads(result.body)
        assert body["success"] is True

    def test_json_data_content_field(self):
        from api.response import build_convert_response, set_request_id
        import json
        set_request_id("test-003")
        result = build_convert_response(content="# Hello\nworld", metadata={"k": "v"})
        body = json.loads(result.body)
        assert body["data"]["content"] == "# Hello\nworld"

    def test_json_data_metadata_field(self):
        from api.response import build_convert_response, set_request_id
        import json
        set_request_id("test-004")
        result = build_convert_response(
            content="x",
            metadata={"source": "doc.pdf", "processing_time": 0.5},
        )
        body = json.loads(result.body)
        assert body["data"]["metadata"]["source"] == "doc.pdf"
        assert body["data"]["metadata"]["processing_time"] == 0.5

    def test_json_has_request_id(self):
        from api.response import build_convert_response, set_request_id
        import json
        set_request_id("req-abc123")
        result = build_convert_response(content="x", metadata={})
        body = json.loads(result.body)
        assert body["request_id"] == "req-abc123"

    def test_explicit_json_format(self):
        from api.response import build_convert_response, set_request_id
        import json
        set_request_id("test-005")
        result = build_convert_response(content="x", metadata={}, return_format="json")
        assert isinstance(result, JSONResponse)
        body = json.loads(result.body)
        assert body["success"] is True


class TestBuildConvertResponseMarkdown:
    """Tests for return_format='markdown'."""

    def test_returns_response_object(self):
        from api.response import build_convert_response
        result = build_convert_response(
            content="# Hello", metadata={}, return_format="markdown"
        )
        assert isinstance(result, Response)
        assert not isinstance(result, JSONResponse)

    def test_content_type_is_text_markdown(self):
        from api.response import build_convert_response
        result = build_convert_response(
            content="# Hello", metadata={}, return_format="markdown"
        )
        assert "text/markdown" in result.media_type

    def test_body_is_utf8_encoded_markdown(self):
        from api.response import build_convert_response
        md = "# 標題\n\n內文"
        result = build_convert_response(content=md, metadata={}, return_format="markdown")
        assert result.body == md.encode("utf-8")

    def test_no_content_disposition_header(self):
        from api.response import build_convert_response
        result = build_convert_response(
            content="x", metadata={}, return_format="markdown"
        )
        assert "content-disposition" not in (result.headers or {})


class TestBuildConvertResponseDownload:
    """Tests for return_format='download'."""

    def test_returns_response_object(self):
        from api.response import build_convert_response
        result = build_convert_response(
            content="# Hello", metadata={}, return_format="download"
        )
        assert isinstance(result, Response)
        assert not isinstance(result, JSONResponse)

    def test_content_type_is_text_markdown(self):
        from api.response import build_convert_response
        result = build_convert_response(
            content="x", metadata={}, return_format="download"
        )
        assert "text/markdown" in result.media_type

    def test_content_disposition_attachment(self):
        from api.response import build_convert_response
        result = build_convert_response(
            content="x",
            metadata={},
            return_format="download",
            filename="output.md",
        )
        disposition = result.headers.get("content-disposition", "")
        assert "attachment" in disposition
        assert "output.md" in disposition

    def test_custom_filename(self):
        from api.response import build_convert_response
        result = build_convert_response(
            content="x",
            metadata={},
            return_format="download",
            filename="report-2026.md",
        )
        disposition = result.headers.get("content-disposition", "")
        assert "report-2026.md" in disposition

    def test_default_filename_is_output_md(self):
        from api.response import build_convert_response
        result = build_convert_response(
            content="x", metadata={}, return_format="download"
        )
        disposition = result.headers.get("content-disposition", "")
        assert "output.md" in disposition

    def test_body_is_utf8_encoded(self):
        from api.response import build_convert_response
        md = "# 下載\n測試"
        result = build_convert_response(
            content=md, metadata={}, return_format="download"
        )
        assert result.body == md.encode("utf-8")
```

- [ ] **Step 1.2 — Run tests to confirm RED**

```bash
cd /Users/kimhsiao/Templates/git/kimhsiao/oh-my-markitdown
uv run pytest tests/unit/test_build_convert_response.py -v 2>&1 | head -40
```

Expected: `ImportError` or `AttributeError: module 'api.response' has no attribute 'build_convert_response'`

- [ ] **Step 1.3 — Implement `build_convert_response()` in `api/response.py`**

Add the following after the existing `transcribe_response()` function in `api/response.py`:

```python
from fastapi.responses import JSONResponse, Response as FastAPIResponse


def build_convert_response(
    content: str,
    metadata: Dict[str, Any],
    return_format: str = "json",
    filename: str = "output.md",
    request_id: Optional[str] = None,
) -> FastAPIResponse:
    """
    Build a unified convert API response.

    Args:
        content: Markdown string to return.
        metadata: Arbitrary metadata dict included in JSON envelope.
        return_format: "json" (default), "markdown", or "download".
        filename: Filename used in Content-Disposition for download mode.
        request_id: Request ID (defaults to context value).

    Returns:
        JSONResponse for "json", Response for "markdown"/"download".
    """
    if return_format == "markdown":
        return FastAPIResponse(
            content=content.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
        )
    elif return_format == "download":
        return FastAPIResponse(
            content=content.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    else:  # json (default)
        return JSONResponse(
            content=success_response(
                data={"content": content, "metadata": metadata},
                request_id=request_id,
            )
        )
```

Also add `JSONResponse` and `Response` to the imports at the top of `api/response.py`:

```python
from fastapi.responses import JSONResponse, Response as FastAPIResponse
```

- [ ] **Step 1.4 — Run tests to confirm GREEN**

```bash
uv run pytest tests/unit/test_build_convert_response.py -v
```

Expected: All tests PASS.

- [ ] **Step 1.5 — Commit**

```bash
git add api/response.py tests/unit/test_build_convert_response.py
git commit -m "feat: add build_convert_response() helper to api/response.py"
```

---

## Task 2: Update `/convert/file` and `/convert/convert`

**Files:**
- Modify: `api/main.py` lines ~246–499
- Test: `tests/api/test_endpoints.py`

- [ ] **Step 2.1 — Write failing integration tests**

Add the following class to `tests/api/test_endpoints.py`:

```python
class TestConvertFileReturnFormat:
    """Integration tests for /convert/file return_format parameter."""

    @pytest.mark.asyncio
    async def test_default_return_format_is_json(self, api_client):
        """Default return_format should be json."""
        import io
        content = b"# Hello"
        response = await api_client.post(
            "/api/v1/convert/file",
            files={"file": ("test.md", io.BytesIO(content), "text/markdown")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "content" in data["data"]
        assert "metadata" in data["data"]

    @pytest.mark.asyncio
    async def test_return_format_json_envelope(self, api_client):
        """return_format=json returns unified envelope."""
        import io
        content = b"# Test\nHello world"
        response = await api_client.post(
            "/api/v1/convert/file",
            files={"file": ("test.md", io.BytesIO(content), "text/markdown")},
            params={"return_format": "json"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"]["content"], str)
        assert isinstance(data["data"]["metadata"], dict)
        assert "request_id" in data

    @pytest.mark.asyncio
    async def test_return_format_markdown_content_type(self, api_client):
        """return_format=markdown returns text/markdown."""
        import io
        content = b"# Hello"
        response = await api_client.post(
            "/api/v1/convert/file",
            files={"file": ("test.md", io.BytesIO(content), "text/markdown")},
            params={"return_format": "markdown"},
        )
        assert response.status_code == 200
        assert "text/markdown" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_return_format_download_content_disposition(self, api_client):
        """return_format=download returns Content-Disposition: attachment."""
        import io
        content = b"# Hello"
        response = await api_client.post(
            "/api/v1/convert/file",
            files={"file": ("report.md", io.BytesIO(content), "text/markdown")},
            params={"return_format": "download"},
        )
        assert response.status_code == 200
        disposition = response.headers.get("content-disposition", "")
        assert "attachment" in disposition

    @pytest.mark.asyncio
    async def test_invalid_return_format_returns_422(self, api_client):
        """Invalid return_format returns 422."""
        import io
        content = b"# Hello"
        response = await api_client.post(
            "/api/v1/convert/file",
            files={"file": ("test.md", io.BytesIO(content), "text/markdown")},
            params={"return_format": "xml"},
        )
        assert response.status_code == 422
```

- [ ] **Step 2.2 — Run to confirm RED**

```bash
uv run pytest tests/api/test_endpoints.py::TestConvertFileReturnFormat -v 2>&1 | head -40
```

Expected: Tests fail because default is `"markdown"` not `"json"` and `download` mode is missing.

- [ ] **Step 2.3 — Update `/convert/file` endpoint in `api/main.py`**

Find the `convert_file_endpoint` function signature (around line 268) and change:

```python
# OLD
return_format: str = Query("markdown", description="Response format: markdown or json", pattern="^(markdown|json)$"),
```

```python
# NEW
return_format: str = Query("json", description="Response format: json (default), markdown, or download", pattern="^(json|markdown|download)$"),
```

Then replace the return block at the end of the `try` block (the section that checks `if return_format == "markdown":`) with a call to the helper. Replace this block:

```python
            if return_format == "markdown":
                # Return Markdown text directly (ensure UTF-8 encoding)
                from urllib.parse import quote
                safe_filename = quote(file.filename or "unknown", safe='')
                
                return Response(
                    content=text_content.encode('utf-8'),
                    media_type="text/markdown; charset=utf-8",
                    headers={
                        "X-Original-Filename": safe_filename,
                        "X-Conversion-Time": datetime.now().isoformat(),
                        "X-OCR-Language": ocr_lang if enable_plugins else "N/A",
                        "Content-Disposition": f'attachment; filename="converted.md"'
                    }
                )
            else:
                # Return JSON format (using unified response format)
                return convert_file_response(
                    content=text_content,
                    format="markdown",
                    filename=file.filename or "unknown",
                    file_size=len(file_content),
                    conversion_time=datetime.now().isoformat(),
                    ocr_language=ocr_lang if enable_plugins else None,
                    request_id=request_id
                )
```

With:

```python
            from .response import build_convert_response
            from pathlib import Path as _Path
            stem = _Path(file.filename or "converted").stem
            return build_convert_response(
                content=text_content,
                metadata={
                    "filename": file.filename or "unknown",
                    "file_size": len(file_content),
                    "conversion_time": datetime.now().isoformat(),
                    "ocr_language": ocr_lang if enable_plugins else None,
                    "format": "markdown",
                },
                return_format=return_format,
                filename=f"{stem}.md",
                request_id=request_id,
            )
```

- [ ] **Step 2.4 — Run tests to confirm GREEN**

```bash
uv run pytest tests/api/test_endpoints.py::TestConvertFileReturnFormat -v
```

Expected: All 5 tests PASS.

- [ ] **Step 2.5 — Commit**

```bash
git add api/main.py tests/api/test_endpoints.py
git commit -m "feat: unify return_format for /convert/file (json default + download support)"
```

---

## Task 3: Update `/convert/audio`

**Files:**
- Modify: `api/main.py` lines ~652–746
- Test: `tests/api/test_endpoints.py`

- [ ] **Step 3.1 — Write failing integration tests**

Add to `tests/api/test_endpoints.py`:

```python
class TestConvertAudioReturnFormat:
    """Integration tests for /convert/audio return_format parameter."""

    @pytest.mark.asyncio
    async def test_default_is_json(self, api_client):
        """Default return_format should be json, not markdown."""
        with patch("api.main.transcribe_audio_chunked") as mock_t, \
             patch("api.main.format_transcript_as_markdown") as mock_f:
            mock_t.return_value = ("transcript text", {"duration": 5.0, "language": "zh"})
            mock_f.return_value = "# Audio\n\ntranscript text"
            import io
            response = await api_client.post(
                "/api/v1/convert/audio",
                files={"file": ("test.wav", io.BytesIO(b"RIFF"), "audio/wav")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "content" in data["data"]
        assert "metadata" in data["data"]

    @pytest.mark.asyncio
    async def test_return_format_json_has_rich_metadata(self, api_client):
        """JSON format includes language, duration, model in metadata."""
        with patch("api.main.transcribe_audio_chunked") as mock_t, \
             patch("api.main.format_transcript_as_markdown") as mock_f:
            mock_t.return_value = ("transcript", {"duration": 10.0, "language": "en", "model": "base"})
            mock_f.return_value = "# Title\n\ntranscript"
            import io
            response = await api_client.post(
                "/api/v1/convert/audio",
                files={"file": ("speech.wav", io.BytesIO(b"RIFF"), "audio/wav")},
                params={"return_format": "json", "language": "en", "model_size": "base"},
            )
        assert response.status_code == 200
        data = response.json()
        meta = data["data"]["metadata"]
        assert "duration" in meta
        assert "language" in meta

    @pytest.mark.asyncio
    async def test_return_format_markdown(self, api_client):
        """return_format=markdown returns text/markdown."""
        with patch("api.main.transcribe_audio_chunked") as mock_t, \
             patch("api.main.format_transcript_as_markdown") as mock_f:
            mock_t.return_value = ("text", {})
            mock_f.return_value = "# T\n\ntext"
            import io
            response = await api_client.post(
                "/api/v1/convert/audio",
                files={"file": ("a.wav", io.BytesIO(b"RIFF"), "audio/wav")},
                params={"return_format": "markdown"},
            )
        assert response.status_code == 200
        assert "text/markdown" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_return_format_download(self, api_client):
        """return_format=download returns Content-Disposition: attachment."""
        with patch("api.main.transcribe_audio_chunked") as mock_t, \
             patch("api.main.format_transcript_as_markdown") as mock_f:
            mock_t.return_value = ("text", {})
            mock_f.return_value = "# T\n\ntext"
            import io
            response = await api_client.post(
                "/api/v1/convert/audio",
                files={"file": ("speech.wav", io.BytesIO(b"RIFF"), "audio/wav")},
                params={"return_format": "download"},
            )
        assert response.status_code == 200
        disposition = response.headers.get("content-disposition", "")
        assert "attachment" in disposition

    @pytest.mark.asyncio
    async def test_invalid_return_format_returns_422(self, api_client):
        """Invalid return_format returns 422."""
        import io
        response = await api_client.post(
            "/api/v1/convert/audio",
            files={"file": ("a.wav", io.BytesIO(b"RIFF"), "audio/wav")},
            params={"return_format": "xml"},
        )
        assert response.status_code == 422
```

- [ ] **Step 3.2 — Run to confirm RED**

```bash
uv run pytest tests/api/test_endpoints.py::TestConvertAudioReturnFormat -v 2>&1 | head -40
```

Expected: `test_default_is_json` fails (currently returns `text/markdown`).

- [ ] **Step 3.3 — Update `/convert/audio` in `api/main.py`**

Change the function signature (around line 652):

```python
# OLD
return_format: str = Query("markdown", description="Response format: markdown or json"),
```

```python
# NEW
return_format: str = Query("json", description="Response format: json (default), markdown, or download", pattern="^(json|markdown|download)$"),
```

Replace the return block inside the `try` block (after `markdown_content = format_transcript_as_markdown(...)`):

```python
# OLD
            if return_format == "markdown":
                return Response(
                    content=markdown_content.encode('utf-8'),
                    media_type="text/markdown; charset=utf-8",
                    headers={
                        "X-Filename": safe_filename,
                        "X-Conversion-Time": datetime.now().isoformat()
                    }
                )
            else:
                return {
                    "success": True,
                    "filename": file.filename,
                    "transcript": transcript,
                    "metadata": metadata,
                    "markdown": markdown_content
                }
```

```python
# NEW
            from .response import build_convert_response
            from pathlib import Path as _Path
            stem = _Path(file.filename or "audio").stem
            return build_convert_response(
                content=markdown_content,
                metadata={
                    "source": file.filename or "unknown",
                    "language": metadata.get("language", language),
                    "duration": metadata.get("duration"),
                    "model": metadata.get("model", model_size),
                    "segments": metadata.get("segments", []),
                    "processing_time": metadata.get("processing_time"),
                },
                return_format=return_format,
                filename=f"{stem}.md",
            )
```

- [ ] **Step 3.4 — Run tests to confirm GREEN**

```bash
uv run pytest tests/api/test_endpoints.py::TestConvertAudioReturnFormat -v
```

Expected: All 5 tests PASS.

- [ ] **Step 3.5 — Commit**

```bash
git add api/main.py tests/api/test_endpoints.py
git commit -m "feat: unify return_format for /convert/audio (json default + download support)"
```

---

## Task 4: Fix `/convert/video` (return_format was silently ignored)

**Files:**
- Modify: `api/main.py` lines ~749–855
- Test: `tests/api/test_endpoints.py`

- [ ] **Step 4.1 — Write failing integration tests**

Add to `tests/api/test_endpoints.py`:

```python
class TestConvertVideoReturnFormat:
    """Integration tests for /convert/video return_format parameter."""

    @pytest.mark.asyncio
    async def test_default_is_json(self, api_client):
        """Default return_format should be json."""
        with patch("api.main.extract_audio_from_video") as mock_e, \
             patch("api.main.transcribe_audio_chunked") as mock_t, \
             patch("api.main.format_transcript_as_markdown") as mock_f:
            mock_e.return_value = "/tmp/fake_audio.wav"
            mock_t.return_value = ("transcript", {"duration": 30.0, "language": "zh"})
            mock_f.return_value = "# Video\n\ntranscript"
            import io
            response = await api_client.post(
                "/api/v1/convert/video",
                files={"file": ("test.mp4", io.BytesIO(b"fake"), "video/mp4")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "content" in data["data"]

    @pytest.mark.asyncio
    async def test_return_format_json_has_metadata(self, api_client):
        """JSON format includes source, language, duration in metadata."""
        with patch("api.main.extract_audio_from_video") as mock_e, \
             patch("api.main.transcribe_audio_chunked") as mock_t, \
             patch("api.main.format_transcript_as_markdown") as mock_f:
            mock_e.return_value = "/tmp/fake_audio.wav"
            mock_t.return_value = ("transcript", {"duration": 30.0, "language": "zh", "model": "base"})
            mock_f.return_value = "# Video\n\ntranscript"
            import io
            response = await api_client.post(
                "/api/v1/convert/video",
                files={"file": ("clip.mp4", io.BytesIO(b"fake"), "video/mp4")},
                params={"return_format": "json"},
            )
        assert response.status_code == 200
        data = response.json()
        meta = data["data"]["metadata"]
        assert "duration" in meta
        assert "language" in meta

    @pytest.mark.asyncio
    async def test_return_format_markdown(self, api_client):
        """return_format=markdown returns text/markdown content-type."""
        with patch("api.main.extract_audio_from_video") as mock_e, \
             patch("api.main.transcribe_audio_chunked") as mock_t, \
             patch("api.main.format_transcript_as_markdown") as mock_f:
            mock_e.return_value = "/tmp/fake_audio.wav"
            mock_t.return_value = ("t", {})
            mock_f.return_value = "# T\n\nt"
            import io
            response = await api_client.post(
                "/api/v1/convert/video",
                files={"file": ("v.mp4", io.BytesIO(b"fake"), "video/mp4")},
                params={"return_format": "markdown"},
            )
        assert response.status_code == 200
        assert "text/markdown" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_return_format_download(self, api_client):
        """return_format=download returns Content-Disposition: attachment."""
        with patch("api.main.extract_audio_from_video") as mock_e, \
             patch("api.main.transcribe_audio_chunked") as mock_t, \
             patch("api.main.format_transcript_as_markdown") as mock_f:
            mock_e.return_value = "/tmp/fake_audio.wav"
            mock_t.return_value = ("t", {})
            mock_f.return_value = "# T\n\nt"
            import io
            response = await api_client.post(
                "/api/v1/convert/video",
                files={"file": ("clip.mp4", io.BytesIO(b"fake"), "video/mp4")},
                params={"return_format": "download"},
            )
        assert response.status_code == 200
        assert "attachment" in response.headers.get("content-disposition", "")
```

- [ ] **Step 4.2 — Run to confirm RED**

```bash
uv run pytest tests/api/test_endpoints.py::TestConvertVideoReturnFormat -v 2>&1 | head -40
```

Expected: `test_default_is_json` fails (currently always returns `text/markdown`).

- [ ] **Step 4.3 — Update `/convert/video` in `api/main.py`**

Change the function signature (around line 749):

```python
# OLD
return_format: str = Query("markdown", description="Response format: markdown or json"),
```

```python
# NEW
return_format: str = Query("json", description="Response format: json (default), markdown, or download", pattern="^(json|markdown|download)$"),
```

Replace the return block (the `return Response(...)` after `markdown_content = format_transcript_as_markdown(...)`):

```python
# OLD
            return Response(
                content=markdown_content.encode('utf-8'),
                media_type="text/markdown; charset=utf-8",
                headers={
                    "X-Filename": safe_filename,
                    "X-Source": "video",
                    "X-Language": language,
                    "X-Model": model_size
                }
            )
```

```python
# NEW
            from .response import build_convert_response
            from pathlib import Path as _Path
            stem = _Path(file.filename or "video").stem
            return build_convert_response(
                content=markdown_content,
                metadata={
                    "source": file.filename or "unknown",
                    "language": metadata.get("language", language),
                    "duration": metadata.get("duration"),
                    "model": metadata.get("model", model_size),
                    "segments": metadata.get("segments", []),
                    "processing_time": metadata.get("processing_time"),
                },
                return_format=return_format,
                filename=f"{stem}.md",
            )
```

Also update the error handling at the bottom of the function — change:

```python
# OLD
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Video transcription failed: {str(e)}"
        )
```

```python
# NEW
    except HTTPException:
        raise
    except Exception as e:
        from .response import error_response, ErrorCodes
        raise HTTPException(
            status_code=500,
            detail=error_response(
                code=ErrorCodes.INTERNAL_ERROR,
                message=f"Video transcription failed: {str(e)}",
            ),
        )
```

- [ ] **Step 4.4 — Run tests to confirm GREEN**

```bash
uv run pytest tests/api/test_endpoints.py::TestConvertVideoReturnFormat -v
```

Expected: All 4 tests PASS.

- [ ] **Step 4.5 — Commit**

```bash
git add api/main.py tests/api/test_endpoints.py
git commit -m "fix: /convert/video now respects return_format (json default + download support)"
```

---

## Task 5: Fix `/convert/youtube`

**Files:**
- Modify: `api/main.py` lines ~525–649
- Test: `tests/api/test_endpoints.py`

- [ ] **Step 5.1 — Write failing integration tests**

Add to `tests/api/test_endpoints.py`:

```python
class TestConvertYoutubeReturnFormat:
    """Integration tests for /convert/youtube return_format parameter."""

    @pytest.mark.asyncio
    async def test_default_is_json(self, api_client):
        """Default return_format should be json (was 'json' but returned bare dict)."""
        with patch("api.main.transcribe_youtube_video") as mock_y, \
             patch("api.main.format_transcript_as_markdown") as mock_f:
            mock_y.return_value = {
                "title": "Test Video",
                "transcript": "Hello world",
                "metadata": {"duration": 60.0, "language": "en"},
            }
            mock_f.return_value = "# Test Video\n\nHello world"
            response = await api_client.post(
                "/api/v1/convert/youtube",
                params={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "content" in data["data"]
        assert "metadata" in data["data"]

    @pytest.mark.asyncio
    async def test_json_metadata_has_rich_fields(self, api_client):
        """JSON metadata includes title, duration, language, segments."""
        with patch("api.main.transcribe_youtube_video") as mock_y, \
             patch("api.main.format_transcript_as_markdown") as mock_f:
            mock_y.return_value = {
                "title": "My Video",
                "transcript": "transcript",
                "metadata": {"duration": 120.0, "language": "zh", "model": "base"},
            }
            mock_f.return_value = "# My Video\n\ntranscript"
            response = await api_client.post(
                "/api/v1/convert/youtube",
                params={"url": "https://youtu.be/abc123", "return_format": "json"},
            )
        assert response.status_code == 200
        data = response.json()
        meta = data["data"]["metadata"]
        assert "title" in meta
        assert "duration" in meta
        assert "language" in meta

    @pytest.mark.asyncio
    async def test_return_format_markdown(self, api_client):
        """return_format=markdown returns text/markdown."""
        with patch("api.main.transcribe_youtube_video") as mock_y, \
             patch("api.main.format_transcript_as_markdown") as mock_f:
            mock_y.return_value = {"title": "T", "transcript": "t", "metadata": {}}
            mock_f.return_value = "# T\n\nt"
            response = await api_client.post(
                "/api/v1/convert/youtube",
                params={"url": "https://youtu.be/x", "return_format": "markdown"},
            )
        assert response.status_code == 200
        assert "text/markdown" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_return_format_download(self, api_client):
        """return_format=download returns Content-Disposition: attachment."""
        with patch("api.main.transcribe_youtube_video") as mock_y, \
             patch("api.main.format_transcript_as_markdown") as mock_f:
            mock_y.return_value = {"title": "My Vid", "transcript": "t", "metadata": {}}
            mock_f.return_value = "# My Vid\n\nt"
            response = await api_client.post(
                "/api/v1/convert/youtube",
                params={"url": "https://youtu.be/x", "return_format": "download"},
            )
        assert response.status_code == 200
        assert "attachment" in response.headers.get("content-disposition", "")
```

- [ ] **Step 5.2 — Run to confirm RED**

```bash
uv run pytest tests/api/test_endpoints.py::TestConvertYoutubeReturnFormat -v 2>&1 | head -40
```

Expected: `test_default_is_json` fails (returns bare dict without `success` key).

- [ ] **Step 5.3 — Update `/convert/youtube` in `api/main.py`**

Change the function signature (around line 525):

```python
# OLD
return_format: str = Query("json", description="Response format: json or markdown"),
```

```python
# NEW
return_format: str = Query("json", description="Response format: json (default), markdown, or download", pattern="^(json|markdown|download)$"),
```

Replace the return block after `markdown_content = format_transcript_as_markdown(...)`:

```python
# OLD
        if return_format == "markdown":
            return Response(
                content=markdown_content.encode('utf-8'),
                media_type="text/markdown; charset=utf-8",
                headers={
                    "X-Source-URL": url,
                    "X-Conversion-Time": datetime.now().isoformat(),
                    "X-Transcript-Length": str(len(result["transcript"]))
                }
            )
        else:
            return {
                "success": True,
                "url": url,
                "title": result["title"],
                "transcript": result["transcript"],
                "metadata": result["metadata"],
                "markdown": markdown_content
            }
```

```python
# NEW
        from .response import build_convert_response
        import re as _re
        safe_title = _re.sub(r'[^\w\-_. ]', '_', result["title"])[:60] or "youtube"
        return build_convert_response(
            content=markdown_content,
            metadata={
                "source": url,
                "title": result["title"],
                "language": result["metadata"].get("language", language),
                "duration": result["metadata"].get("duration"),
                "model": model_size,
                "segments": result["metadata"].get("segments", []),
                "processing_time": result["metadata"].get("processing_time"),
            },
            return_format=return_format,
            filename=f"{safe_title}.md",
        )
```

- [ ] **Step 5.4 — Run tests to confirm GREEN**

```bash
uv run pytest tests/api/test_endpoints.py::TestConvertYoutubeReturnFormat -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5.5 — Commit**

```bash
git add api/main.py tests/api/test_endpoints.py
git commit -m "feat: unify return_format for /convert/youtube (json default, fix bare dict)"
```

---

## Task 6: Update `/convert/url`

**Files:**
- Modify: `api/main.py` lines ~1269–1690
- Test: `tests/api/test_endpoints.py`

- [ ] **Step 6.1 — Write failing integration tests**

Add to `tests/api/test_endpoints.py`:

```python
class TestConvertUrlReturnFormat:
    """Integration tests for /convert/url return_format parameter."""

    @pytest.mark.asyncio
    async def test_default_is_json_for_document_url(self, api_client):
        """Default return_format for URL document conversion should be json."""
        with patch("api.main.detect_url_type") as mock_d, \
             patch("api.main.requests") as mock_r, \
             patch("api.main.md") as mock_md:
            mock_d.return_value = ("document", {})
            mock_resp = MagicMock()
            mock_resp.iter_content.return_value = [b"# Hello"]
            mock_resp.headers = {"Content-Type": "application/pdf"}
            mock_r.get.return_value = mock_resp
            mock_md.convert.return_value = MagicMock(text_content="# Hello")
            response = await api_client.post(
                "/api/v1/convert/url",
                params={"url": "https://example.com/doc.pdf"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "content" in data["data"]

    @pytest.mark.asyncio
    async def test_return_format_download(self, api_client):
        """return_format=download returns Content-Disposition: attachment."""
        with patch("api.main.detect_url_type") as mock_d, \
             patch("api.main.requests") as mock_r, \
             patch("api.main.md") as mock_md:
            mock_d.return_value = ("document", {})
            mock_resp = MagicMock()
            mock_resp.iter_content.return_value = [b"# Hello"]
            mock_resp.headers = {"Content-Type": "application/pdf"}
            mock_r.get.return_value = mock_resp
            mock_md.convert.return_value = MagicMock(text_content="# Hello")
            response = await api_client.post(
                "/api/v1/convert/url",
                params={"url": "https://example.com/doc.pdf", "return_format": "download"},
            )
        assert response.status_code == 200
        assert "attachment" in response.headers.get("content-disposition", "")
```

- [ ] **Step 6.2 — Run to confirm RED**

```bash
uv run pytest tests/api/test_endpoints.py::TestConvertUrlReturnFormat -v 2>&1 | head -30
```

Expected: Tests fail since `/convert/url` has no `return_format` parameter.

- [ ] **Step 6.3 — Add `return_format` to `/convert/url` in `api/main.py`**

Add to the function signature (around line 1269):

```python
    return_format: str = Query("json", description="Response format: json (default), markdown, or download", pattern="^(json|markdown|download)$"),
```

Then find every `return convert_file_response(...)` and `return transcribe_response(...)` call in this function and replace them all with `build_convert_response()`. There are multiple branches (document, audio, video, image, youtube, webpage). For the `document` branch, replace:

```python
                return convert_file_response(
                    content=text_content,
                    format="markdown",
                    filename=filename,
                    file_size=os.path.getsize(tmp_path),
                    conversion_time=datetime.now().isoformat(),
                    ocr_language=ocr_lang,
                    request_id=request_id
                )
```

With:

```python
                from .response import build_convert_response
                from pathlib import Path as _Path
                stem = _Path(filename).stem
                return build_convert_response(
                    content=text_content,
                    metadata={
                        "source": url,
                        "filename": filename,
                        "file_size": os.path.getsize(tmp_path),
                        "conversion_time": datetime.now().isoformat(),
                        "ocr_language": ocr_lang,
                        "format": "markdown",
                    },
                    return_format=return_format,
                    filename=f"{stem}.md",
                    request_id=request_id,
                )
```

For any other branch that returns `transcribe_response(...)` or another dict, apply equivalent wrapping using `build_convert_response()` with the markdown content and appropriate metadata.

- [ ] **Step 6.4 — Run tests to confirm GREEN**

```bash
uv run pytest tests/api/test_endpoints.py::TestConvertUrlReturnFormat -v
```

Expected: All tests PASS.

- [ ] **Step 6.5 — Commit**

```bash
git add api/main.py tests/api/test_endpoints.py
git commit -m "feat: add return_format to /convert/url (json default + download support)"
```

---

## Task 7: Add `return_format` to `/convert/clean-html`

**Files:**
- Modify: `api/main.py` lines ~1691–1780
- Test: `tests/api/test_endpoints.py`

- [ ] **Step 7.1 — Write failing integration tests**

Add to `tests/api/test_endpoints.py`:

```python
class TestConvertCleanHtmlReturnFormat:
    """Integration tests for /convert/clean-html return_format parameter."""

    @pytest.mark.asyncio
    async def test_default_is_json(self, api_client):
        """Default return_format should be json."""
        with patch("api.main._html_to_markdown") as mock_h:
            mock_h.return_value = "# Title\n\nCleaned content"
            import io
            response = await api_client.post(
                "/api/v1/convert/clean-html",
                files={"file": ("page.html", io.BytesIO(b"<html><body>hi</body></html>"), "text/html")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "content" in data["data"]

    @pytest.mark.asyncio
    async def test_return_format_markdown(self, api_client):
        """return_format=markdown returns text/markdown."""
        with patch("api.main._html_to_markdown") as mock_h:
            mock_h.return_value = "# Title\n\ncontent"
            import io
            response = await api_client.post(
                "/api/v1/convert/clean-html",
                files={"file": ("page.html", io.BytesIO(b"<html><body>hi</body></html>"), "text/html")},
                params={"return_format": "markdown"},
            )
        assert response.status_code == 200
        assert "text/markdown" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_return_format_download(self, api_client):
        """return_format=download returns Content-Disposition: attachment."""
        with patch("api.main._html_to_markdown") as mock_h:
            mock_h.return_value = "# Title\n\ncontent"
            import io
            response = await api_client.post(
                "/api/v1/convert/clean-html",
                files={"file": ("page.html", io.BytesIO(b"<html><body>hi</body></html>"), "text/html")},
                params={"return_format": "download"},
            )
        assert response.status_code == 200
        assert "attachment" in response.headers.get("content-disposition", "")

    @pytest.mark.asyncio
    async def test_invalid_return_format_returns_422(self, api_client):
        """Invalid return_format returns 422."""
        import io
        response = await api_client.post(
            "/api/v1/convert/clean-html",
            files={"file": ("page.html", io.BytesIO(b"<html></html>"), "text/html")},
            params={"return_format": "pdf"},
        )
        assert response.status_code == 422
```

- [ ] **Step 7.2 — Run to confirm RED**

```bash
uv run pytest tests/api/test_endpoints.py::TestConvertCleanHtmlReturnFormat -v 2>&1 | head -30
```

Expected: `test_default_is_json` fails since endpoint has no `return_format` parameter.

- [ ] **Step 7.3 — Update `/convert/clean-html` in `api/main.py`**

Add `return_format` to the function signature (around line 1691):

```python
async def convert_clean_html(
    url: Optional[str] = Query(None, description="URL to fetch and clean"),
    file: Optional[UploadFile] = File(None, description="HTML file to clean"),
    return_format: str = Query("json", description="Response format: json (default), markdown, or download", pattern="^(json|markdown|download)$"),
):
```

Replace the final return call `return convert_file_response(...)` with:

```python
        from .response import build_convert_response
        return build_convert_response(
            content=markdown_content,
            metadata={
                "source": url or (file.filename if file else "upload"),
                "file_size": len(html_content),
                "conversion_time": datetime.now().isoformat(),
                "format": "markdown",
            },
            return_format=return_format,
            filename="cleaned.md",
            request_id=request_id,
        )
```

- [ ] **Step 7.4 — Run tests to confirm GREEN**

```bash
uv run pytest tests/api/test_endpoints.py::TestConvertCleanHtmlReturnFormat -v
```

Expected: All 4 tests PASS.

- [ ] **Step 7.5 — Commit**

```bash
git add api/main.py tests/api/test_endpoints.py
git commit -m "feat: add return_format to /convert/clean-html (json default + download support)"
```

---

## Task 8: E2E smoke tests for all three return formats

**Files:**
- Create: `tests/e2e/test_convert_formats.py`

- [ ] **Step 8.1 — Create the E2E test file**

Create `tests/e2e/test_convert_formats.py`:

```python
"""
E2E smoke tests for unified return_format across all convert endpoints.

These tests use real ASGI transport (no mocks). They use lightweight
inputs (plain text / tiny markdown files) to avoid Whisper/OCR dependencies.
Audio/video tests are skipped when fixtures are absent.
"""
import io
import pytest
from pathlib import Path

pytestmark = pytest.mark.e2e

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestReturnFormatJson:
    """All convert endpoints return unified JSON envelope by default."""

    @pytest.mark.asyncio
    async def test_convert_file_json_default(self, api_client):
        """POST /convert/file — default returns JSON envelope."""
        content = b"# Hello\n\nWorld"
        response = await api_client.post(
            "/api/v1/convert/file",
            files={"file": ("test.md", io.BytesIO(content), "text/markdown")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"]["content"], str)
        assert isinstance(data["data"]["metadata"], dict)
        assert "request_id" in data

    @pytest.mark.asyncio
    async def test_convert_clean_html_json_default(self, api_client):
        """POST /convert/clean-html — default returns JSON envelope."""
        html = b"<html><body><h1>Title</h1><p>Content</p></body></html>"
        response = await api_client.post(
            "/api/v1/convert/clean-html",
            files={"file": ("page.html", io.BytesIO(html), "text/html")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"]["content"], str)
        assert "request_id" in data

    @pytest.mark.asyncio
    async def test_convert_audio_json_default(self, api_client):
        """POST /convert/audio — default returns JSON envelope (skip if no fixture)."""
        audio_path = FIXTURES_DIR / "5s_speech.wav"
        if not audio_path.exists():
            pytest.skip("Audio fixture not found")
        with open(audio_path, "rb") as f:
            response = await api_client.post(
                "/api/v1/convert/audio",
                files={"file": ("5s_speech.wav", f, "audio/wav")},
                params={"language": "en", "model_size": "tiny"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "content" in data["data"]
        assert "metadata" in data["data"]


class TestReturnFormatMarkdown:
    """return_format=markdown returns raw text/markdown stream."""

    @pytest.mark.asyncio
    async def test_convert_file_markdown_content_type(self, api_client):
        """POST /convert/file?return_format=markdown — Content-Type: text/markdown."""
        content = b"# Hello\n\nWorld"
        response = await api_client.post(
            "/api/v1/convert/file",
            files={"file": ("test.md", io.BytesIO(content), "text/markdown")},
            params={"return_format": "markdown"},
        )
        assert response.status_code == 200
        assert "text/markdown" in response.headers.get("content-type", "")
        assert len(response.text) > 0

    @pytest.mark.asyncio
    async def test_convert_clean_html_markdown_content_type(self, api_client):
        """POST /convert/clean-html?return_format=markdown — Content-Type: text/markdown."""
        html = b"<html><body><h1>Title</h1><p>Content</p></body></html>"
        response = await api_client.post(
            "/api/v1/convert/clean-html",
            files={"file": ("page.html", io.BytesIO(html), "text/html")},
            params={"return_format": "markdown"},
        )
        assert response.status_code == 200
        assert "text/markdown" in response.headers.get("content-type", "")


class TestReturnFormatDownload:
    """return_format=download returns Content-Disposition: attachment."""

    @pytest.mark.asyncio
    async def test_convert_file_download_disposition(self, api_client):
        """POST /convert/file?return_format=download — Content-Disposition: attachment."""
        content = b"# Report\n\nData"
        response = await api_client.post(
            "/api/v1/convert/file",
            files={"file": ("report.md", io.BytesIO(content), "text/markdown")},
            params={"return_format": "download"},
        )
        assert response.status_code == 200
        disposition = response.headers.get("content-disposition", "")
        assert "attachment" in disposition
        assert ".md" in disposition

    @pytest.mark.asyncio
    async def test_convert_clean_html_download_disposition(self, api_client):
        """POST /convert/clean-html?return_format=download — Content-Disposition: attachment."""
        html = b"<html><body><h1>Title</h1></body></html>"
        response = await api_client.post(
            "/api/v1/convert/clean-html",
            files={"file": ("page.html", io.BytesIO(html), "text/html")},
            params={"return_format": "download"},
        )
        assert response.status_code == 200
        assert "attachment" in response.headers.get("content-disposition", "")


class TestReturnFormatValidation:
    """Invalid return_format values are rejected with 422."""

    @pytest.mark.asyncio
    async def test_convert_file_invalid_format(self, api_client):
        content = b"# Hello"
        response = await api_client.post(
            "/api/v1/convert/file",
            files={"file": ("test.md", io.BytesIO(content), "text/markdown")},
            params={"return_format": "xml"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_convert_clean_html_invalid_format(self, api_client):
        html = b"<html><body></body></html>"
        response = await api_client.post(
            "/api/v1/convert/clean-html",
            files={"file": ("p.html", io.BytesIO(html), "text/html")},
            params={"return_format": "csv"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_convert_audio_invalid_format(self, api_client):
        response = await api_client.post(
            "/api/v1/convert/audio",
            files={"file": ("a.wav", io.BytesIO(b"RIFF"), "audio/wav")},
            params={"return_format": "html"},
        )
        assert response.status_code == 422


class TestErrorsAlwaysJson:
    """Errors always return JSON regardless of return_format."""

    @pytest.mark.asyncio
    async def test_unsupported_file_type_returns_json_error(self, api_client):
        """File type error returns JSON even with return_format=markdown."""
        response = await api_client.post(
            "/api/v1/convert/file",
            files={"file": ("test.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
            params={"return_format": "markdown"},
        )
        assert response.status_code in (400, 422)
        # Should always be JSON even when requesting markdown
        data = response.json()
        assert "success" in data or "detail" in data
```

- [ ] **Step 8.2 — Run E2E tests to confirm they pass**

```bash
uv run pytest tests/e2e/test_convert_formats.py -v -k "not audio"
```

Expected: All non-audio tests PASS.

- [ ] **Step 8.3 — Also update existing E2E audio test expectations**

In `tests/e2e/test_audio_transcribe.py`, update `test_transcribe_with_json_format`:

```python
    @pytest.mark.asyncio
    async def test_transcribe_with_json_format(self, api_client):
        """Test transcription with JSON return format returns unified envelope."""
        audio_path = FIXTURES_DIR / "5s_speech.wav"
        if not audio_path.exists():
            pytest.skip("Test fixture not found")

        with open(audio_path, "rb") as f:
            response = await api_client.post(
                "/api/v1/convert/audio",
                files={"file": ("5s_speech.wav", f, "audio/wav")},
                params={"language": "en", "model_size": "tiny", "return_format": "json"},
            )

        assert response.status_code == 200
        data = response.json()
        # New unified envelope
        assert data["success"] is True
        assert "content" in data["data"]
        assert "metadata" in data["data"]
        assert isinstance(data["data"]["content"], str)
```

- [ ] **Step 8.4 — Commit**

```bash
git add tests/e2e/test_convert_formats.py tests/e2e/test_audio_transcribe.py
git commit -m "test: add e2e smoke tests for unified return_format across all convert endpoints"
```

---

## Task 9: Full test suite run and version bump

- [ ] **Step 9.1 — Run all unit tests**

```bash
uv run pytest tests/unit/ -v --tb=short 2>&1 | tail -20
```

Expected: All existing unit tests PASS.

- [ ] **Step 9.2 — Run all integration + API tests**

```bash
uv run pytest tests/api/ tests/unit/test_build_convert_response.py -v --tb=short 2>&1 | tail -30
```

Expected: All tests PASS.

- [ ] **Step 9.3 — Run E2E tests (excluding fixtures-dependent)**

```bash
uv run pytest tests/e2e/test_convert_formats.py -v -k "not audio" --tb=short
```

Expected: All tests PASS.

- [ ] **Step 9.4 — Bump version to v0.8.0**

In `pyproject.toml`, find and update:

```toml
# OLD
version = "0.7.x"
```

```toml
# NEW
version = "0.8.0"
```

- [ ] **Step 9.5 — Commit and tag**

```bash
git add pyproject.toml
git commit -m "chore: bump version to v0.8.0 — unified return_format for all convert APIs"
git tag v0.8.0
```

---

## Self-Review

### Spec Coverage Check

| Spec Requirement | Covered By |
|---|---|
| All 7 endpoints support `json`/`markdown`/`download` | Tasks 2–7 |
| Default is `json` everywhere | Tasks 2–7 (signature change) |
| `data.content` + `data.metadata` structure | Task 1 (helper) |
| Transcription metadata: `segments`, `duration`, `language`, `model` | Tasks 3, 4, 5 |
| `filename` in download mode | Task 1 (helper), per-endpoint stem |
| Errors always JSON | Task 4 (video error fix), all tests |
| `pattern="^(json\|markdown\|download)$"` on all endpoints | Tasks 2–7 |
| Unit tests for helper | Task 1 |
| Integration tests per endpoint | Tasks 2–7 |
| E2E tests for all 3 modes | Task 8 |
| Version bump to v0.8.0 | Task 9 |

### Placeholder Scan

✅ No TBD, TODO, or "implement later" found.

### Type Consistency

- `build_convert_response()` defined in Task 1, called in Tasks 2–7 with identical signature.
- `metadata` is always `Dict[str, Any]` — consistent across all callers.
- `return_format` pattern `^(json|markdown|download)$` applied identically in all 7 endpoints.
