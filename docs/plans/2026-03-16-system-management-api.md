# MarkItDown System Management API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement comprehensive system management APIs for cleanup, storage monitoring, cache management, and configuration control with full logging and error handling.

**Architecture:** Modular design with constants extraction, middleware layer for logging/timeout, system module for management APIs, and CLI scripts for manual operations.

**Tech Stack:** Python 3.12, FastAPI, psutil, uvicorn, Docker

---

## Phase 1: Foundation (Constants & Environment)

### Task 1: Create Constants Module

**Files:**
- Create: `api/constants.py`
- Modify: `api/main.py` (import constants)
- Test: `tests/api/test_constants.py`

**Step 1: Write constants module**

```python
"""
MarkItDown API Constants
Centralized constants to avoid duplication across modules.
"""

# Supported file extensions for conversion
SUPPORTED_EXTENSIONS = {
    '.pdf', '.docx', '.doc', '.pptx', '.ppt',
    '.xlsx', '.xls', '.html', '.htm', '.csv',
    '.json', '.xml', '.zip', '.epub', '.msg',
    '.jpg', '.jpeg', '.png', '.gif', '.webp',
    '.mp3', '.wav', '.m4a', '.flac'
}

# OCR language codes
OCR_LANGUAGES = {
    "chi_sim": "簡體中文",
    "chi_tra": "繁體中文",
    "eng": "英文",
    "jpn": "日文",
    "kor": "韓文",
    "tha": "泰文",
    "vie": "越南文",
}

# Whisper transcription languages
SUPPORTED_LANGUAGES = {
    "zh": "中文",
    "zh-TW": "繁體中文",
    "zh-CN": "簡體中文",
    "en": "英文",
    "ja": "日文",
    "ko": "韓文",
    "fr": "法文",
    "de": "德文",
    "es": "西班牙文",
    "pt": "葡萄牙文",
    "ru": "俄文",
    "ar": "阿拉伯文",
    "hi": "印地文",
    "th": "泰文",
    "vi": "越南文",
}

# Cleanup type constants
CLEANUP_TYPES = {
    "youtube": "YouTube audio files",
    "ocr": "OCR temporary images",
    "uploads": "Upload temporary files",
    "models": "Whisper model cache",
    "failed": "Failed conversion files",
    "all": "All of the above",
}
```

**Step 2: Run test to verify constants import**

```bash
cd .worktrees/system-management-api
python -c "from api.constants import SUPPORTED_EXTENSIONS, OCR_LANGUAGES; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add api/constants.py
git commit -m "feat: add centralized constants module"
```

---

### Task 2: Update Environment Variables Configuration

**Files:**
- Modify: `.env.example` (add new variables)
- Create: `docs/ENVIRONMENT.md` (documentation)
- Test: Manual verification

**Step 1: Add new environment variables to .env.example**

```bash
# Append to .env.example
```

**Step 2: Update .env.example with new variables**

Add these sections:

```bash
# ===== System Management =====
API_KEY=                    # Optional API key for system management endpoints

# ===== Logging Configuration =====
LOG_FORMAT=text             # Output format: text / json
LOG_OUTPUT=stdout           # Output target: stdout / file / stdout,file
LOG_FILE=/var/log/markitdown.log  # Log file path (when LOG_OUTPUT=file)
LOG_FILE_MAX_SIZE=10m       # Max size per log file
LOG_FILE_MAX_COUNT=3        # Number of log files to keep

# ===== Error Messages =====
ERROR_LANG=zh-TW            # Error message language: zh-TW / en

# ===== Timeout Configuration =====
CONVERT_TIMEOUT=300         # File conversion timeout (seconds)
YOUTUBE_TRANSCRIBE_TIMEOUT=600  # YouTube transcription timeout
AUDIO_TRANSCRIBE_TIMEOUT=600    # Audio transcription timeout

# ===== Retry Configuration =====
AUTO_MAX_RETRIES=3          # Maximum retry attempts
AUTO_RETRY_BASE_DELAY=2     # Base delay (seconds) for exponential backoff
AUTO_RETRY_MAX_DELAY=60     # Maximum delay between retries

# ===== Cache Configuration =====
WHISPER_MODEL_CACHE_SIZE=3  # Maximum number of cached Whisper models

# ===== Temporary Directory =====
TEMP_DIR=/tmp               # Root directory for temporary files
```

**Step 3: Commit**

```bash
git add .env.example
git commit -m "docs: add new environment variables for system management"
```

---

### Task 3: Update Existing Modules to Use Constants

**Files:**
- Modify: `api/main.py` (import from constants)
- Modify: `api/auto_convert.py` (import from constants)
- Modify: `cli.py` (import from constants)
- Test: `python -m pytest tests/ -v`

**Step 1: Update api/main.py imports**

Replace:
```python
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', ...}
OCR_LANGUAGES = {...}
```

With:
```python
from .constants import SUPPORTED_EXTENSIONS, OCR_LANGUAGES
```

**Step 2: Update api/auto_convert.py imports**

Replace local `SUPPORTED_EXTENSIONS` with import from constants.

**Step 3: Update cli.py imports**

Replace local `SUPPORTED_EXTENSIONS` with import from constants.

**Step 4: Verify imports work**

```bash
python -c "from api.main import app; print('main.py OK')"
python -c "from api.auto_convert import convert_file; print('auto_convert.py OK')"
python -c "import cli; print('cli.py OK')"
```

Expected: All print OK statements

**Step 5: Commit**

```bash
git add api/main.py api/auto_convert.py cli.py
git commit -m "refactor: use centralized constants across modules"
```

---

## Phase 2: Logging & Error Handling

