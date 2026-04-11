from fastapi import FastAPI, File, UploadFile, HTTPException, Query, APIRouter, Form
from fastapi.responses import Response, StreamingResponse
from markitdown import MarkItDown
import tempfile
import os
from pathlib import Path
from datetime import datetime
import io
import re
import ipaddress
import socket
from urllib.parse import urlparse
from typing import Optional
import requests

# Default headers for HTTP requests
DEFAULT_REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}


def _validate_url_not_private(url: str) -> None:
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: no hostname")
    if hostname in ('localhost', '127.0.0.1', '0.0.0.0', '::1'):
        raise ValueError(f"URL resolves to a private address: {hostname}")
    try:
        ip = socket.getaddrinfo(hostname, None)
        for family, _, _, _, sockaddr in ip:
            addr = sockaddr[0]
            if ipaddress.ip_address(addr).is_private:
                raise ValueError(f"URL resolves to a private address: {addr}")
    except (socket.gaierror, ValueError) as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Could not resolve hostname: {hostname}")


def _html_to_markdown(html_content: bytes | str) -> str:
    from .readability_client import extract_readability
    result = extract_readability(html_content)
    md_converter = MarkItDown()
    md_result = md_converter.convert_stream(
        io.BytesIO(result["content"].encode("utf-8")),
        file_extension=".html",
        mime_type="text/html",
    )
    return md_result.text_content

# Validate environment variables on startup
from .config import validate_environment, ConfigurationError

# Import unified response format and error codes
from .response import (
    success_response,
    error_response,
    ErrorCodes,
    set_request_id,
    transcribe_response,
    convert_file_response,
    build_convert_response,
)

# Import concurrency manager
from .concurrency import get_concurrency_manager

# Import OCR client module
from .ocr_client import ocr_image, ocr_pdf, OCRError

try:
    _config = validate_environment()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    raise SystemExit(1)

# Read configuration from config object
API_DEBUG = _config.api.debug
DEFAULT_OCR_LANG = _config.ocr.default_lang
ENABLE_PLUGINS_BY_DEFAULT = _config.ocr.enabled_by_default
MAX_UPLOAD_SIZE = _config.upload.max_size

# OpenAI configuration (optional)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")


def ocr_image_pdf(pdf_path: str, ocr_lang: str = "chi_tra+eng") -> str:
    """
    Perform OCR on image-based PDFs using pytesseract SDK.
    
    Some PDFs are scanned documents (image PDFs), which MarkItDown cannot extract text from directly.
    This function:
    1. Uses PyMuPDF to convert PDF pages to high-resolution images
    2. Uses pytesseract OCR to recognize text in the images
    
    Args:
        pdf_path: Path to the PDF file
        ocr_lang: OCR language code (default: chi_tra+eng)
    
    Returns:
        OCR recognized text content
    """
    try:
        return ocr_pdf(pdf_path, ocr_lang, zoom=3.0, min_text_length=10)
    except OCRError as e:
        raise Exception(f"OCR processing failed: {str(e)}")
    except Exception as e:
        raise Exception(f"OCR processing failed: {str(e)}")

