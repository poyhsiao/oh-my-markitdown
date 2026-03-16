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

# ===== Storage Query Endpoint =====
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

# ===== Cleanup Endpoint =====
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

# ===== Model Cache Management Endpoints =====
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

# ===== Configuration Endpoints =====
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