### Task 4: Implement Logging Middleware

**Files:**
- Create: `api/middleware.py`
- Modify: `api/main.py` (add middleware)
- Test: `tests/api/test_middleware.py`

**Step 1: Create logging middleware**

```python
"""
Request logging middleware with configurable format.
"""
import logging
import time
import uuid
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import os

# Configuration from environment
LOG_FORMAT = os.getenv("LOG_FORMAT", "text").lower()
LOG_OUTPUT = os.getenv("LOG_OUTPUT", "stdout")
LOG_FILE = os.getenv("LOG_FILE", "/var/log/markitdown.log")

# Configure logging
def setup_logging():
    """Configure logging based on environment variables."""
    log_handlers = []
    
    # Console handler
    if "stdout" in LOG_OUTPUT:
        console_handler = logging.StreamHandler()
        log_handlers.append(console_handler)
    
    # File handler
    if "file" in LOG_OUTPUT:
        from logging.handlers import RotatingFileHandler
        max_bytes = parse_size(os.getenv("LOG_FILE_MAX_SIZE", "10m"))
        backup_count = int(os.getenv("LOG_FILE_MAX_COUNT", "3"))
        file_handler = RotatingFileHandler(
            LOG_FILE, 
            maxBytes=max_bytes, 
            backupCount=backup_count
        )
        log_handlers.append(file_handler)
    
    # Format based on LOG_FORMAT
    if LOG_FORMAT == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Setup root logger
    logger = logging.getLogger("markitdown-api")
    logger.setLevel(logging.INFO)
    
    for handler in log_handlers:
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

class JsonFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id
        if hasattr(record, 'method'):
            log_data["method"] = record.method
        if hasattr(record, 'path'):
            log_data["path"] = record.path
        if hasattr(record, 'status'):
            log_data["status"] = record.status
        if hasattr(record, 'duration_ms'):
            log_data["duration_ms"] = record.duration_ms
        return json.dumps(log_data)

def parse_size(size_str):
    """Parse size string like '10m' to bytes."""
    size_str = size_str.lower().strip()
    multipliers = {'k': 1024, 'm': 1024**2, 'g': 1024**3}
    
    for suffix, multiplier in multipliers.items():
        if size_str.endswith(suffix):
            return int(float(size_str[:-1]) * multiplier)
    
    return int(size_str)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests with configurable format."""
    
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Get content length
        content_length = 0
        try:
            content_length = int(request.headers.get("content-length", 0))
        except:
            pass
        
        # Log request
        logger = logging.getLogger("markitdown-api")
        extra = {
            'request_id': request_id,
            'method': request.method,
            'path': request.url.path,
        }
        
        logger.info(
            f"[{request_id}] → {request.method} {request.url.path} "
            f"(ip={client_ip}, size={content_length})",
            extra=extra
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Get response size
        response_size = 0
        try:
            response_size = int(response.headers.get("content-length", 0))
        except:
            pass
        
        # Log response
        extra['status'] = response.status_code
        extra['duration_ms'] = round(duration_ms, 2)
        extra['response_size'] = response_size
        
        logger.info(
            f"[{request_id}] ← {response.status_code} "
            f"({duration_ms:.2f}ms, size={response_size})",
            extra=extra
        )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
```

**Step 2: Add middleware to api/main.py**

```python
from .middleware import RequestLoggingMiddleware, setup_logging

# Setup logging
logger = setup_logging()

# Add middleware
app.add_middleware(RequestLoggingMiddleware)
```

**Step 3: Write test for middleware**

```python
# tests/api/test_middleware.py
def test_request_logging():
    """Test that requests are logged with request ID."""
    from fastapi.testclient import TestClient
    from api.main import app
    
    client = TestClient(app)
    response = client.get("/health")
    
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
```

**Step 4: Run test**

```bash
python -m pytest tests/api/test_middleware.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add api/middleware.py api/main.py tests/api/test_middleware.py
git commit -m "feat: add configurable request logging middleware"
```

---

### Task 5: Implement Error Handling Middleware

**Files:**
- Modify: `api/main.py` (add error handlers)
- Test: `tests/api/test_error_handling.py`

**Step 1: Add error language configuration**

```python
# api/main.py - add after imports
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
    # Priority: Accept-Language header > ERROR_LANG env var
    lang = accept_language if accept_language else ERROR_LANG
    if lang not in ERROR_MESSAGES:
        lang = "en"  # Fallback to English
    return ERROR_MESSAGES.get(lang, {}).get(key, "Unknown error")
```

**Step 2: Add custom exception handler**

```python
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
import logging

logger = logging.getLogger("markitdown-api")

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
```

**Step 3: Write tests**

```python
# tests/api/test_error_handling.py
def test_404_empty_response():
    """Test that 404 returns empty response."""
    from fastapi.testclient import TestClient
    from api.main import app
    
    client = TestClient(app)
    response = client.get("/nonexistent-path")
    
    assert response.status_code == 404
    assert response.content == b""

def test_internal_error_hides_details():
    """Test that internal errors hide details in production."""
    import os
    os.environ["API_DEBUG"] = "false"
    
    from fastapi.testclient import TestClient
    from api.main import app
    
    client = TestClient(app)
    # Trigger an internal error somehow
    response = client.post("/api/v1/convert", files={"file": ("test.txt", b"invalid")})
    
    assert response.status_code == 500
    assert "detail" in response.json()
    # Should not contain stack trace
    assert "Traceback" not in response.text
```

**Step 4: Run tests**

```bash
python -m pytest tests/api/test_error_handling.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add api/main.py tests/api/test_error_handling.py
git commit -m "feat: add language-aware error handling with production safety"
```

