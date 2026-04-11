# Unified Return Format Design

**Date:** 2026-04-11
**Status:** Approved
**Scope:** All `/api/v1/convert/*` endpoints

## Problem Statement

The current convert API endpoints have inconsistent response formats:

- Some endpoints return `Response(text/markdown)` regardless of `return_format` parameter
- `/convert/video` has a `return_format` parameter that is silently ignored
- `/convert/youtube` returns a bare `dict` instead of the unified `success_response()` envelope
- `/convert/clean-html` has no `return_format` parameter at all
- Default values are inconsistent (`/convert/youtube` defaults to `"json"`, others to `"markdown"`)
- Some endpoints lack regex validation on `return_format`
- Error handling is mixed between `HTTPException` and `error_response()`

## Goals

1. All convert endpoints support three `return_format` values: `json`, `markdown`, `download`
2. Default `return_format` is `json` across all endpoints
3. JSON response uses a unified `data.content` + `data.metadata` structure
4. Transcription endpoints (`youtube`, `audio`, `video`) include rich metadata in `data.metadata`
5. Errors always return JSON regardless of `return_format`
6. All endpoints use `pattern="^(json|markdown|download)$"` validation

## Return Format Specification

### `return_format` Values

| Value | Content-Type | Behavior |
|-------|-------------|----------|
| `json` (default) | `application/json` | Unified envelope with `data.content` + `data.metadata` |
| `markdown` | `text/markdown; charset=utf-8` | Raw Markdown text stream |
| `download` | `text/markdown; charset=utf-8` | Markdown with `Content-Disposition: attachment; filename="{filename}"` |

### JSON Envelope Structure

**Document conversion** (`/convert/file`, `/convert/url`, `/convert/clean-html`):

```json
{
  "success": true,
  "data": {
    "content": "# Title\n\nBody...",
    "metadata": {
      "source": "document.pdf",
      "format": "markdown",
      "processing_time": 0.52
    }
  },
  "request_id": "req-abc123"
}
```

**Transcription** (`/convert/youtube`, `/convert/audio`, `/convert/video`):

```json
{
  "success": true,
  "data": {
    "content": "# Video Title\n\nTranscript...",
    "metadata": {
      "source": "https://youtube.com/...",
      "language": "zh",
      "duration": 182.5,
      "model": "base",
      "segments": [
        { "start": 0.0, "end": 3.2, "text": "Hello" }
      ],
      "processing_time": 12.3
    }
  },
  "request_id": "req-abc123"
}
```

## Architecture

### New Helper: `build_convert_response()`

Add to `api/response.py`:

```python
def build_convert_response(
    content: str,
    metadata: dict,
    return_format: str = "json",
    filename: str = "output.md",
    request_id: str | None = None,
) -> Response:
    if return_format == "markdown":
        return Response(
            content=content.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
        )
    elif return_format == "download":
        return Response(
            content=content.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
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

### Unified Parameter Definition

All convert endpoints use the same `return_format` parameter definition:

```python
return_format: str = Query(
    "json",
    description="Response format: json (default), markdown, or download",
    pattern="^(json|markdown|download)$"
)
```

### Endpoint Changes

| Endpoint | Changes | `filename` Default |
|----------|---------|-------------------|
| `POST /convert/file` | Add `download` support, change default to `json`, call helper | `{original_filename}.md` |
| `POST /convert/convert` | Same as above (legacy, delegates to file) | Same |
| `POST /convert/youtube` | Fix bare dict, enrich metadata, change default to `json` | `{video_title}.md` |
| `POST /convert/audio` | Fix always-markdown bug, change default to `json` | `{audio_filename}.md` |
| `POST /convert/video` | Fix ignored `return_format`, change default to `json` | `{video_filename}.md` |
| `POST /convert/url` | Add `download` support, add validation | `output.md` |
| `POST /convert/clean-html` | Add `return_format` parameter (new), default `json` | `cleaned.md` |

## Error Handling

Errors always return JSON regardless of `return_format`:

```python
return JSONResponse(
    status_code=400,
    content=error_response(
        code=ErrorCodes.INVALID_FORMAT,
        message="Unsupported file format",
        details=f"Extension '{ext}' is not supported",
        request_id=request_id,
    )
)
```

All endpoints migrate from `HTTPException` to `JSONResponse + error_response()`.

## Testing Strategy

### Unit Tests

`tests/unit/test_response.py` — test `build_convert_response()`:

- `return_format=json` returns correct envelope with `data.content` and `data.metadata`
- `return_format=markdown` returns `text/markdown` content type
- `return_format=download` returns `Content-Disposition: attachment` header with correct filename
- Errors always return JSON

### Integration Tests (per endpoint)

Each endpoint must cover:

| Test Case | Description |
|-----------|-------------|
| `return_format=json` (default) | `success=true`, `data.content` is string, `data.metadata` has values |
| `return_format=markdown` | `Content-Type: text/markdown`, plain text body |
| `return_format=download` | `Content-Disposition: attachment`, correct filename |
| `return_format=invalid` | Returns 422 Unprocessable Entity |
| Error scenario (any format) | Always returns JSON error envelope |

### Test Files

```
tests/
  unit/
    test_response.py              # build_convert_response() unit tests (new)
  integration/
    test_convert_file.py          # Existing, add new cases
    test_convert_youtube.py       # Existing, add new cases
    test_convert_audio.py         # Existing, add new cases
    test_convert_video.py         # New
    test_convert_url.py           # Existing, add new cases
    test_convert_clean_html.py    # New
```

## Non-Goals

- No changes to non-convert endpoints (`/health`, `/formats`, `/config`, etc.)
- No changes to error envelope structure
- No changes to existing metadata fields — only adding `content` wrapper and `metadata` key

## Versioning

This is a **breaking change** for clients currently consuming:
- `/convert/youtube` bare dict response
- `/convert/video` always-markdown response
- `/convert/audio` always-markdown response

Version bump: `v0.7.x` → `v0.8.0` (MINOR — backward-incompatible response structure change)
