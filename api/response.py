"""
Unified JSON response format module.

All API responses follow the same structure for consistency.

Success response:
{
    "success": true,
    "data": { ... },
    "metadata": { ... },
    "request_id": "req-xxx"
}

Error response:
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "Error description",
        "details": "Additional details"
    },
    "request_id": "req-xxx",
    "timestamp": "2026-03-16T14:30:00Z"
}
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
import uuid
from contextvars import ContextVar
from fastapi.responses import JSONResponse, Response as FastAPIResponse

# Context variable to store request ID per request
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"req-{uuid.uuid4().hex[:12]}"


def get_request_id() -> str:
    """Get the current request ID from context."""
    rid = request_id_var.get()
    return rid if rid else generate_request_id()


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set the request ID in context. Returns the ID."""
    if request_id is None:
        request_id = generate_request_id()
    request_id_var.set(request_id)
    return request_id


@dataclass
class ErrorResponse:
    """Standardized error response structure."""
    code: str
    message: str
    details: Optional[str] = None


# Error codes from spec Section 3.15
class ErrorCodes:
    """Standard error codes."""
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    INVALID_OCR_LANGUAGE = "INVALID_OCR_LANGUAGE"
    YOUTUBE_DOWNLOAD_FAILED = "YOUTUBE_DOWNLOAD_FAILED"
    WHISPER_DOWNLOADING = "WHISPER_DOWNLOADING"
    WHISPER_TRANSCRIPTION_FAILED = "WHISPER_TRANSCRIPTION_FAILED"
    VIDEO_CONVERSION_FAILED = "VIDEO_CONVERSION_FAILED"
    QUEUE_WAITING = "QUEUE_WAITING"
    IP_NOT_ALLOWED = "IP_NOT_ALLOWED"
    INVALID_CONFIG = "INVALID_CONFIG"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"


def success_response(
    data: Any,
    metadata: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized success response.
    
    Args:
        data: The response data
        metadata: Optional metadata dict
        request_id: Request ID (defaults to context value)
        
    Returns:
        Standardized response dict
    """
    return {
        "success": True,
        "data": data,
        "metadata": metadata or {},
        "request_id": request_id or get_request_id()
    }


def error_response(
    code: str,
    message: str,
    details: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        code: Error code from ErrorCodes
        message: Human-readable error message
        details: Optional additional details
        request_id: Request ID (defaults to context value)
        
    Returns:
        Standardized error response dict
    """
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details
        },
        "request_id": request_id or get_request_id(),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }


def queue_waiting_response(
    queue_position: int,
    estimated_wait_seconds: int,
    current_processing: int,
    max_concurrent: int,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a queue waiting response (HTTP 202).
    
    Args:
        queue_position: Position in queue
        estimated_wait_seconds: Estimated wait time
        current_processing: Current number of processing requests
        max_concurrent: Maximum concurrent requests
        request_id: Request ID
        
    Returns:
        Queue waiting response dict
    """
    return {
        "success": False,
        "error": {
            "code": ErrorCodes.QUEUE_WAITING,
            "message": "Service busy, request is queuing",
            "details": {
                "queue_position": queue_position,
                "estimated_wait_seconds": estimated_wait_seconds,
                "current_processing": current_processing,
                "max_concurrent": max_concurrent
            }
        },
        "request_id": request_id or get_request_id(),
        "retry_after": estimated_wait_seconds
    }


# Conversion response helpers
def convert_file_response(
    content: str,
    format: str,
    filename: str,
    file_size: int,
    conversion_time: str,
    ocr_language: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a file conversion response.
    
    Args:
        content: Converted markdown content
        format: Output format
        filename: Original filename
        file_size: File size in bytes
        conversion_time: Conversion timestamp
        ocr_language: OCR language used (if applicable)
        request_id: Request ID
        
    Returns:
        Standardized conversion response
    """
    return success_response(
        data={
            "content": content,
            "format": format
        },
        metadata={
            "filename": filename,
            "file_size": file_size,
            "conversion_time": conversion_time,
            "ocr_language": ocr_language
        },
        request_id=request_id
    )


def build_convert_response(
    content: str,
    metadata: Dict[str, Any],
    return_format: str = "json",
    filename: str = "output.md",
    request_id: Optional[str] = None,
) -> FastAPIResponse:
    """
    Build a unified conversion response in the requested format.

    Args:
        content: Markdown content string
        metadata: Endpoint-specific metadata dict
        return_format: One of 'json' (default), 'markdown', 'download'
        filename: Filename used for the Content-Disposition header (download only)
        request_id: Optional request ID; auto-generated when omitted

    Returns:
        FastAPI Response: JSONResponse for 'json', plain Response for others
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


def transcribe_response(
    formats: Dict[str, str],
    default_format: str,
    source_type: str,
    title: Optional[str] = None,
    duration: Optional[float] = None,
    language: Optional[str] = None,
    model: Optional[str] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a transcription response.
    
    Args:
        formats: Dict mapping format names to content
        default_format: Default format key
        source_type: Source type (youtube, audio, video)
        title: Media title
        duration: Duration in seconds
        language: Detected/specified language
        model: Whisper model used
        request_id: Request ID
        
    Returns:
        Standardized transcription response
    """
    return success_response(
        data={
            "formats": formats,
            "default_format": default_format
        },
        metadata={
            "source_type": source_type,
            "title": title,
            "duration": duration,
            "language": language,
            "model": model
        },
        request_id=request_id
    )