---

## Phase 3: System Management Module

### Task 6: Create System Management Module

**Files:**
- Create: `api/system.py`
- Modify: `api/main.py` (mount system router)
- Test: `tests/api/test_system.py`

**Step 1: Create system management module skeleton**

```python
"""
System Management API Module
Provides endpoints for cleanup, storage monitoring, cache management, and configuration.
"""
from fastapi import APIRouter, HTTPException, Header, Query
from fastapi.responses import Response
import os
import psutil
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import json

api_router = APIRouter(prefix="/api/v1/system")

# Configuration from environment
API_KEY = os.getenv("API_KEY", "")
TEMP_DIR = os.getenv("TEMP_DIR", "/tmp")
WHISPER_MODEL_CACHE_SIZE = int(os.getenv("WHISPER_MODEL_CACHE_SIZE", "3"))

def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key if configured."""
    if not API_KEY:
        return  # No API key configured, skip auth
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
```

**Step 2: Add storage query endpoint**

```python
@api_router.get("/storage")
async def get_storage_info(
    x_api_key: Optional[str] = Header(None)
):
    """
    Query current storage usage across all temporary directories.
    
    Returns detailed breakdown by category:
    - youtube_audio: YouTube downloaded audio files
    - ocr_temp: OCR temporary images
    - uploads: Upload temporary files
    - models: Whisper model cache (memory)
    """
    verify_api_key(x_api_key)
    
    result = {
        "total_bytes": 0,
        "total_mb": 0,
        "breakdown": {},
        "models": {
            "cached_count": 0,
            "estimated_memory_mb": 0
        }
    }
    
    # Calculate youtube audio files
    youtube_bytes = 0
    youtube_files = 0
    try:
        for f in Path(TEMP_DIR).glob("*.mp3"):
            if f.is_file():
                youtube_bytes += f.stat().st_size
                youtube_files += 1
    except:
        pass
    
    result["breakdown"]["youtube_audio"] = {
        "bytes": youtube_bytes,
        "mb": round(youtube_bytes / 1024 / 1024, 2),
        "files": youtube_files
    }
    
    # Calculate OCR temp images
    ocr_bytes = 0
    ocr_files = 0
    try:
        for f in Path(TEMP_DIR).glob("page_*.png"):
            if f.is_file():
                ocr_bytes += f.stat().st_size
                ocr_files += 1
    except:
        pass
    
    result["breakdown"]["ocr_temp"] = {
        "bytes": ocr_bytes,
        "mb": round(ocr_bytes / 1024 / 1024, 2),
        "files": ocr_files
    }
    
    # Calculate upload temp files
    upload_bytes = 0
    upload_files = 0
    try:
        for f in Path(TEMP_DIR).glob("temp_*"):
            if f.is_file():
                upload_bytes += f.stat().st_size
                upload_files += 1
    except:
        pass
    
    result["breakdown"]["uploads"] = {
        "bytes": upload_bytes,
        "mb": round(upload_bytes / 1024 / 1024, 2),
        "files": upload_files
    }
    
    # Calculate failed files
    failed_bytes = 0
    failed_files = 0
    try:
        failed_dir = Path(TEMP_DIR) / ".failed"
        if failed_dir.exists():
            for f in failed_dir.iterdir():
                if f.is_file() and not f.name.endswith(".error"):
                    failed_bytes += f.stat().st_size
                    failed_files += 1
    except:
        pass
    
    result["breakdown"]["failed"] = {
        "bytes": failed_bytes,
        "mb": round(failed_bytes / 1024 / 1024, 2),
        "files": failed_files
    }
    
    # Get model cache info (import from whisper_transcribe)
    try:
        from .whisper_transcribe import get_model_cache_info
        cache_info = get_model_cache_info()
        result["models"] = cache_info
    except:
        pass
    
    # Calculate total
    result["total_bytes"] = (
        youtube_bytes + ocr_bytes + upload_bytes + failed_bytes
    )
    result["total_mb"] = round(result["total_bytes"] / 1024 / 1024, 2)
    
    return result
```

**Step 3: Add cleanup endpoint**

```python
@api_router.post("/cleanup")
async def cleanup_temp_files(
    request_body: dict,
    x_api_key: Optional[str] = Header(None)
):
    """
    Clean up temporary files by category.
    
    Request body:
    {
        "types": ["youtube", "ocr", "uploads", "models", "failed", "all"]
    }
    
    Default: all types
    """
    verify_api_key(x_api_key)
    
    types = request_body.get("types", ["all"])
    if "all" in types:
        types = ["youtube", "ocr", "uploads", "models", "failed"]
    
    result = {
        "success": True,
        "cleaned": {},
        "total_freed_bytes": 0,
        "total_freed_mb": 0
    }
    
    total_freed = 0
    
    # Clean youtube audio
    if "youtube" in types:
        freed = 0
        count = 0
        try:
            for f in Path(TEMP_DIR).glob("*.mp3"):
                if f.is_file():
                    freed += f.stat().st_size
                    f.unlink()
                    count += 1
        except Exception as e:
            pass
        
        result["cleaned"]["youtube_audio"] = {
            "files": count,
            "bytes": freed
        }
        total_freed += freed
    
    # Clean OCR temp images
    if "ocr" in types:
        freed = 0
        count = 0
        try:
            for f in Path(TEMP_DIR).glob("page_*.png"):
                if f.is_file():
                    freed += f.stat().st_size
                    f.unlink()
                    count += 1
        except:
            pass
        
        result["cleaned"]["ocr_temp"] = {
            "files": count,
            "bytes": freed
        }
        total_freed += freed
    
    # Clean upload temp files
    if "uploads" in types:
        freed = 0
        count = 0
        try:
            for f in Path(TEMP_DIR).glob("temp_*"):
                if f.is_file():
                    freed += f.stat().st_size
                    f.unlink()
                    count += 1
        except:
            pass
        
        result["cleaned"]["uploads"] = {
            "files": count,
            "bytes": freed
        }
        total_freed += freed
    
    # Clean failed files
    if "failed" in types:
        freed = 0
        count = 0
        try:
            failed_dir = Path(TEMP_DIR) / ".failed"
            if failed_dir.exists():
                for f in failed_dir.iterdir():
                    if f.is_file():
                        freed += f.stat().st_size
                        f.unlink()
                        count += 1
        except:
            pass
        
        result["cleaned"]["failed"] = {
            "files": count,
            "bytes": freed
        }
        total_freed += freed
    
    # Clear model cache
    if "models" in types:
        try:
            from .whisper_transcribe import clear_model_cache
            freed_mb = clear_model_cache()
            result["cleaned"]["models"] = {
                "cleared": freed_mb,
                "freed_memory_mb": freed_mb
            }
            total_freed += freed_mb * 1024 * 1024
        except:
            pass
    
    result["total_freed_bytes"] = total_freed
    result["total_freed_mb"] = round(total_freed / 1024 / 1024, 2)
    
    return result
```

