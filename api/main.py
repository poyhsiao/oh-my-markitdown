from fastapi import FastAPI, File, UploadFile, HTTPException, Query, APIRouter
from fastapi.responses import Response, StreamingResponse
from markitdown import MarkItDown
import tempfile
import os
from pathlib import Path
from datetime import datetime
import io
import subprocess
import re
from urllib.parse import urlparse

# Validate environment variables on startup
from .config import validate_environment, ConfigurationError

# Import unified response format and error codes
from .response import (
    success_response, 
    error_response, 
    ErrorCodes, 
    set_request_id,
    transcribe_response,
    convert_file_response
)

# Import concurrency manager
from .concurrency import get_concurrency_manager

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
    Perform OCR on image-based PDFs.
    
    Some PDFs are scanned documents (image PDFs), which MarkItDown cannot extract text from directly.
    This function:
    1. Uses PyMuPDF to convert PDF pages to high-resolution images
    2. Uses Tesseract OCR to recognize text in the images
    
    Args:
        pdf_path: Path to the PDF file
        ocr_lang: OCR language code (default: chi_tra+eng)
    
    Returns:
        OCR recognized text content
    """
    try:
        import fitz  # PyMuPDF
        from PIL import Image
        
        doc = fitz.open(pdf_path)
        all_text = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Check if page has extractable text
            text = page.get_text()
            if text.strip():
                # If text exists, use it directly
                all_text.append(f"--- Page {page_num + 1} ---\n{text}")
                continue
            
            # No text, use OCR
            # High resolution rendering (3x zoom)
            mat = fitz.Matrix(3, 3)
            pix = page.get_pixmap(matrix=mat)
            
            # Save as temporary image
            temp_img = f"/tmp/page_{page_num}.png"
            pix.save(temp_img)
            
            # Use Tesseract OCR
            result = subprocess.run(
                ["tesseract", temp_img, "stdout", "-l", ocr_lang],
                capture_output=True,
                text=True
            )
            
            ocr_text = result.stdout.strip()
            if ocr_text:
                all_text.append(f"--- Page {page_num + 1} (OCR) ---\n{ocr_text}")
            
            # Clean up temporary image
            try:
                os.unlink(temp_img)
            except:
                pass
        
        doc.close()
        return "\n\n".join(all_text)
    
    except Exception as e:
        raise Exception(f"OCR processing failed: {str(e)}")

app = FastAPI(
    title="MarkItDown API",
    description="Convert various file formats to Markdown via HTTP API with multi-language OCR support and YouTube/Audio transcription",
    version="0.2.0",
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

def get_error_message(key: str, accept_language: str = None) -> str:
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
    """Handle validation errors with language-aware messages."""
    accept_language = request.headers.get("Accept-Language", ERROR_LANG)
    message = get_error_message("validation_error", accept_language)
    
    return Response(
        content=json.dumps({
            "detail": message,
            "errors": exc.errors() if API_DEBUG else None
        }),
        status_code=400,
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
    return_format: str = Query("markdown", description="Response format: markdown or json", pattern="^(markdown|json)$")
):
    """
    Upload a file and convert it to Markdown.
    
    - **file**: File to convert (supports PDF, DOCX, PPTX, XLSX, images, audio, etc.)
    - **enable_ocr**: Enable OCR (default: false)
    - **ocr_lang**: OCR language (default: environment variable DEFAULT_OCR_LANG, supports chi_tra, chi_sim, eng, jpn, kor, tha, vie, combinable with +)
    - **return_format**: Response format (markdown or json)
    
    Returns:
    - **markdown**: Returns Markdown text directly (Content-Type: text/markdown)
    - **json**: Returns JSON with metadata and content
    """
    
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
            
            # Special handling: If image and OCR enabled, use Tesseract
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
            if file_ext in image_extensions and enable_plugins:
                if API_DEBUG:
                    print(f"Image OCR processing...")
                
                try:
                    ocr_result = subprocess.run(
                        ["tesseract", tmp_path, "stdout", "-l", ocr_lang or DEFAULT_OCR_LANG],
                        capture_output=True,
                        text=True
                    )
                    ocr_text = ocr_result.stdout.strip()
                    if ocr_text and len(ocr_text) > len(text_content.strip()):
                        text_content = f"[OCR Result]\n\n{ocr_text}"
                        if API_DEBUG:
                            print(f"Image OCR successful: {len(text_content)} characters")
                except Exception as ocr_error:
                    if API_DEBUG:
                        print(f"Image OCR failed: {ocr_error}")
            
            if return_format == "markdown":
                # Return Markdown text directly (ensure UTF-8 encoding)
                # HTTP headers must be ASCII/latin-1, cannot contain Chinese
                # Use URL encoding for filename
                from urllib.parse import quote
                safe_filename = quote(file.filename or "unknown", safe='')
                
                return Response(
                    content=text_content.encode('utf-8'),
                    media_type="text/markdown; charset=utf-8",
                    headers={
                        "X-Original-Filename": safe_filename,
                        "X-Conversion-Time": datetime.now().isoformat(),
                        "X-OCR-Language": ocr_lang if enable_plugins else "N/A",
                        # Use ASCII safe characters for filename to avoid encoding issues
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
async def convert_file_legacy(
    file: UploadFile = File(..., description="File to convert"),
    enable_ocr: bool = Query(False, description="Enable OCR, default false"),
    ocr_lang: str = Query("chi_tra+eng", description="OCR language code, default chi_tra+eng, use + to combine multiple languages"),
    return_format: str = Query("markdown", description="Response format: markdown or json", pattern="^(markdown|json)$")
):
    """Legacy endpoint for backward compatibility. Redirects to /convert/file."""
    return await convert_file_endpoint(file, enable_ocr, ocr_lang, return_format)


# ==================== Whisper Transcription Endpoints ====================

from .whisper_transcribe import (
    transcribe_audio,
    transcribe_youtube_video,
    transcribe_with_formats,
    extract_audio_from_video,
    format_transcript_as_markdown,
    SUPPORTED_LANGUAGES
)
from .response import success_response, transcribe_response, ErrorCodes
from .concurrency import get_concurrency_manager

@api_router.post("/convert/youtube")
async def transcribe_youtube(
    url: str = Query(..., description="YouTube video URL"),
    language: str = Query("zh", description="Language code (zh, en, ja, ko, etc.)"),
    model_size: str = Query("base", description="Model size (tiny, base, small, medium, large)"),
    return_format: str = Query("markdown", description="Response format: markdown or json"),
    include_timestamps: bool = Query(False, description="Include timestamps"),
    include_metadata: bool = Query(True, description="Include metadata")
):
    """
    Download YouTube video audio and transcribe using Whisper.
    
    - **url**: YouTube video URL
    - **language**: Language code (zh=Chinese, en=English, ja=Japanese, ko=Korean)
    - **model_size**: Model size (tiny fastest, large most accurate)
    - **return_format**: Response format
    - **include_metadata**: Include transcription metadata
    """
    
    # Set request ID
    request_id = set_request_id()
    
    # ===== CONCURRENCY CONTROL INTEGRATION =====
    # Get concurrency manager
    manager = get_concurrency_manager()
    
    # Wait for processing slot with timeout
    acquired, queue_item = await manager.wait_for_slot(
        request_type="youtube",
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
        # Transcribe YouTube video
        result = transcribe_youtube_video(
            url=url,
            language=language,
            model_size=model_size
        )
        
        # Format as Markdown
        markdown_content = format_transcript_as_markdown(
            title=result["title"],
            transcript=result["transcript"],
            metadata=result["metadata"],
            include_metadata=include_metadata
        )
        
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
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )


@api_router.post("/convert/audio")
async def transcribe_audio_file(
    file: UploadFile = File(..., description="Audio file"),
    language: str = Query("zh", description="Language code"),
    model_size: str = Query("base", description="Model size"),
    return_format: str = Query("markdown", description="Response format"),
    include_timestamps: bool = Query(False, description="Include timestamps")
):
    """
    Upload audio file and transcribe using Whisper.
    
    - **file**: Audio file (MP3, WAV, M4A, FLAC, etc.)
    - **language**: Language code
    - **model_size**: Model size
    - **return_format**: Response format
    """
    
    try:
        # Save uploaded file
        suffix = Path(file.filename or "").suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Transcribe
            transcript, metadata = transcribe_audio(
                tmp_path,
                language=language,
                model_size=model_size
            )
            
            # Format
            markdown_content = format_transcript_as_markdown(
                title=file.filename or "Audio Transcription",
                transcript=transcript,
                metadata=metadata
            )
            
            if return_format == "markdown":
                return Response(
                    content=markdown_content.encode('utf-8'),
                    media_type="text/markdown; charset=utf-8",
                    headers={
                        "X-Filename": file.filename or "unknown",
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
        
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )


@api_router.post("/convert/video")
async def transcribe_video_file(
    file: UploadFile = File(..., description="Video file (MP4, MKV, WebM, AVI, MOV, FLV, TS)"),
    language: str = Query("auto", description="Language code (auto=auto-detect)"),
    model_size: str = Query("base", description="Model size"),
    output_formats: str = Query("markdown", description="Output formats (comma-separated, e.g.: markdown,srt,vtt)"),
    include_timestamps: bool = Query(False, description="Include timestamps in Markdown")
):
    """
    Upload video file and transcribe using Whisper.
    
    - **file**: Video file (MP4, MKV, WebM, AVI, MOV, FLV, TS)
    - **language**: Language code
    - **model_size**: Model size
    - **output_formats**: Output formats (comma-separated, e.g.: markdown,srt,vtt)
    - **include_timestamps**: Include timestamps in Markdown
    """
    
    # Validate video file type
    allowed_video_extensions = {
        '.mp4', '.mkv', '.webm', '.avi', '.mov', '.flv', '.ts'
    }
    
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in allowed_video_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video type: {file_ext}. Supported types: {', '.join(allowed_video_extensions)}"
        )
    
    try:
        # Save uploaded video file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            content = await file.read()
            tmp.write(content)
            video_path = tmp.name
        
        audio_path = None
        
        try:
            # Extract audio
            audio_path = extract_audio_from_video(video_path)
            
            # Transcribe and generate multiple formats
            formats_dict, metadata = transcribe_with_formats(
                audio_path,
                language=language,
                model_size=model_size,
                output_formats=output_formats,
                include_timestamps=include_timestamps
            )
            
            # Use unified response format
            return transcribe_response(
                formats=formats_dict,
                default_format="markdown",
                source_type="video",
                title=file.filename or "Video Transcription",
                duration=metadata.get("duration"),
                language=language,
                model=model_size
            )
        
        finally:
            # Clean up temporary file
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
            "version": "0.2.0",
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

def detect_url_type(url: str, type_hint: str = "auto") -> str:
    """
    Detect URL type based on URL pattern or type hint.

    Args:
        url: URL to analyze
        type_hint: Type hint to override detection (auto/youtube/document/audio/video/webpage)

    Returns:
        Detected type: youtube, document, audio, video, webpage
    """
    # If type_hint is provided and not auto, use it directly
    if type_hint != "auto":
        valid_types = ["youtube", "document", "audio", "video", "webpage"]
        if type_hint in valid_types:
            return type_hint
        # Invalid type_hint, fall through to auto-detection

    # Auto-detect based on URL pattern
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.lower()

    # YouTube detection
    if "youtube.com" in domain or "youtu.be" in domain:
        return "youtube"

    # Document file extensions
    doc_extensions = {'.pdf', '.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls', '.odt', '.ods', '.odp'}
    if any(path.endswith(ext) for ext in doc_extensions):
        return "document"

    # Audio file extensions
    audio_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma'}
    if any(path.endswith(ext) for ext in audio_extensions):
        return "audio"

    # Video file extensions
    video_extensions = {'.mp4', '.mkv', '.webm', '.avi', '.mov', '.flv', '.ts', '.wmv'}
    if any(path.endswith(ext) for ext in video_extensions):
        return "video"

    # Default to webpage
    return "webpage"


@api_router.post("/convert/url")
async def convert_url(
    url: str = Query(..., description="URL address"),
    type_hint: str = Query("auto", description="Type hint: auto/youtube/document/audio/video/webpage"),
    language: str = Query("auto", description="Transcription language (auto=auto-detect)"),
    model_size: str = Query("base", description="Whisper model size"),
    ocr_lang: str = Query(DEFAULT_OCR_LANG, description="OCR language"),
    output_formats: str = Query("markdown", description="Output formats (comma-separated)"),
    include_timestamps: bool = Query(False, description="Include timestamps in Markdown")
):
    """
    Unified URL endpoint - auto-detects URL type and processes accordingly.
    
    - **url**: URL address
    - **type_hint**: Type hint (overrides auto-detection)
    - **language**: Transcription language (auto=auto-detect)
    - **model_size**: Whisper model size (tiny, base, small, medium, large)
    - **ocr_lang**: OCR language (default: environment variable DEFAULT_OCR_LANG)
    - **output_formats**: Output formats (comma-separated, e.g.: markdown,srt,vtt)
    - **include_timestamps**: Include timestamps in Markdown
    
    Supported types:
    - youtube: YouTube video transcription
    - document: Document conversion (PDF, DOCX, etc.)
    - audio: Audio file transcription
    - video: Video file transcription
    - webpage: Webpage content conversion
    """
    
    # Set request ID
    request_id = set_request_id()
    
    try:
        # Detect URL type
        url_type = detect_url_type(url, type_hint)
        
        if url_type == "youtube":
            # YouTube video transcription
            result = transcribe_youtube_video(
                url=url,
                language=language if language != "auto" else None,
                model_size=model_size
            )
            
            # Format output
            formats_list = [f.strip() for f in output_formats.split(",")]
            formats_dict = {}
            
            # Generate Markdown format
            markdown_content = format_transcript_as_markdown(
                title=result["title"],
                transcript=result["transcript"],
                metadata=result["metadata"],
                include_metadata=True,
                include_timestamps=include_timestamps
            )
            formats_dict["markdown"] = markdown_content
            
            # Generate other formats (if needed)
            if "srt" in formats_list or "vtt" in formats_list:
                # Use transcribe_with_formats to generate multiple formats
                # Need to download audio first
                import tempfile
                import os
                from .youtube_grabber import download_youtube_audio
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                    audio_path = download_youtube_audio(url, tmp.name)
                    
                    try:
                        formats_dict, metadata = transcribe_with_formats(
                            audio_path,
                            language=language if language != "auto" else None,
                            model_size=model_size,
                            output_formats=output_formats,
                            include_timestamps=include_timestamps
                        )
                    finally:
                        if os.path.exists(audio_path):
                            os.unlink(audio_path)
            
            return transcribe_response(
                formats=formats_dict,
                default_format="markdown",
                source_type="youtube",
                title=result["title"],
                duration=result["metadata"].get("duration"),
                language=language if language != "auto" else result["metadata"].get("language"),
                model=model_size,
                request_id=request_id
            )
            
        elif url_type == "document":
            # Document conversion - use MarkItDown to process URL
            # Need to download file to temporary location
            import tempfile
            import os
            import requests
            
            # Download file
            response = requests.get(url, stream=True)
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
                # Convert using MarkItDown
                result = md.convert(tmp_path, enable_plugins=True)
                text_content = result.text_content
                
                # Special handling: if PDF and content is empty, try OCR
                if file_ext == '.pdf' and (not text_content or len(text_content.strip()) < 10):
                    try:
                        ocr_result = ocr_image_pdf(tmp_path, ocr_lang)
                        if ocr_result and len(ocr_result.strip()) > len(text_content.strip()):
                            text_content = f"[OCR Result]\n\n{ocr_result}"
                    except Exception as ocr_error:
                        if API_DEBUG:
                            print(f"OCR failed: {ocr_error}")
                
                return convert_file_response(
                    content=text_content,
                    format="markdown",
                    filename=filename,
                    file_size=os.path.getsize(tmp_path),
                    conversion_time=datetime.now().isoformat(),
                    ocr_language=ocr_lang,
                    request_id=request_id
                )
            
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        elif url_type == "audio":
            # Audio file transcription
            import tempfile
            import os
            import requests
            
            # Download audio file
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Get filename from URL
            filename = os.path.basename(urlparse(url).path)
            if not filename:
                filename = "audio"
            
            # Determine file extension
            file_ext = Path(filename).suffix.lower()
            if not file_ext:
                file_ext = '.mp3'  # Default
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp.write(chunk)
                audio_path = tmp.name
            
            try:
                # Transcribe audio
                formats_list = [f.strip() for f in output_formats.split(",")]
                
                if len(formats_list) == 1 and formats_list[0] == "markdown":
                    # Simple transcription, only generate Markdown
                    transcript, metadata = transcribe_audio(
                        audio_path,
                        language=language if language != "auto" else None,
                        model_size=model_size
                    )
                    
                    markdown_content = format_transcript_as_markdown(
                        title=filename,
                        transcript=transcript,
                        metadata=metadata,
                        include_metadata=True,
                        include_timestamps=include_timestamps
                    )
                    
                    formats_dict = {"markdown": markdown_content}
                else:
                    # Multiple format transcription
                    formats_dict, metadata = transcribe_with_formats(
                        audio_path,
                        language=language if language != "auto" else None,
                        model_size=model_size,
                        output_formats=output_formats,
                        include_timestamps=include_timestamps
                    )
                
                return transcribe_response(
                    formats=formats_dict,
                    default_format="markdown",
                    source_type="audio",
                    title=filename,
                    duration=metadata.get("duration"),
                    language=language if language != "auto" else metadata.get("language"),
                    model=model_size,
                    request_id=request_id
                )
            
            finally:
                if os.path.exists(audio_path):
                    os.unlink(audio_path)
        
        elif url_type == "video":
            # Video file transcription
            import tempfile
            import os
            import requests
            
            # Download video file
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Get filename from URL
            filename = os.path.basename(urlparse(url).path)
            if not filename:
                filename = "video"
            
            # Determine file extension
            file_ext = Path(filename).suffix.lower()
            if not file_ext:
                file_ext = '.mp4'  # Default
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp.write(chunk)
                video_path = tmp.name
            
            audio_path = None
            try:
                # Extract audio
                audio_path = extract_audio_from_video(video_path)
                
                # Transcribe and generate multiple formats
                formats_dict, metadata = transcribe_with_formats(
                    audio_path,
                    language=language if language != "auto" else None,
                    model_size=model_size,
                    output_formats=output_formats,
                    include_timestamps=include_timestamps
                )
                
                return transcribe_response(
                    formats=formats_dict,
                    default_format="markdown",
                    source_type="video",
                    title=filename,
                    duration=metadata.get("duration"),
                    language=language if language != "auto" else metadata.get("language"),
                    model=model_size,
                    request_id=request_id
                )
            
            finally:
                if os.path.exists(video_path):
                    os.unlink(video_path)
                if audio_path and os.path.exists(audio_path):
                    os.unlink(audio_path)
        
        elif url_type == "webpage":
            # Webpage content conversion
            import requests
            from markitdown import MarkItDown
            
            # Download webpage content
            response = requests.get(url)
            response.raise_for_status()
            
            # Create temporary HTML file
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
                tmp.write(response.content)
                html_path = tmp.name
            
            try:
                # Convert HTML using MarkItDown
                result = md.convert(html_path, enable_plugins=False)
                text_content = result.text_content
                
                return convert_file_response(
                    content=text_content,
                    format="markdown",
                    filename=os.path.basename(urlparse(url).path) or "webpage",
                    file_size=len(response.content),
                    conversion_time=datetime.now().isoformat(),
                    ocr_language=None,
                    request_id=request_id
                )
            
            finally:
                if os.path.exists(html_path):
                    os.unlink(html_path)
        
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


# Register API Router
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT_INTERNAL", "8000"))
    )