app = FastAPI(
    title="MarkItDown API",
    description="Convert various file formats to Markdown via HTTP API with multi-language OCR support and YouTube/Audio transcription",
    version="0.8.0",
    debug=API_DEBUG,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Create API Router with /api/v1 prefix
api_router = APIRouter(prefix="/api/v1")

# Configure servers for Swagger to know correct API endpoints
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .constants import OCR_LANGUAGES

# Add IP whitelist middleware for admin endpoints
from .ip_whitelist import IPWhitelistMiddleware
app.add_middleware(IPWhitelistMiddleware)

# Setup logging and add middleware
from .middleware import RequestLoggingMiddleware, setup_logging
logger = setup_logging()

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# ===== Error Handling Configuration =====
import json
from fastapi.exceptions import RequestValidationError

ERROR_LANG = os.getenv("ERROR_LANG", "zh-TW")

ERROR_MESSAGES = {
    "zh-TW": {
        "internal_error": "伺服器內部錯誤，請稍後重試",
        "not_found": "找不到資源",
        "validation_error": "請求參數驗證失敗",
        "timeout": "操作超時，請稍後重試",
    },
    "en": {
        "internal_error": "Internal server error, please try again later",
        "not_found": "Resource not found",
        "validation_error": "Request validation failed",
        "timeout": "Operation timed out, please try again later",
    }
}

def get_error_message(key: str, accept_language: Optional[str] = None) -> str:
    """Get error message in preferred language."""
    lang = accept_language if accept_language else ERROR_LANG
    if lang not in ERROR_MESSAGES:
        lang = "en"  # Fallback to English
    return ERROR_MESSAGES.get(lang, {}).get(key, "Unknown error")

# ===== Exception Handlers =====
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Handle unhandled exceptions with language-aware messages."""
    if API_DEBUG:
        # Debug mode: show full error details
        return Response(
            content=json.dumps({
                "detail": str(exc),
                "type": type(exc).__name__,
            }),
            status_code=500,
            media_type="application/json"
        )
    else:
        # Production mode: hide internal details
        accept_language = request.headers.get("Accept-Language", ERROR_LANG)
        message = get_error_message("internal_error", accept_language)
        
        # Log full error internally
        logger.error(f"Internal error: {exc}", exc_info=True)
        
        return Response(
            content=json.dumps({"detail": message}),
            status_code=500,
            media_type="application/json"
        )

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Return empty 404 response."""
    return Response(status_code=404)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors with language-aware messages.

    Returns 422 for query/path/header parameter validation errors (standard HTTP
    semantics for unprocessable input), and 400 for body validation errors.
    """
    accept_language = request.headers.get("Accept-Language", ERROR_LANG)
    message = get_error_message("validation_error", accept_language)

    errors = exc.errors()
    # Return 422 if all errors are from non-body locations (query, path, header)
    # so that FastAPI's standard Query pattern validation returns the expected 422.
    non_body_locations = {"query", "path", "header", "cookie"}
    all_non_body = errors and all(
        (err.get("loc") or ("body",))[0] in non_body_locations
        for err in errors
    )
    status_code = 422 if all_non_body else 400

    return Response(
        content=json.dumps({
            "detail": message,
            "errors": errors if API_DEBUG else None
        }),
        status_code=status_code,
        media_type="application/json"
    )

# Initialize MarkItDown
from fastapi.responses import Response

md = MarkItDown(enable_plugins=ENABLE_PLUGINS_BY_DEFAULT)

@app.get("/", include_in_schema=False)
async def root():
    """Return 404 for root path."""
    return Response(status_code=404)

# Mount system router
from .system import api_router as system_router
app.include_router(system_router)

# Keep health endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

# Rename /api/v1/convert to /api/v1/convert/file and add backward compatibility alias
@api_router.post("/convert/file", 
           summary="Convert file to Markdown",
           description="Upload a file and convert it to Markdown format.\n\n"
                       "**Supported file formats:**\n"
                       "- PDF, DOCX, DOC, PPTX, PPT\n"
                       "- XLSX, XLS\n"
                       "- Images (JPG, PNG, GIF, WEBP, etc.)\n"
                       "- Audio (MP3, WAV, M4A, etc.)\n"
                       "- HTML, CSV, JSON, XML\n"
                       "- ZIP, EPub\n\n"
                       "**OCR language support:**\n"
                       "- chi_tra: Traditional Chinese\n"
                       "- chi_sim: Simplified Chinese\n"
                       "- eng: English\n"
                       "- jpn: Japanese\n"
                       "- kor: Korean\n"
                       "- tha: Thai\n"
                       "- vie: Vietnamese\n\n"
                       "**Response formats:**\n"
                       "- markdown: Returns Markdown text directly\n"
                       "- json: Returns JSON with metadata and content")
async def convert_file_endpoint(
    file: UploadFile = File(..., description="File to convert"),
    enable_ocr: bool = Query(False, description="Enable OCR, default false"),
    ocr_lang: str = Query("chi_tra+eng", description="OCR language code, default chi_tra+eng, use + to combine multiple languages"),
    return_format: str = Query("json", description="Response format: json (default), markdown, or download", pattern="^(json|markdown|download)$"),
    clean_html: str = Form("true", description="Use Readability to clean HTML before conversion (default: true)")
):
    """
    Upload a file and convert it to Markdown.

    - **file**: File to convert (supports PDF, DOCX, PPTX, XLSX, images, audio, etc.)
    - **enable_ocr**: Enable OCR (default: false)
    - **ocr_lang**: OCR language (default: environment variable DEFAULT_OCR_LANG, supports chi_tra, chi_sim, eng, jpn, kor, tha, vie, combinable with +)
    - **return_format**: Response format (json, markdown, or download)
    - **clean_html**: Use Readability to clean HTML before conversion (default: true)
    
    Returns:
    - **markdown**: Returns Markdown text directly (Content-Type: text/markdown)
    - **json**: Returns JSON with metadata and content
    """
    clean_html_bool = clean_html.lower() in ("true", "1", "yes")
    
    # Set request ID
    request_id = set_request_id()
    
    # Validate file size
    file_content = await file.read()
    if len(file_content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=error_response(
                code=ErrorCodes.FILE_TOO_LARGE,
                message=f"File too large: {len(file_content)} bytes. Maximum: {MAX_UPLOAD_SIZE} bytes ({MAX_UPLOAD_SIZE // 1024 // 1024}MB)",
                request_id=request_id
            )
        )
    
    # Validate file type
    allowed_extensions = {
        '.pdf', '.docx', '.doc', '.pptx', '.ppt', 
        '.xlsx', '.xls', '.html', '.htm', '.csv',
        '.json', '.xml', '.zip', '.epub', '.msg',
        '.jpg', '.jpeg', '.png', '.gif', '.webp',
        '.mp3', '.wav', '.m4a', '.flac'
    }
    
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=error_response(
                code=ErrorCodes.UNSUPPORTED_FORMAT,
                message=f"Unsupported file type: {file_ext}. Supported types: {', '.join(allowed_extensions)}",
                request_id=request_id
            )
        )
    
    # Use environment variable defaults
    enable_plugins = enable_ocr  # Use enable_ocr parameter (spec-compliant name)
    
    if ocr_lang is None:
        ocr_lang = DEFAULT_OCR_LANG
    
    # Validate OCR language
    if ocr_lang:
        valid_langs = set(OCR_LANGUAGES.keys())
        requested_langs = ocr_lang.split('+')
        for lang in requested_langs:
            if lang not in valid_langs:
                raise HTTPException(
                    status_code=400,
                    detail=error_response(
                        code=ErrorCodes.INVALID_OCR_LANGUAGE,
                        message=f"Unsupported OCR language: {lang}. Supported languages: {', '.join(valid_langs)}",
                        request_id=request_id
                    )
                )
    
    # ===== CONCURRENCY CONTROL INTEGRATION =====
    # Get concurrency manager
    manager = get_concurrency_manager()
    
    # Wait for processing slot with timeout
    acquired, queue_item = await manager.wait_for_slot(
        request_type="convert",
        request_id=request_id,
        timeout=None  # Use default queue_timeout from config
    )
    
    if not acquired:
        # Queue is full, return queue waiting response
        from .response import queue_waiting_response
        from fastapi.responses import JSONResponse
        
        # Calculate estimated wait time based on queue position
        estimated_wait = 30  # Default 30 seconds
        if queue_item:
            estimated_wait = queue_item.position * 10  # 10 seconds per position
        
        return JSONResponse(
            status_code=202,
            content=queue_waiting_response(
                queue_position=queue_item.position if queue_item else 1,
                estimated_wait_seconds=estimated_wait,
                current_processing=manager.current_processing,
                max_concurrent=manager.max_concurrent,
                request_id=request_id
            )
        )
    
    # Slot acquired, proceed with processing
    try:
        # Use temporary file for conversion (MarkItDown requires file path)
        # Important: Use delete=False and manage manually to ensure correct encoding
        import uuid
        temp_filename = f"temp_{uuid.uuid4().hex}{file_ext}"
        temp_dir = tempfile.gettempdir()
        tmp_path = os.path.join(temp_dir, temp_filename)
        
        try:
            # Write file in binary mode (avoid encoding issues)
            with open(tmp_path, 'wb') as tmp_file:
                tmp_file.write(file_content)
            
            # Execute conversion (set environment variable for OCR if needed)
            env_vars = {}
            if enable_plugins and ocr_lang:
                env_vars['TESSERACT_LANG'] = ocr_lang
            
            html_extensions = {'.html', '.htm'}
            if clean_html_bool and file_ext in html_extensions:
                with open(tmp_path, 'rb') as f:
                    raw_html = f.read()
                text_content = _html_to_markdown(raw_html)
            else:
                result = md.convert(tmp_path, enable_plugins=enable_plugins)
                text_content = result.text_content
            
            # Special handling: If PDF content is empty or minimal, it may be a scanned PDF
            # Need to use OCR
            if file_ext == '.pdf' and (not text_content or len(text_content.strip()) < 10):
                if API_DEBUG:
                    print(f"PDF content is empty or less than 10 characters, trying OCR...")
                
                try:
                    ocr_result = ocr_image_pdf(tmp_path, ocr_lang or DEFAULT_OCR_LANG)
                    if ocr_result and len(ocr_result.strip()) > len(text_content.strip()):
                        text_content = f"[OCR Result]\n\n{ocr_result}"
                        if API_DEBUG:
                            print(f"OCR successful: {len(text_content)} characters")
                except Exception as ocr_error:
                    if API_DEBUG:
                        print(f"OCR failed: {ocr_error}")
            
            # Special handling: If image and OCR enabled, use pytesseract SDK
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
            if file_ext in image_extensions and enable_plugins:
                if API_DEBUG:
                    print(f"Image OCR processing...")
                
                try:
                    ocr_text = ocr_image(tmp_path, ocr_lang or DEFAULT_OCR_LANG)
                    if ocr_text and len(ocr_text) > len(text_content.strip()):
                        text_content = f"[OCR Result]\n\n{ocr_text}"
                        if API_DEBUG:
                            print(f"Image OCR successful: {len(text_content)} characters")
                except Exception as ocr_error:
                    if API_DEBUG:
                        print(f"Image OCR failed: {ocr_error}")
            
            return build_convert_response(
                content=text_content,
                metadata={
                    "source": file.filename or "unknown",
                    "format": "markdown",
                    "file_size": len(file_content),
                    "ocr_language": ocr_lang if enable_plugins else None,
                },
                return_format=return_format,
                filename=f"{Path(file.filename or 'output').stem}.md",
                request_id=request_id,
            )
        
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception as cleanup_error:
                    if API_DEBUG:
                        print(f"Failed to clean up temporary file: {cleanup_error}")
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=error_response(
                code=ErrorCodes.INTERNAL_ERROR,
                message=f"Conversion failed: {str(e)}",
                request_id=request_id
            )
        )
    finally:
        # Always release the processing slot
        manager.release(request_id)


@api_router.post("/convert/convert")
async def convert_file_legacy(
    file: UploadFile = File(..., description="File to convert"),
    enable_ocr: bool = Query(False, description="Enable OCR, default false"),
    ocr_lang: str = Query("chi_tra+eng", description="OCR language code, default chi_tra+eng, use + to combine multiple languages"),
    return_format: str = Query("json", description="Response format: json (default), markdown, or download", pattern="^(json|markdown|download)$"),
    clean_html: str = Form("true", description="Use Readability to clean HTML before conversion (default: true)")
):
    """Legacy endpoint for backward compatibility. Redirects to /convert/file."""
    return await convert_file_endpoint(file, enable_ocr, ocr_lang, return_format, clean_html)


# ==================== Whisper Transcription Endpoints ====================

from .whisper_transcribe import (
    transcribe_audio,
    transcribe_audio_chunked,
    transcribe_youtube_video,
    transcribe_with_formats,
    extract_audio_from_video,
    format_transcript_as_markdown,
    get_recommended_model,
    SUPPORTED_LANGUAGES
)
from .response import success_response, transcribe_response, ErrorCodes
from .concurrency import get_concurrency_manager
from .device_utils import get_device_info
from .chunking import ChunkConfig, get_audio_duration, should_enable_chunking
from .constants import (
    DEFAULT_CHUNK_DURATION,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_AUTO_CHUNK_THRESHOLD,
    MAX_TOTAL_DURATION
)

@api_router.post("/convert/youtube")
async def convert_youtube(
    url: str = Query(..., description="YouTube video URL"),
    language: str = Query("zh", description="Language code (zh, en, ja, ko, etc.)"),
    model_size: str = Query("auto", description="Model size (auto, tiny, base, small, medium, large)"),
    return_format: str = Query("json", description="Response format: json (default), markdown, or download", pattern="^(json|markdown|download)$"),
    quality_mode: str = Query("standard", description="Quality preset: fast, standard, best"),
    include_timestamps: bool = Query(False, description="Include timestamps in transcript"),
    device: str = Query(None, description="Compute device: auto, cpu, cuda, mps, rocm")
):
    """
    Download YouTube video audio and transcribe using Whisper.

    **Parameters:**
    - **url**: YouTube video URL
    - **language**: Language code (zh=Chinese, en=English, ja=Japanese, ko=Korean)
    - **model_size**: Model size (auto=tiny/base/small based on duration)
    - **return_format**: Response format (json=structured data, markdown=text)
    - **quality_mode**: Quality preset (fast, standard, best)
    - **include_timestamps**: Include [HH:MM:SS] timestamps in transcript
    - **device**: Compute device (auto-detect if None)

    **Auto-configured internally (when device=None):**
    - Device: auto-detect (CUDA > MPS > CPU)
    - VAD: always enabled
    - Subtitle priority: auto-enabled for fast transcription
    - Chunking: auto-enabled for long audio
    """

    # Set request ID
    request_id = set_request_id()

    # ===== CONCURRENCY CONTROL INTEGRATION =====
    manager = get_concurrency_manager()

    acquired, queue_item = await manager.wait_for_slot(
        request_type="youtube",
        request_id=request_id,
        timeout=None
    )

    if not acquired:
        from .response import queue_waiting_response
        from fastapi.responses import JSONResponse

        estimated_wait = 30
        if queue_item:
            estimated_wait = queue_item.position * 10

        return JSONResponse(
            status_code=202,
            content=queue_waiting_response(
                queue_position=queue_item.position if queue_item else 1,
                estimated_wait_seconds=estimated_wait,
                current_processing=manager.current_processing,
                max_concurrent=manager.max_concurrent,
                request_id=request_id
            )
        )

    try:
        # Resolve quality preset to beam_size/temperature
        from .constants import QUALITY_PRESETS
        preset = QUALITY_PRESETS.get(quality_mode, QUALITY_PRESETS["standard"])

        # Device: use provided value or auto-detect
        if device and device != "auto":
            effective_device = device
        else:
            from .device_utils import detect_device
            effective_device = detect_device()

        from .device_utils import get_compute_type_for_device, get_recommended_threads
        effective_compute_type = get_compute_type_for_device(effective_device)
        effective_threads = get_recommended_threads(0)

        result = transcribe_youtube_video(
            url=url,
            language=language,
            model_size=model_size,
            device=effective_device,
            compute_type=effective_compute_type,
            cpu_threads=effective_threads,
            vad_enabled=True,
            prefer_subtitles=True,
            fast_mode=(quality_mode == "fast"),
            beam_size=preset["beam_size"],
            temperature=preset["temperature"],
            include_timestamps=include_timestamps,
        )

        # Format as Markdown
        markdown_content = format_transcript_as_markdown(
            title=result["title"],
            transcript=result["transcript"],
            metadata=result["metadata"],
            include_metadata=True,
            include_timestamps=include_timestamps,
        )

        return build_convert_response(
            content=markdown_content,
            metadata={
                "source": url,
                "title": result["title"],
                "transcript": result["transcript"],
                **result["metadata"],
            },
            return_format=return_format,
            filename=f"{result['title'][:50]}.md" if result.get("title") else "transcript.md",
            request_id=request_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )


@api_router.post("/convert/audio")
async def transcribe_audio_file(
    file: UploadFile = File(..., description="Audio file"),
    language: str = Query("zh", description="Language code"),
    model_size: str = Query("auto", description="Model size (auto, tiny, base, small, medium, large)"),
    return_format: str = Query("json", description="Response format: json (default), markdown, or download", pattern="^(json|markdown|download)$"),
    quality_mode: str = Query("standard", description="Quality preset: fast, standard, best")
):
    """
    Upload audio file and transcribe using Whisper.

    **Parameters:**
    - **file**: Audio file (MP3, WAV, M4A, FLAC, etc.)
    - **language**: Language code
    - **model_size**: Model size (auto=tiny/base/small based on duration)
    - **return_format**: Response format (markdown or json)
    - **quality_mode**: Quality preset (fast, standard, best)

    **Auto-configured internally:**
    - Device: auto-detect (CUDA > MPS > CPU)
    - VAD: always enabled
    - Chunking: auto-enabled for files > 90s
    """
    from .constants import QUALITY_PRESETS
    from .device_utils import detect_device, get_compute_type_for_device, get_recommended_threads

    preset = QUALITY_PRESETS.get(quality_mode, QUALITY_PRESETS["standard"])
    effective_device = detect_device()
    effective_compute_type = get_compute_type_for_device(effective_device)
    effective_threads = get_recommended_threads(0)

    try:
        suffix = Path(file.filename or "").suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            transcript, metadata = transcribe_audio_chunked(
                tmp_path,
                language=language,
                model_size=model_size,
                device=effective_device,
                compute_type=effective_compute_type,
                cpu_threads=effective_threads,
                vad_enabled=True,
                enable_chunking=True,
                chunk_duration=DEFAULT_CHUNK_DURATION,
                chunk_overlap=DEFAULT_CHUNK_OVERLAP,
                auto_enable_threshold=DEFAULT_AUTO_CHUNK_THRESHOLD,
                beam_size=preset["beam_size"],
                temperature=preset["temperature"],
            )

            markdown_content = format_transcript_as_markdown(
                title=file.filename or "Audio Transcription",
                transcript=transcript,
                metadata=metadata
            )

            from urllib.parse import quote
            safe_filename = file.filename or "unknown"
            try:
                safe_filename.encode('ascii')
            except UnicodeEncodeError:
                safe_filename = quote(safe_filename, safe='')

            return build_convert_response(
                content=markdown_content,
                metadata={
                    "source": file.filename or "unknown",
                    "transcript": transcript,
                    **metadata,
                },
                return_format=return_format,
                filename=f"{Path(file.filename or 'audio').stem}.md",
                request_id=None,
            )

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )


@api_router.post("/convert/video")
async def transcribe_video_file(
    file: UploadFile = File(..., description="Video file"),
    language: str = Query("auto", description="Language code"),
    model_size: str = Query("auto", description="Model size (auto, tiny, base, small, medium, large)"),
    return_format: str = Query("json", description="Response format: json (default), markdown, or download", pattern="^(json|markdown|download)$"),
    quality_mode: str = Query("standard", description="Quality preset: fast, standard, best")
):
    """
    Upload video file and transcribe using Whisper.

    **Parameters:**
    - **file**: Video file (MP4, MKV, WebM, AVI, MOV, FLV, TS)
    - **language**: Language code
    - **model_size**: Model size (auto=tiny/base/small based on duration)
    - **return_format**: Response format (markdown or json)
    - **quality_mode**: Quality preset (fast, standard, best)

    **Auto-configured internally:**
    - Device: auto-detect (CUDA > MPS > CPU)
    - VAD: always enabled
    - Chunking: auto-enabled for files > 90s
    """
    from .constants import QUALITY_PRESETS
    from .device_utils import detect_device, get_compute_type_for_device, get_recommended_threads

    allowed_video_extensions = {
        '.mp4', '.mkv', '.webm', '.avi', '.mov', '.flv', '.ts'
    }

    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in allowed_video_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video type: {file_ext}. Supported types: {', '.join(allowed_video_extensions)}"
        )

    preset = QUALITY_PRESETS.get(quality_mode, QUALITY_PRESETS["standard"])
    effective_device = detect_device()
    effective_compute_type = get_compute_type_for_device(effective_device)
    effective_threads = get_recommended_threads(0)

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            content = await file.read()
            tmp.write(content)
            video_path = tmp.name

        audio_path = None

        try:
            audio_path = extract_audio_from_video(video_path)

            transcript, metadata = transcribe_audio_chunked(
                audio_path,
                language=language,
                model_size=model_size,
                device=effective_device,
                compute_type=effective_compute_type,
                cpu_threads=effective_threads,
                vad_enabled=True,
                enable_chunking=True,
                chunk_duration=DEFAULT_CHUNK_DURATION,
                chunk_overlap=DEFAULT_CHUNK_OVERLAP,
                auto_enable_threshold=DEFAULT_AUTO_CHUNK_THRESHOLD,
                beam_size=preset["beam_size"],
                temperature=preset["temperature"],
            )

            metadata["source"] = "video"
            metadata["original_filename"] = file.filename

            markdown_content = format_transcript_as_markdown(
                title=file.filename or "Video Transcription",
                transcript=transcript,
                metadata=metadata
            )

            from urllib.parse import quote
            safe_filename = file.filename or "unknown"
            try:
                safe_filename.encode('ascii')
            except UnicodeEncodeError:
                safe_filename = quote(safe_filename, safe='')

            return build_convert_response(
                content=markdown_content,
                metadata={
                    "source": "video",
                    "original_filename": file.filename,
                    "transcript": transcript,
                    **metadata,
                },
                return_format=return_format,
                filename=f"{Path(file.filename or 'video').stem}.md",
                request_id=None,
            )

        finally:
            if os.path.exists(video_path):
                os.unlink(video_path)
            if audio_path and os.path.exists(audio_path):
                os.unlink(audio_path)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Video transcription failed: {str(e)}"
        )


@api_router.get("/convert/languages")
async def list_transcribe_languages():
    """List supported Whisper languages."""
    return {
        "supported_languages": SUPPORTED_LANGUAGES,
        "models": {
            "tiny": {"speed": "Fastest", "accuracy": "Fair", "memory": "~500MB"},
            "base": {"speed": "Fast", "accuracy": "Good", "memory": "~1GB"},
            "small": {"speed": "Medium", "accuracy": "Very Good", "memory": "~2GB"},
            "medium": {"speed": "Slow", "accuracy": "Excellent", "memory": "~5GB"},
            "large": {"speed": "Slowest", "accuracy": "Best", "memory": "~10GB"}
        },
        "recommended": {
            "fast": "tiny",
            "balanced": "base",
            "accurate": "small"
        }
    }

@api_router.get("/formats")
async def list_formats():
    """
    Supported file formats.
    
    Per spec Section 3.12, returns wrapped response with success wrapper.
    """
    data = {
        "documents": ["pdf", "docx", "doc", "pptx", "ppt", "xlsx", "xls"],
        "images": ["jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff"],
        "audio": ["mp3", "wav", "m4a", "flac", "ogg"],
        "video": ["mp4", "mkv", "webm", "avi", "mov", "flv", "ts"],
        "web": ["html", "htm", "url"],
        "data": ["csv", "json", "xml"]
    }
    
    return success_response(data=data)

@api_router.get("/ocr-languages")
async def list_ocr_languages():
    """List all supported OCR languages."""
    return {
        "supported_languages": OCR_LANGUAGES,
        "default": DEFAULT_OCR_LANG,
        "usage": "Combine multiple languages with + symbol, e.g., chi_tra+eng+jpn",
        "examples": [
            {"code": "chi_tra", "name": "Traditional Chinese"},
            {"code": "chi_sim", "name": "Simplified Chinese"},
            {"code": "eng", "name": "English"},
            {"code": "jpn", "name": "Japanese"},
            {"code": "kor", "name": "Korean"},
            {"code": "tha", "name": "Thai"},
            {"code": "vie", "name": "Vietnamese"},
            {"code": "chi_tra+eng", "name": "Traditional Chinese + English (Default)"},
            {"code": "chi_sim+eng", "name": "Simplified Chinese + English"},
            {"code": "chi_tra+jpn+kor+eng", "name": "Multi-language Mix"},
            {"code": "tha+eng", "name": "Thai + English"},
            {"code": "vie+eng", "name": "Vietnamese + English"},
            {"code": "chi_tra+tha+vie+eng", "name": "Southeast Asian Multi-language Mix"},
        ]
    }

@api_router.get("/config")
async def get_config():
    """Get current API configuration (sensitive info hidden)."""
    return {
        "api": {
            "version": "0.8.0",
            "debug": API_DEBUG,
            "max_upload_size": MAX_UPLOAD_SIZE,
            "max_upload_size_mb": MAX_UPLOAD_SIZE // 1024 // 1024,
        },
        "ocr": {
            "default_language": DEFAULT_OCR_LANG,
            "plugins_enabled_by_default": ENABLE_PLUGINS_BY_DEFAULT,
            "supported_languages": OCR_LANGUAGES,
        },
        "openai": {
            "configured": bool(OPENAI_API_KEY),
            "model": OPENAI_MODEL if OPENAI_API_KEY else "N/A",
            "base_url": OPENAI_BASE_URL if OPENAI_API_KEY else "N/A",
        }
    }


@api_router.get("/device-info")
async def get_device_info_endpoint():
    """
    Get compute device information for Whisper transcription.
    
    Returns information about:
    - **device**: Detected device (cpu, cuda, or mps)
    - **cuda_available**: Whether NVIDIA CUDA is available
    - **mps_available**: Whether Apple Silicon MPS is available
    - **cpu_count**: Number of CPU cores
    - **recommended_compute_type**: Recommended compute type for the device
    - **cuda_device_name**: GPU name (if CUDA available)
    - **cuda_device_count**: Number of CUDA devices
    - **cuda_memory_gb**: GPU memory in GB (if CUDA available)
    
    This endpoint helps users understand what compute resources are available
    and choose the optimal device for transcription.
    """
    from .response import success_response
    
    device_info = get_device_info()
    return success_response(data=device_info)


# ===== Languages Endpoints (Spec-compliant) =====
@api_router.get("/languages/ocr")
async def get_ocr_languages():
    """
    Query OCR supported languages.
    
    Returns:
        - languages: Dict of language code to name
        - default: Default OCR language combination
        - combinations: List of recommended language combinations
    """
    from .response import success_response
    
    data = {
        "languages": {
            "chi_tra": "Traditional Chinese",
            "chi_sim": "Simplified Chinese",
            "eng": "English",
            "jpn": "Japanese",
            "kor": "Korean",
            "tha": "Thai",
            "vie": "Vietnamese"
        },
        "default": DEFAULT_OCR_LANG,
        "combinations": [
            "chi_tra+eng",
            "chi_sim+eng",
            "chi_tra+jpn+kor+eng"
        ]
    }
    
    return success_response(data=data)


@api_router.get("/languages/transcribe")
async def get_transcribe_languages():
    """
    Query transcription supported languages and models.
    
    Returns:
        - languages: Dict of language code to name
        - models: Dict of model info with speed, accuracy, memory_mb
    """
    from .response import success_response
    
    data = {
        "languages": {
            "zh": "Chinese",
            "en": "English",
            "ja": "Japanese",
            "ko": "Korean"
        },
        "models": {
            "tiny": {"speed": "fastest", "accuracy": "fair", "memory_mb": 500},
            "base": {"speed": "fast", "accuracy": "good", "memory_mb": 1000},
            "small": {"speed": "medium", "accuracy": "very good", "memory_mb": 2000},
            "medium": {"speed": "slow", "accuracy": "excellent", "memory_mb": 5000},
            "large": {"speed": "slowest", "accuracy": "best", "memory_mb": 10000}
        }
    }
    
    return success_response(data=data)

def detect_url_type(url: str, type_hint: str = "auto") -> tuple[str, dict]:
    """
    Detect URL type based on HTTP Content-Type header, magic bytes, or URL pattern.

    Args:
        url: URL to analyze
        type_hint: Type hint to override detection

    Returns:
        Tuple of (detected_type, metadata) where metadata may include filename from Content-Disposition
    """
    metadata = {}
    
    if type_hint != "auto":
        valid_types = ["youtube", "document", "audio", "video", "image", "webpage", "json", "markdown", "text"]
        if type_hint in valid_types:
            return (type_hint, metadata)

    import requests
    from urllib.parse import urlparse
    
    # Try to get Content-Type from headers
    try:
        response = requests.head(url, allow_redirects=True, timeout=10, headers=DEFAULT_REQUEST_HEADERS)
        content_type = response.headers.get('Content-Type', '').lower()
        content_disposition = response.headers.get('Content-Disposition', '').lower()
        content_type_main = content_type.split(';')[0].strip()
        
        # Map Content-Type to URL type
        type_mappings = {
            # YouTube
            'video/youtube': 'youtube',
            # Document types
            'application/pdf': 'document',
            'application/msword': 'document',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'document',
            'application/vnd.ms-powerpoint': 'document',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'document',
            'application/vnd.ms-excel': 'document',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'document',
            'application/epub+zip': 'document',
            'application/zip': 'document',
            'application/x-rar-compressed': 'document',
            # Image types
            'image/jpeg': 'image',
            'image/jpg': 'image',
            'image/png': 'image',
            'image/gif': 'image',
            'image/webp': 'image',
            'image/bmp': 'image',
            'image/tiff': 'image',
            'image/svg+xml': 'image',
            # Audio types
            'audio/mpeg': 'audio',
            'audio/mp3': 'audio',
            'audio/wav': 'audio',
            'audio/x-wav': 'audio',
            'audio/flac': 'audio',
            'audio/ogg': 'audio',
            'audio/aac': 'audio',
            'audio/x-m4a': 'audio',
            # Video types
            'video/mp4': 'video',
            'video/x-matroska': 'video',
            'video/webm': 'video',
            'video/avi': 'video',
            'video/quicktime': 'video',
            'video/x-msvideo': 'video',
            # Text-based types (new)
            'application/json': 'json',
            'text/json': 'json',
            'text/markdown': 'markdown',
            'text/x-markdown': 'markdown',
            'text/md': 'markdown',
            'text/plain': 'text',
            'text/csv': 'text',
            'text/xml': 'text',
            'application/xml': 'text',
            'text/css': 'text',
            'application/javascript': 'text',
            'text/javascript': 'text',
            # Webpage
            'text/html': 'webpage',
            'application/xhtml+xml': 'webpage',
            # Octet-stream (needs magic bytes detection)
            'application/octet-stream': 'octet-stream',
        }
        
        if content_type_main in type_mappings:
            detected_type = type_mappings[content_type_main]
            # If octet-stream, we need to check filename or do magic bytes
            if detected_type == 'octet-stream':
                # Try to get filename from Content-Disposition
                if 'filename=' in content_disposition:
                    import re
                    match = re.search(r'filename[*]?=([^;]+)', content_disposition)
                    if match:
                        metadata['filename'] = match.group(1).strip('"\'')
                        ext = Path(metadata['filename']).suffix.lower()
                        type_from_ext = _detect_type_from_extension(ext)
                        if type_from_ext:
                            return (type_from_ext, metadata)
                # Need magic bytes detection
                return _detect_from_magic_bytes(url, metadata)
            
            return (detected_type, metadata)
        
        # Check Content-Disposition for filename
        if 'filename=' in content_disposition:
            import re
            match = re.search(r'filename[*]?=([^;]+)', content_disposition)
            if match:
                metadata['filename'] = match.group(1).strip('"\'')
                ext = Path(metadata['filename']).suffix.lower()
                type_from_ext = _detect_type_from_extension(ext)
                if type_from_ext:
                    return (type_from_ext, metadata)
        
    except Exception:
        pass
    
    # Fallback: Extension-based detection
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.lower()

    if "youtube.com" in domain or "youtu.be" in domain:
        return ("youtube", metadata)

    doc_extensions = {'.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls', '.odt', '.ods', '.odp', '.epub', '.zip'}
    if any(path.endswith(ext) for ext in doc_extensions):
        return ("document", metadata)

    audio_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma'}
    if any(path.endswith(ext) for ext in audio_extensions):
        return ("audio", metadata)

    video_extensions = {'.mp4', '.mkv', '.webm', '.avi', '.mov', '.flv', '.ts', '.wmv'}
    if any(path.endswith(ext) for ext in video_extensions):
        return ("video", metadata)

    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif', '.svg'}
    if any(path.endswith(ext) for ext in image_extensions):
        return ("image", metadata)

    # Text-based extensions
    text_extensions = {'.json', '.md', '.markdown', '.txt', '.csv', '.xml', '.css', '.js', '.html', '.htm'}
    ext = Path(path).suffix.lower()
    if ext in text_extensions:
        type_from_ext = _detect_type_from_extension(ext)
        if type_from_ext:
            return (type_from_ext, metadata)

    return ("webpage", metadata)


def _detect_type_from_extension(ext: str) -> str:
    """Detect type from file extension."""
    ext = ext.lower()
    image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif', '.svg'}
    audio_exts = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma'}
    video_exts = {'.mp4', '.mkv', '.webm', '.avi', '.mov', '.flv', '.ts', '.wmv'}
    doc_exts = {'.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls', '.odt', '.ods', '.odp', '.epub', '.zip'}
    json_exts = {'.json'}
    md_exts = {'.md', '.markdown'}
    
    if ext in image_exts:
        return "image"
    if ext in audio_exts:
        return "audio"
    if ext in video_exts:
        return "video"
    if ext in doc_exts:
        return "document"
    if ext in json_exts:
        return "json"
    if ext in md_exts:
        return "markdown"
    if ext in {'.txt', '.csv', '.xml', '.css', '.js', '.html', '.htm'}:
        return "text"
    return "text"


def _detect_from_magic_bytes(url: str, metadata: dict) -> tuple[str, dict]:
    """Detect file type from magic bytes (first few bytes)."""
    import requests
    
    try:
        # Get first 512 bytes to check magic bytes
        response = requests.get(url, stream=True, timeout=10, headers={**DEFAULT_REQUEST_HEADERS, 'Range': 'bytes=0-511'})
        if response.status_code not in (200, 206):
            return ("document", metadata)
        
        first_bytes = response.content[:512]
        
        # Magic bytes signatures
        magic_signatures = {
            # PDF
            b'%PDF': 'document',
            # Images
            b'\x89PNG': 'image',
            b'\xff\xd8\xff': 'image',  # JPEG
            b'GIF87a': 'image',
            b'GIF89a': 'image',
            b'BM': 'image',
            b'RIFF': 'image',  # WEBP
            b'II\x2a\x00': 'image',  # TIFF
            b'MM\x00\x2a': 'image',  # TIFF
            # Audio
            b'ID3': 'audio',
            b'\xff\xfb': 'audio',  # MP3
            b'RIFF': 'audio',  # WAV (check later)
            b'fLaC': 'audio',  # FLAC
            # Video
            b'\x00\x00\x00\x18ftypmp4': 'video',
            b'\x00\x00\x00\x1cftyp': 'video',
            b'\x1aE\xdf\xa3': 'video',  # MKV
            # ZIP
            b'PK\x03\x04': 'document',
            # Office formats (ZIP-based)
            b'PK\x03\x04': 'document',  # DOCX, XLSX, PPTX
        }
        
        for sig, file_type in magic_signatures.items():
            if first_bytes.startswith(sig):
                # Special case for RIFF (could be WEBP image or WAV audio)
                if first_bytes.startswith(b'RIFF'):
                    if b'WEBP' in first_bytes[8:20]:
                        return ("image", metadata)
                    elif b'WAVE' in first_bytes[8:20]:
                        return ("audio", metadata)
                return (file_type, metadata)
        
    except Exception:
        pass
    
    # Default to document
    return ("document", metadata)


@api_router.post("/convert/url")
async def convert_url(
    url: str = Query(..., description="URL address"),
    type_hint: str = Query("auto", description="Type hint: auto/youtube/document/audio/video/image/webpage"),
    language: str = Query("auto", description="Transcription language (auto=auto-detect)"),
    model_size: str = Query("base", description="Whisper model size"),
    ocr_mode: str = Query("auto", description="OCR mode: auto (auto-detect), true (force OCR), false (disable OCR)", pattern="^(auto|true|false)$"),
    ocr_lang: str = Query(DEFAULT_OCR_LANG, description="OCR language"),
    include_timestamps: bool = Query(False, description="Include timestamps in Markdown"),
    clean_html: bool = Query(True, description="Use Readability to clean HTML before conversion (default: true)"),
    device: str = Query(None, description="Compute device: auto, cpu, cuda, mps, rocm"),
    cpu_threads: int = Query(None, description="CPU thread count (auto-detect if None)"),
    vad_enabled: bool = Query(True, description="Enable VAD filtering"),
    return_format: str = Query("json", description="Response format: json (default), markdown, or download", pattern="^(json|markdown|download)$"),
):
    """
    Unified URL endpoint - auto-detects URL type and processes accordingly.
    
    - **url**: URL address
    - **type_hint**: Type hint (overrides auto-detection)
    - **language**: Transcription language (auto=auto-detect)
    - **model_size**: Whisper model size (tiny, base, small, medium, large)
    - **ocr_mode**: OCR mode (auto=auto-detect, true=force OCR, false=disable OCR)
    - **ocr_lang**: OCR language (default: environment variable DEFAULT_OCR_LANG)
    - **include_timestamps**: Include timestamps in Markdown
    
    Supported types:
    - youtube: YouTube video transcription
    - document: Document conversion (PDF, DOCX, etc.)
    - audio: Audio file transcription
    - video: Video file transcription
    - image: Image OCR (JPG, PNG, GIF, WEBP, etc.)
    - json: JSON file (returns as code block)
    - markdown: Markdown file (returns raw content)
    - text: Plain text file
    - webpage: Webpage content conversion
    
    Fixed STT settings for audio/video: device=auto, cpu_threads=0, vad_enabled=true,
    enable_chunking=true, chunk_duration=60, chunk_overlap=2, auto_chunk_threshold=90
    """
    # Set request ID
    request_id = set_request_id()
    
    try:
        # Detect URL type (returns tuple: type, metadata)
        url_type, type_metadata = detect_url_type(url, type_hint)
        
        if url_type == "youtube":
            lang_param = None if language == "auto" else language
            result = transcribe_youtube_video(
                url=url,
                language=lang_param if lang_param else "zh",
                model_size=model_size,
                device="auto",
                compute_type="auto",
                cpu_threads=0,
                vad_enabled=True,
                beam_size=3,
                temperature=0.0,
                include_timestamps=include_timestamps,
            )
            
            markdown_content = format_transcript_as_markdown(
                title=result["title"],
                transcript=result["transcript"],
                metadata=result["metadata"],
                include_metadata=True,
                include_timestamps=include_timestamps,
            )
            
            return build_convert_response(
                content=markdown_content,
                metadata={
                    "source": url,
                    "source_type": "youtube",
                    "title": result["title"],
                    "duration": result["metadata"].get("duration"),
                    "language": language if language != "auto" else result["metadata"].get("language"),
                    "model": model_size,
                },
                return_format=return_format,
                filename=f"{result['title'][:50]}.md" if result.get("title") else "transcript.md",
                request_id=request_id,
            )
            
        elif url_type == "document":
            
            # Download file
            response = requests.get(url, stream=True, headers=DEFAULT_REQUEST_HEADERS)
            response.raise_for_status()
            
            # Get filename from URL
            filename = os.path.basename(urlparse(url).path)
            if not filename:
                filename = "document"
            
            # Determine file extension
            file_ext = Path(filename).suffix.lower()
            if not file_ext:
                # Guess extension from Content-Type
                content_type = response.headers.get('Content-Type', '')
                if 'pdf' in content_type:
                    file_ext = '.pdf'
                elif 'word' in content_type or 'docx' in content_type:
                    file_ext = '.docx'
                elif 'excel' in content_type or 'xlsx' in content_type:
                    file_ext = '.xlsx'
                elif 'powerpoint' in content_type or 'pptx' in content_type:
                    file_ext = '.pptx'
                else:
                    file_ext = '.pdf'  # Default
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp.write(chunk)
                tmp_path = tmp.name
            
            try:
                enable_plugins = ocr_mode == "true" or (ocr_mode == "auto")
                
                result = md.convert(tmp_path, enable_plugins=enable_plugins)
                text_content = result.text_content
                
                if file_ext == '.pdf' and enable_plugins and (not text_content or len(text_content.strip()) < 10):
                    try:
                        ocr_result = ocr_image_pdf(tmp_path, ocr_lang)
                        if ocr_result and len(ocr_result.strip()) > len(text_content.strip()):
                            text_content = f"[OCR Result]\n\n{ocr_result}"
                    except Exception as ocr_error:
                        if API_DEBUG:
                            print(f"OCR failed: {ocr_error}")
                
                return build_convert_response(
                    content=text_content,
                    metadata={
                        "source": url,
                        "source_type": "document",
                        "filename": filename,
                        "file_size": os.path.getsize(tmp_path),
                        "ocr_language": ocr_lang,
                    },
                    return_format=return_format,
                    filename=f"{Path(filename).stem}.md",
                    request_id=request_id,
                )
            
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        elif url_type == "audio":
            response = requests.get(url, stream=True, headers=DEFAULT_REQUEST_HEADERS)
            response.raise_for_status()
            
            filename = os.path.basename(urlparse(url).path)
            if not filename:
                filename = "audio"
            
            file_ext = Path(filename).suffix.lower()
            if not file_ext:
                file_ext = '.mp3'
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp.write(chunk)
                audio_path = tmp.name
            
            try:
                transcript, metadata = transcribe_audio_chunked(
                    audio_path,
                    language=language if language != "auto" else "auto",
                    model_size=model_size,
                    device="auto",
                    compute_type="auto",
                    cpu_threads=0,
                    vad_enabled=True,
                    enable_chunking=True,
                    chunk_duration=60,
                    chunk_overlap=2,
                    auto_enable_threshold=90,
                    beam_size=3,
                    temperature=0.0,
                )
                
                markdown_content = format_transcript_as_markdown(
                    title=filename,
                    transcript=transcript,
                    metadata=metadata,
                    include_metadata=True
                )
                
                return build_convert_response(
                    content=markdown_content,
                    metadata={
                        "source": url,
                        "source_type": "audio",
                        "title": filename,
                        "duration": metadata.get("duration"),
                        "language": language if language != "auto" else metadata.get("language"),
                        "model": model_size,
                    },
                    return_format=return_format,
                    filename=f"{Path(filename).stem}.md",
                    request_id=request_id,
                )
            
            finally:
                if os.path.exists(audio_path):
                    os.unlink(audio_path)
        
        elif url_type == "video":
            response = requests.get(url, stream=True, headers=DEFAULT_REQUEST_HEADERS)
            response.raise_for_status()
            
            filename = os.path.basename(urlparse(url).path)
            if not filename:
                filename = "video"
            
            file_ext = Path(filename).suffix.lower()
            if not file_ext:
                file_ext = '.mp4'
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp.write(chunk)
                video_path = tmp.name
            
            audio_path = None
            try:
                audio_path = extract_audio_from_video(video_path)
                
                transcript, metadata = transcribe_audio_chunked(
                    audio_path,
                    language=language if language != "auto" else "auto",
                    model_size=model_size,
                    device="auto",
                    compute_type="auto",
                    cpu_threads=0,
                    vad_enabled=True,
                    enable_chunking=True,
                    chunk_duration=60,
                    chunk_overlap=2,
                    auto_enable_threshold=90,
                    beam_size=3,
                    temperature=0.0,
                )
                
                markdown_content = format_transcript_as_markdown(
                    title=filename,
                    transcript=transcript,
                    metadata=metadata,
                    include_metadata=True
                )
                
                return build_convert_response(
                    content=markdown_content,
                    metadata={
                        "source": url,
                        "source_type": "video",
                        "title": filename,
                        "duration": metadata.get("duration"),
                        "language": language if language != "auto" else metadata.get("language"),
                        "model": model_size,
                    },
                    return_format=return_format,
                    filename=f"{Path(filename).stem}.md",
                    request_id=request_id,
                )
            
            finally:
                if os.path.exists(video_path):
                    os.unlink(video_path)
                if audio_path and os.path.exists(audio_path):
                    os.unlink(audio_path)
        
        elif url_type == "image":
            response = requests.get(url, stream=True, headers=DEFAULT_REQUEST_HEADERS)
            response.raise_for_status()
            
            filename = os.path.basename(urlparse(url).path)
            if not filename:
                filename = "image"
            
            file_ext = Path(filename).suffix.lower()
            if not file_ext:
                file_ext = '.jpg'
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp.write(chunk)
                image_path = tmp.name
            
            try:
                enable_plugins = ocr_mode == "true" or (ocr_mode == "auto")
                
                result = md.convert(image_path, enable_plugins=enable_plugins)
                text_content = result.text_content
                
                # ocr_mode=true: always run OCR
                # ocr_mode=auto: run OCR if content is empty/short (likely scanned image)
                # ocr_mode=false: never run OCR
                should_ocr = ocr_mode == "true" or (
                    ocr_mode == "auto" and 
                    (not text_content or len(text_content.strip()) < 10 or text_content.startswith("ImageSize:"))
                )
                
                if should_ocr:
                    try:
                        ocr_result = ocr_image(image_path, ocr_lang)
                        if ocr_result:
                            text_content = f"[OCR Result]\n\n{ocr_result}"
                    except Exception as ocr_error:
                        if API_DEBUG:
                            print(f"Image OCR failed: {ocr_error}")
                
                return build_convert_response(
                    content=text_content,
                    metadata={
                        "source": url,
                        "source_type": "image",
                        "filename": filename,
                        "file_size": os.path.getsize(image_path),
                        "ocr_language": ocr_lang if enable_plugins else None,
                    },
                    return_format=return_format,
                    filename=f"{Path(filename).stem}.md",
                    request_id=request_id,
                )
            
            finally:
                if os.path.exists(image_path):
                    os.unlink(image_path)
        
        elif url_type == "json":
            response = requests.get(url, headers=DEFAULT_REQUEST_HEADERS)
            response.raise_for_status()
            try:
                json_data = response.json()
                json_text = "```json\n" + json.dumps(json_data, indent=2, ensure_ascii=False) + "\n```"
            except Exception:
                json_text = response.text
            
            return build_convert_response(
                content=json_text,
                metadata={
                    "source": url,
                    "source_type": "json",
                    "filename": os.path.basename(urlparse(url).path) or "data.json",
                    "file_size": len(response.content),
                },
                return_format=return_format,
                filename=f"{Path(os.path.basename(urlparse(url).path) or 'data').stem}.md",
                request_id=request_id,
            )
        
        elif url_type == "markdown":
            response = requests.get(url, headers=DEFAULT_REQUEST_HEADERS)
            response.raise_for_status()
            
            return build_convert_response(
                content=response.text,
                metadata={
                    "source": url,
                    "source_type": "markdown",
                    "filename": os.path.basename(urlparse(url).path) or "document.md",
                    "file_size": len(response.content),
                },
                return_format=return_format,
                filename=os.path.basename(urlparse(url).path) or "document.md",
                request_id=request_id,
            )
        
        elif url_type == "text":
            response = requests.get(url, headers=DEFAULT_REQUEST_HEADERS)
            response.raise_for_status()
            
            return build_convert_response(
                content=response.text,
                metadata={
                    "source": url,
                    "source_type": "text",
                    "filename": os.path.basename(urlparse(url).path) or "document.txt",
                    "file_size": len(response.content),
                },
                return_format=return_format,
                filename=f"{Path(os.path.basename(urlparse(url).path) or 'document').stem}.md",
                request_id=request_id,
            )
        
        elif url_type == "webpage":
            # Download webpage content
            response = requests.get(url, headers=DEFAULT_REQUEST_HEADERS)
            response.raise_for_status()
            
            if clean_html:
                html_content = response.content
                text_content = _html_to_markdown(html_content)
            else:
                # Create temporary HTML file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
                    tmp.write(response.content)
                    html_path = tmp.name
                
                try:
                    enable_plugins = ocr_mode == "true"
                    result = md.convert(html_path, enable_plugins=enable_plugins)
                    text_content = result.text_content
                finally:
                    if os.path.exists(html_path):
                        os.unlink(html_path)
            
            return build_convert_response(
                content=text_content,
                metadata={
                    "source": url,
                    "source_type": "webpage",
                    "filename": os.path.basename(urlparse(url).path) or "webpage",
                    "file_size": len(response.content),
                },
                return_format=return_format,
                filename=f"{Path(os.path.basename(urlparse(url).path) or 'webpage').stem}.md",
                request_id=request_id,
            )
        
        else:
            raise HTTPException(
                status_code=400,
                detail=error_response(
                    code=ErrorCodes.UNSUPPORTED_FORMAT,
                    message=f"Unsupported URL type: {url_type}",
                    request_id=request_id
                )
            )
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=400,
            detail=error_response(
                code=ErrorCodes.INTERNAL_ERROR,
                message=f"URL download failed: {str(e)}",
                request_id=request_id
            )
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=error_response(
                code=ErrorCodes.INTERNAL_ERROR,
                message=f"URL processing failed: {str(e)}",
                request_id=request_id
            )
        )


@api_router.post("/convert/clean-html", status_code=200)
async def convert_clean_html(
    url: Optional[str] = Query(None, description="URL to fetch and clean"),
    file: Optional[UploadFile] = File(None, description="HTML file to clean"),
    return_format: str = Query("json", description="Response format: json (default), markdown, or download", pattern="^(json|markdown|download)$"),
):
    request_id = set_request_id()

    try:
        if file is not None:
            html_content = await file.read()
            filename = file.filename or "clean-html"
        elif url:
            try:
                _validate_url_not_private(url)
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=error_response(
                        code=ErrorCodes.INTERNAL_ERROR,
                        message=str(e),
                        request_id=request_id,
                    ),
                )

            response = requests.get(url, timeout=30, headers=DEFAULT_REQUEST_HEADERS)

            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=error_response(
                        code=ErrorCodes.INTERNAL_ERROR,
                        message=f"URL not found (404): {url}",
                        request_id=request_id,
                    ),
                )

            if len(response.content) < 500:
                raise HTTPException(
                    status_code=400,
                    detail=error_response(
                        code=ErrorCodes.INTERNAL_ERROR,
                        message="URL returned insufficient content (likely empty or JavaScript-heavy page)",
                        request_id=request_id,
                    ),
                )

            response.raise_for_status()
            html_content = response.content
            filename = os.path.basename(urlparse(url).path) or "clean-html"
        else:
            raise HTTPException(
                status_code=400,
                detail=error_response(
                    code=ErrorCodes.INTERNAL_ERROR,
                    message="Either 'url' or 'file' parameter is required",
                    request_id=request_id,
                ),
            )

        markdown_content = _html_to_markdown(html_content)

        return build_convert_response(
            content=markdown_content,
            metadata={
                "source": url or (file.filename if file else "unknown"),
                "format": "markdown",
                "file_size": len(html_content),
            },
            return_format=return_format,
            filename=f"{Path(filename).stem}.md",
            request_id=request_id,
        )

    except HTTPException:
        raise
    except requests.RequestException as e:
        raise HTTPException(
            status_code=400,
            detail=error_response(
                code=ErrorCodes.INTERNAL_ERROR,
                message=f"Failed to fetch URL: {str(e)}",
                request_id=request_id,
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=error_response(
                code=ErrorCodes.INTERNAL_ERROR,
                message=f"Clean HTML extraction failed: {str(e)}",
                request_id=request_id,
            ),
        )


# Register API Router
app.include_router(api_router)


# ===== Model Pre-warm =====
from .constants import PRE_WARM_MODELS
from .whisper_transcribe import get_model


def sync_prewarm_models():
    """Synchronously pre-warm models to eliminate cold-start latency."""
    for model_size, device, compute_type, cpu_threads in PRE_WARM_MODELS:
        try:
            get_model(model_size, device, compute_type, cpu_threads=cpu_threads)
        except Exception:
            pass


sync_prewarm_models()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT_INTERNAL", "8000"))
    )