**Step 4: Mount router in api/main.py**

```python
from .system import api_router as system_router

# Mount system router
app.include_router(system_router)
```

**Step 5: Write tests**

```python
# tests/api/test_system.py
def test_storage_endpoint():
    """Test storage query endpoint."""
    from fastapi.testclient import TestClient
    from api.main import app
    
    client = TestClient(app)
    response = client.get("/api/v1/system/storage")
    
    assert response.status_code == 200
    data = response.json()
    assert "total_bytes" in data
    assert "breakdown" in data

def test_cleanup_endpoint():
    """Test cleanup endpoint."""
    from fastapi.testclient import TestClient
    from api.main import app
    
    client = TestClient(app)
    response = client.post(
        "/api/v1/system/cleanup",
        json={"types": ["all"]}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "cleaned" in data
```

**Step 6: Run tests**

```bash
python -m pytest tests/api/test_system.py -v
```

Expected: PASS

**Step 7: Commit**

```bash
git add api/system.py api/main.py tests/api/test_system.py
git commit -m "feat: add system management API for storage and cleanup"
```

---

### Task 7: Add Model Cache Management Endpoints

**Files:**
- Modify: `api/system.py` (add cache endpoints)
- Modify: `api/whisper_transcribe.py` (add cache management functions)
- Test: `tests/api/test_cache.py`

**Step 1: Update whisper_transcribe.py with LRU cache**

```python
# Add to api/whisper_transcribe.py
import psutil
from typing import Dict, List

class ModelCache:
    """LRU model cache with size limit."""
    
    def __init__(self, max_size: int = 3):
        self._cache: Dict[str, WhisperModel] = {}
        self._order: List[str] = []
        self._max_size = max_size
    
    def get(self, key: str):
        if key in self._cache:
            self._order.remove(key)
            self._order.append(key)
            return self._cache[key]
        return None
    
    def set(self, key: str, model):
        if key in self._cache:
            return
        
        if len(self._cache) >= self._max_size:
            oldest_key = self._order.pop(0)
            del self._cache[oldest_key]
            print(f"[Whisper] Cache full, removed: {oldest_key}")
        
        self._cache[key] = model
        self._order.append(key)
    
    def clear(self) -> int:
        """Clear all cached models, return count cleared."""
        count = len(self._cache)
        self._cache.clear()
        self._order.clear()
        return count
    
    def remove(self, key: str) -> bool:
        """Remove specific model from cache."""
        if key in self._cache:
            del self._cache[key]
            self._order.remove(key)
            return True
        return False
    
    def get_info(self) -> dict:
        """Get cache information."""
        # Estimate memory using psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        return {
            "cached_count": len(self._cache),
            "max_size": self._max_size,
            "models": [
                {"key": key, "loaded_at": "unknown"}
                for key in self._order
            ],
            "estimated_memory_mb": round(memory_mb, 2)
        }

# Global cache instance
_model_cache = ModelCache(max_size=WHISPER_MODEL_CACHE_SIZE)

def get_model_cache_info():
    """Get cache information for API."""
    return _model_cache.get_info()

def clear_model_cache() -> int:
    """Clear all cached models."""
    return _model_cache.clear()

def remove_model_from_cache(key: str) -> bool:
    """Remove specific model from cache."""
    return _model_cache.remove(key)

def update_cache_max_size(max_size: int):
    """Update cache max size."""
    _model_cache._max_size = max_size
    # Trim if necessary
    while len(_model_cache._cache) > max_size:
        oldest_key = _model_cache._order.pop(0)
        del _model_cache._cache[oldest_key]
```

**Step 2: Add cache management endpoints to system.py**

```python
@api_router.get("/models")
async def get_model_cache(
    x_api_key: Optional[str] = Header(None)
):
    """Get Whisper model cache information."""
    verify_api_key(x_api_key)
    
    from .whisper_transcribe import get_model_cache_info
    return get_model_cache_info()

@api_router.delete("/models")
async def clear_all_models(
    x_api_key: Optional[str] = Header(None)
):
    """Clear all cached models."""
    verify_api_key(x_api_key)
    
    from .whisper_transcribe import clear_model_cache
    cleared = clear_model_cache()
    
    return {
        "success": True,
        "cleared_count": cleared
    }

@api_router.delete("/models/{key}")
async def remove_model(
    key: str,
    x_api_key: Optional[str] = Header(None)
):
    """Remove specific model from cache."""
    verify_api_key(x_api_key)
    
    from .whisper_transcribe import remove_model_from_cache
    removed = remove_model_from_cache(key)
    
    if not removed:
        raise HTTPException(status_code=404, detail=f"Model '{key}' not found")
    
    return {
        "success": True,
        "removed": key
    }

@api_router.patch("/models/config")
async def update_cache_config(
    request_body: dict,
    x_api_key: Optional[str] = Header(None)
):
    """Update cache configuration."""
    verify_api_key(x_api_key)
    
    max_size = request_body.get("max_size")
    
    if not isinstance(max_size, int) or max_size < 1:
        raise HTTPException(
            status_code=400,
            detail="max_size must be a positive integer"
        )
    
    from .whisper_transcribe import update_cache_max_size
    update_cache_max_size(max_size)
    
    return {
        "success": True,
        "max_size": max_size
    }
```

**Step 3: Write tests**

```python
# tests/api/test_cache.py
def test_get_model_cache():
    """Test model cache info endpoint."""
    from fastapi.testclient import TestClient
    from api.main import app
    
    client = TestClient(app)
    response = client.get("/api/v1/system/models")
    
    assert response.status_code == 200
    data = response.json()
    assert "cached_count" in data
    assert "max_size" in data

def test_clear_models():
    """Test clear all models endpoint."""
    from fastapi.testclient import TestClient
    from api.main import app
    
    client = TestClient(app)
    response = client.delete("/api/v1/system/models")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
```

**Step 4: Run tests**

```bash
python -m pytest tests/api/test_cache.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add api/system.py api/whisper_transcribe.py tests/api/test_cache.py
git commit -m "feat: add Whisper model cache management with LRU eviction"
```

---

### Task 8: Add Configuration Endpoints

**Files:**
- Modify: `api/system.py` (add config endpoints)
- Test: `tests/api/test_config.py`

**Step 1: Add timeout configuration endpoints**

```python
# Add to api/system.py
import os

# Global config storage (in-memory, reset on restart)
_config = {
    "timeouts": {
        "convert": int(os.getenv("CONVERT_TIMEOUT", "300")),
        "youtube_transcribe": int(os.getenv("YOUTUBE_TRANSCRIBE_TIMEOUT", "600")),
        "audio_transcribe": int(os.getenv("AUDIO_TRANSCRIBE_TIMEOUT", "600")),
    }
}

@api_router.get("/config/timeouts")
async def get_timeout_config(
    x_api_key: Optional[str] = Header(None)
):
    """Get current timeout configuration."""
    verify_api_key(x_api_key)
    
    return _config["timeouts"]

@api_router.patch("/config/timeouts")
async def update_timeout_config(
    request_body: dict,
    x_api_key: Optional[str] = Header(None)
):
    """Update timeout configuration."""
    verify_api_key(x_api_key)
    
    # Validate all values are positive integers
    for key, value in request_body.items():
        if not isinstance(value, int) or value < 1:
            raise HTTPException(
                status_code=400,
                detail=f"{key} must be a positive integer"
            )
    
    # Update config
    _config["timeouts"].update(request_body)
    
    return {
        "success": True,
        "timeouts": _config["timeouts"]
    }

@api_router.get("/config/cache")
async def get_cache_config(
    x_api_key: Optional[str] = Header(None)
):
    """Get current cache configuration."""
    verify_api_key(x_api_key)
    
    from .whisper_transcribe import WHISPER_MODEL_CACHE_SIZE
    return {
        "max_size": WHISPER_MODEL_CACHE_SIZE
    }
```

**Step 2: Write tests**

```python
# tests/api/test_config.py
def test_get_timeouts():
    """Test get timeout config."""
    from fastapi.testclient import TestClient
    from api.main import app
    
    client = TestClient(app)
    response = client.get("/api/v1/system/config/timeouts")
    
    assert response.status_code == 200
    data = response.json()
    assert "convert" in data

def test_update_timeouts():
    """Test update timeout config."""
    from fastapi.testclient import TestClient
    from api.main import app
    
    client = TestClient(app)
    response = client.patch(
        "/api/v1/system/config/timeouts",
        json={"convert": 600}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["timeouts"]["convert"] == 600
```

**Step 3: Run tests**

```bash
python -m pytest tests/api/test_config.py -v
```

Expected: PASS

**Step 4: Commit**

```bash
git add api/system.py tests/api/test_config.py
git commit -m "feat: add configuration endpoints for timeouts and cache"
```

---

## Phase 4: Retry Mechanism

### Task 9: Implement Retry Logic in Auto-Convert

**Files:**
- Modify: `api/auto_convert.py`
- Test: `tests/api/test_retry.py`

**Step 1: Add retry configuration**

```python
# api/auto_convert.py - add after imports
MAX_RETRIES = int(os.getenv("AUTO_MAX_RETRIES", "3"))
RETRY_BASE_DELAY = int(os.getenv("AUTO_RETRY_BASE_DELAY", "2"))
RETRY_MAX_DELAY = int(os.getenv("AUTO_RETRY_MAX_DELAY", "60"))
```

**Step 2: Implement retry function**

```python
import time

def convert_file_with_retry(file_path, max_retries=MAX_RETRIES):
    """Convert file with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            return convert_file(file_path)
        except Exception as e:
            if attempt < max_retries - 1:
                # Exponential backoff with max delay
                wait_time = min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY)
                print(f"[{datetime.now().isoformat()}] ⚠️ Conversion failed, retrying in {wait_time}s ({attempt+1}/{max_retries}): {str(e)}")
                time.sleep(wait_time)
            else:
                # Final failure - move to failed directory
                print(f"[{datetime.now().isoformat()}] ✗ Retries exhausted: {str(e)}")
                
                # Move to failed directory
                failed_dir = Path(TEMP_DIR) / ".failed"
                failed_dir.mkdir(exist_ok=True)
                
                # Move file
                shutil.move(str(file_path), str(failed_dir / file_path.name))
                
                # Write error file
                error_file = failed_dir / f"{file_path.name}.error"
                with open(error_file, 'w', encoding='utf-8') as f:
                    f.write(json.dumps({
                        "timestamp": datetime.now().isoformat(),
                        "error": str(e),
                        "retries": max_retries,
                        "file": str(file_path.name)
                    }, indent=2))
                
                logger.warning(f"File moved to failed directory: {file_path.name}")
                return False
```

**Step 3: Update main loop to use retry**

```python
# In main() function, replace:
success = convert_file(file_path)

# With:
success = convert_file_with_retry(file_path)
```

**Step 4: Write tests**

```python
# tests/api/test_retry.py
def test_retry_with_exponential_backoff():
    """Test retry logic with exponential backoff."""
    from api.auto_convert import convert_file_with_retry, MAX_RETRIES
    import time
    
    # Mock a file that fails twice then succeeds
    call_count = [0]
    
    def mock_convert():
        call_count[0] += 1
        if call_count[0] < 3:
            raise Exception("Simulated failure")
        return True
    
    start = time.time()
    result = convert_file_with_retry(mock_convert, max_retries=3)
    elapsed = time.time() - start
    
    assert result == True
    assert call_count[0] == 3
    # Should have waited at least 2 + 4 = 6 seconds
    assert elapsed >= 6
```

**Step 5: Run tests**

```bash
python -m pytest tests/api/test_retry.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add api/auto_convert.py tests/api/test_retry.py
git commit -m "feat: add exponential backoff retry with failed file handling"
```

---

## Phase 5: CLI Scripts

### Task 10: Create Cleanup Script

**Files:**
- Create: `scripts/cleanup.py`
- Test: Manual testing

**Step 1: Create cleanup script**

```python
#!/usr/bin/env python3
"""
Cleanup script for MarkItDown temporary files.

Usage:
    python scripts/cleanup.py --types youtube,ocr,uploads,failed,models,all
    python scripts/cleanup.py --dry-run
    python scripts/cleanup.py --force
"""

import argparse
import sys
import os
import json
from pathlib import Path
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.constants import CLEANUP_TYPES

TEMP_DIR = os.getenv("TEMP_DIR", "/tmp")

def get_storage_info():
    """Get storage information."""
    info = {
        "youtube_audio": {"files": 0, "bytes": 0},
        "ocr_temp": {"files": 0, "bytes": 0},
        "uploads": {"files": 0, "bytes": 0},
        "failed": {"files": 0, "bytes": 0},
    }
    
    # Count youtube files
    for f in Path(TEMP_DIR).glob("*.mp3"):
        if f.is_file():
            info["youtube_audio"]["files"] += 1
            info["youtube_audio"]["bytes"] += f.stat().st_size
    
    # Count OCR temp files
    for f in Path(TEMP_DIR).glob("page_*.png"):
        if f.is_file():
            info["ocr_temp"]["files"] += 1
            info["ocr_temp"]["bytes"] += f.stat().st_size
    
    # Count upload temp files
    for f in Path(TEMP_DIR).glob("temp_*"):
        if f.is_file():
            info["uploads"]["files"] += 1
            info["uploads"]["bytes"] += f.stat().st_size
    
    # Count failed files
    failed_dir = Path(TEMP_DIR) / ".failed"
    if failed_dir.exists():
        for f in failed_dir.iterdir():
            if f.is_file() and not f.name.endswith(".error"):
                info["failed"]["files"] += 1
                info["failed"]["bytes"] += f.stat().st_size
    
    return info

def cleanup(types, dry_run=False):
    """Perform cleanup."""
    if "all" in types:
        types = ["youtube", "ocr", "uploads", "failed", "models"]
    
    result = {
        "cleaned": {},
        "total_freed_bytes": 0
    }
    
    if "youtube" in types:
        count = 0
        freed = 0
        for f in Path(TEMP_DIR).glob("*.mp3"):
            if f.is_file():
                freed += f.stat().st_size
                if not dry_run:
                    f.unlink()
                count += 1
        result["cleaned"]["youtube_audio"] = {"files": count, "bytes": freed}
        result["total_freed_bytes"] += freed
    
    if "ocr" in types:
        count = 0
        freed = 0
        for f in Path(TEMP_DIR).glob("page_*.png"):
            if f.is_file():
                freed += f.stat().st_size
                if not dry_run:
                    f.unlink()
                count += 1
        result["cleaned"]["ocr_temp"] = {"files": count, "bytes": freed}
        result["total_freed_bytes"] += freed
    
    if "uploads" in types:
        count = 0
        freed = 0
        for f in Path(TEMP_DIR).glob("temp_*"):
            if f.is_file():
                freed += f.stat().st_size
                if not dry_run:
                    f.unlink()
                count += 1
        result["cleaned"]["uploads"] = {"files": count, "bytes": freed}
        result["total_freed_bytes"] += freed
    
    if "failed" in types:
        count = 0
        freed = 0
        failed_dir = Path(TEMP_DIR) / ".failed"
        if failed_dir.exists():
            for f in failed_dir.iterdir():
                if f.is_file():
                    freed += f.stat().st_size
                    if not dry_run:
                        f.unlink()
                    count += 1
        result["cleaned"]["failed"] = {"files": count, "bytes": freed}
        result["total_freed_bytes"] += freed
    
    if "models" in types:
        # Note: Can't clear model cache from CLI, only via API
        result["cleaned"]["models"] = {
            "note": "Model cache can only be cleared via API"
        }
    
    return result

def main():
    parser = argparse.ArgumentParser(
        description='Cleanup MarkItDown temporary files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Preview what would be cleaned
    python scripts/cleanup.py --dry-run
    
    # Clean YouTube audio files
    python scripts/cleanup.py --types youtube --force
    
    # Clean all temporary files
    python scripts/cleanup.py --types all --force
    
    # Clean specific types
    python scripts/cleanup.py --types ocr,uploads --force
        """
    )
    
    parser.add_argument(
        '--types', '-t',
        nargs='+',
        default=['all'],
        choices=list(CLEANUP_TYPES.keys()),
        help='Types to clean (default: all)'
    )
    
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be cleaned without actually cleaning'
    )
    
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Actually perform cleanup (required for safety)'
    )
    
    parser.add_argument(
        '--json', '-j',
        action='store_true',
        help='Output in JSON format'
    )
    
    args = parser.parse_args()
    
    # Get storage info
    info = get_storage_info()
    
    if args.dry_run:
        print("DRY RUN - No files will be deleted\n")
        print("Would clean:")
        for type_name in args.types:
            if type_name == "all":
                for t in ["youtube", "ocr", "uploads", "failed"]:
                    print(f"  {t}: {info[t]['files']} files, {info[t]['bytes'] / 1024 / 1024:.2f} MB")
            else:
                print(f"  {type_name}: {info[type_name]['files']} files, {info[type_name]['bytes'] / 1024 / 1024:.2f} MB")
        
        print("\nUse --force to actually clean up files")
        return
    
    if not args.force:
        print("ERROR: --force is required to perform cleanup")
        print("Use --dry-run to preview what would be cleaned")
        sys.exit(1)
    
    # Perform cleanup
    result = cleanup(args.types)
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("\nCleanup complete:")
        for category, data in result["cleaned"].items():
            if "files" in data:
                print(f"  {category}: {data['files']} files, {data['bytes'] / 1024 / 1024:.2f} MB freed")
        
        total_mb = result["total_freed_bytes"] / 1024 / 1024
        print(f"\nTotal freed: {total_mb:.2f} MB")

if __name__ == "__main__":
    main()
```

**Step 2: Make executable**

```bash
chmod +x scripts/cleanup.py
```

**Step 3: Test dry run**

```bash
python scripts/cleanup.py --dry-run
```

Expected: Shows what would be cleaned

**Step 4: Test with --force**

```bash
python scripts/cleanup.py --types youtube --force
```

Expected: Cleans youtube files

**Step 5: Commit**

```bash
git add scripts/cleanup.py
git commit -m "feat: add cleanup CLI script with dry-run safety"
```

---

### Task 11: Create Storage Query Script

**Files:**
- Create: `scripts/storage.py`
- Test: Manual testing

**Step 1: Create storage script**

```python
#!/usr/bin/env python3
"""
Storage query script for MarkItDown.

Usage:
    python scripts/storage.py
    python scripts/storage.py --json
"""

import argparse
import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

TEMP_DIR = os.getenv("TEMP_DIR", "/tmp")

def get_storage_info():
    """Get detailed storage information."""
    info = {
        "total_bytes": 0,
        "total_mb": 0,
        "breakdown": {}
    }
    
    # YouTube audio
    youtube_bytes = 0
    youtube_files = 0
    for f in Path(TEMP_DIR).glob("*.mp3"):
        if f.is_file():
            youtube_bytes += f.stat().st_size
            youtube_files += 1
    
    info["breakdown"]["youtube_audio"] = {
        "bytes": youtube_bytes,
        "mb": round(youtube_bytes / 1024 / 1024, 2),
        "files": youtube_files
    }
    
    # OCR temp
    ocr_bytes = 0
    ocr_files = 0
    for f in Path(TEMP_DIR).glob("page_*.png"):
        if f.is_file():
            ocr_bytes += f.stat().st_size
            ocr_files += 1
    
    info["breakdown"]["ocr_temp"] = {
        "bytes": ocr_bytes,
        "mb": round(ocr_bytes / 1024 / 1024, 2),
        "files": ocr_files
    }
    
    # Uploads
    upload_bytes = 0
    upload_files = 0
    for f in Path(TEMP_DIR).glob("temp_*"):
        if f.is_file():
            upload_bytes += f.stat().st_size
            upload_files += 1
    
    info["breakdown"]["uploads"] = {
        "bytes": upload_bytes,
        "mb": round(upload_bytes / 1024 / 1024, 2),
        "files": upload_files
    }
    
    # Failed
    failed_bytes = 0
    failed_files = 0
    failed_dir = Path(TEMP_DIR) / ".failed"
    if failed_dir.exists():
        for f in failed_dir.iterdir():
            if f.is_file() and not f.name.endswith(".error"):
                failed_bytes += f.stat().st_size
                failed_files += 1
    
    info["breakdown"]["failed"] = {
        "bytes": failed_bytes,
        "mb": round(failed_bytes / 1024 / 1024, 2),
        "files": failed_files
    }
    
    # Total
    info["total_bytes"] = youtube_bytes + ocr_bytes + upload_bytes + failed_bytes
    info["total_mb"] = round(info["total_bytes"] / 1024 / 1024, 2)
    
    return info

def main():
    parser = argparse.ArgumentParser(
        description='Query MarkItDown storage usage'
    )
    
    parser.add_argument(
        '--json', '-j',
        action='store_true',
        help='Output in JSON format'
    )
    
    args = parser.parse_args()
    
    info = get_storage_info()
    
    if args.json:
        print(json.dumps(info, indent=2))
    else:
        print("\n=== MarkItDown Storage Usage ===\n")
        
        for category, data in info["breakdown"].items():
            print(f"{category}:")
            print(f"  Files: {data['files']}")
            print(f"  Size:  {data['mb']:.2f} MB")
            print()
        
        print(f"Total: {info['total_mb']:.2f} MB ({info['total_bytes']} bytes)")

if __name__ == "__main__":
    main()
```

**Step 2: Make executable**

```bash
chmod +x scripts/storage.py
```

**Step 3: Test**

```bash
python scripts/storage.py
python scripts/storage.py --json
```

Expected: Shows storage breakdown

**Step 4: Commit**

```bash
git add scripts/storage.py
git commit -m "feat: add storage query CLI script"
```

---

## Phase 6: Documentation & Cleanup

### Task 12: Update API Routes for 404 Handling

**Files:**
- Modify: `api/main.py` (update root endpoint)
- Test: Manual testing

**Step 1: Update root endpoint to return 404**

```python
# Replace the existing root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Return 404 for root path."""
    return Response(status_code=404)

# Keep health endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
```

**Step 2: Test 404 behavior**

```bash
curl -i http://localhost:51083/
```

Expected: `404 Not Found` with empty body

```bash
curl -i http://localhost:51083/health
```

Expected: `200 OK` with `{"status": "ok"}`

**Step 3: Commit**

```bash
git add api/main.py
git commit -m "fix: return 404 for undefined routes including root"
```

---

### Task 13: Update Documentation

**Files:**
- Create: `docs/SYSTEM_MANAGEMENT.md`
- Modify: `README.md` (add system management section)
- Modify: `AGENTS.md` (update with new patterns)

**Step 1: Create system management documentation**

```markdown
# System Management Guide

## Overview

The System Management API provides endpoints for monitoring and managing server resources, temporary files, model caches, and configuration.

## Authentication

If `API_KEY` environment variable is set, all system endpoints require authentication via `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:51083/api/v1/system/storage
```

If `API_KEY` is not set, authentication is skipped.

## Endpoints

### Storage Query

```bash
GET /api/v1/system/storage
```

Returns detailed storage breakdown by category.

### Cleanup

```bash
POST /api/v1/system/cleanup
Content-Type: application/json

{
  "types": ["youtube", "ocr", "uploads", "failed", "models", "all"]
}
```

### Model Cache

```bash
GET /api/v1/system/models              # Get cache info
DELETE /api/v1/system/models           # Clear all models
DELETE /api/v1/system/models/{key}     # Remove specific model
PATCH /api/v1/system/models/config     # Update max cache size
```

### Configuration

```bash
GET /api/v1/system/config/timeouts     # Get timeout config
PATCH /api/v1/system/config/timeouts   # Update timeouts
GET /api/v1/system/config/cache        # Get cache config
```

## CLI Scripts

### Cleanup

```bash
# Preview
python scripts/cleanup.py --dry-run

# Clean specific types
python scripts/cleanup.py --types youtube --force

# Clean all
python scripts/cleanup.py --types all --force
```

### Storage Query

```bash
python scripts/storage.py
python scripts/storage.py --json
```
```

**Step 2: Update README.md**

Add a new section after the API Usage section:

```markdown
## System Management

For monitoring and cleanup operations, see [System Management Guide](docs/SYSTEM_MANAGEMENT.md).

Quick commands:
```bash
# Check storage usage
python scripts/storage.py

# Clean temporary files
python scripts/cleanup.py --dry-run
python scripts/cleanup.py --force
```
```

**Step 3: Update AGENTS.md**

Add new sections for system management patterns.

**Step 4: Commit**

```bash
git add docs/SYSTEM_MANAGEMENT.md README.md AGENTS.md
git commit -m "docs: add system management documentation"
```

---

### Task 14: Final Verification

**Files:** All modified files

**Step 1: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: All tests pass

**Step 2: Manual API testing**

```bash
# Start server
uvicorn api.main:app --reload

# Test storage endpoint
curl http://localhost:8000/api/v1/system/storage | jq

# Test cleanup (dry run via API - would need to implement)
curl -X POST http://localhost:8000/api/v1/system/cleanup \
  -H "Content-Type: application/json" \
  -d '{"types": ["all"]}' | jq

# Test 404
curl -i http://localhost:8000/
```

**Step 3: Verify environment variables**

```bash
# Test with different LOG_FORMAT
LOG_FORMAT=json uvicorn api.main:app --reload
```

**Step 4: Create final commit**

```bash
git add .
git commit -m "chore: final verification and cleanup"
```

---

## Testing Checklist

- [ ] All constants imported correctly
- [ ] Logging middleware works (text and json formats)
- [ ] Error handling hides details in production
- [ ] 404 returns empty response
- [ ] Storage endpoint returns breakdown
- [ ] Cleanup endpoint removes files
- [ ] Model cache endpoints work
- [ ] Configuration endpoints work
- [ ] Retry logic with exponential backoff
- [ ] CLI scripts work with --dry-run and --force
- [ ] API_KEY authentication works when set
- [ ] API_KEY authentication skipped when not set

---

## Rollback Plan

If issues occur:

```bash
# Revert to main
git checkout main

# Or reset worktree
cd .worktrees/system-management-api
git reset --hard HEAD
```

---

## Execution Instructions

**REQUIRED:** Use `superpowers:executing-plans` skill to execute this plan task-by-task with review checkpoints.

Each task should be executed by a fresh subagent with code review between tasks.