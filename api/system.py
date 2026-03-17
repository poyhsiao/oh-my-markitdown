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

from .concurrency import get_concurrency_manager
from .config import get_config
from .response import success_response

api_router = APIRouter(prefix="/api/v1/admin")

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
        "targets": ["temp", "whisper", "all"],
        "dry_run": false
    }
    
    Default: all targets, dry_run=true
    
    Target values:
    - temp: Clean temporary files (youtube audio, OCR temp, uploads, failed)
    - whisper: Clear Whisper model cache
    - all: Clean both temp and whisper
    """
    verify_api_key(x_api_key)
    
    targets = request_body.get("targets", ["all"])
    dry_run = request_body.get("dry_run", True)
    
    # Map spec targets to internal types
    types_to_clean = []
    if "all" in targets:
        types_to_clean = ["youtube", "ocr", "uploads", "models", "failed"]
    else:
        if "temp" in targets:
            types_to_clean.extend(["youtube", "ocr", "uploads", "failed"])
        if "whisper" in targets:
            types_to_clean.append("models")
    
    result = {
        "success": True,
        "dry_run": dry_run,
        "cleaned": {},
        "total_freed_bytes": 0,
        "total_freed_mb": 0
    }
    
    total_freed = 0
    
    # Clean youtube audio
    if "youtube" in types_to_clean:
        freed = 0
        count = 0
        try:
            for f in Path(TEMP_DIR).glob("*.mp3"):
                if f.is_file():
                    freed += f.stat().st_size
                    if not dry_run:
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
    if "ocr" in types_to_clean:
        freed = 0
        count = 0
        try:
            for f in Path(TEMP_DIR).glob("page_*.png"):
                if f.is_file():
                    freed += f.stat().st_size
                    if not dry_run:
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
    if "uploads" in types_to_clean:
        freed = 0
        count = 0
        try:
            for f in Path(TEMP_DIR).glob("temp_*"):
                if f.is_file():
                    freed += f.stat().st_size
                    if not dry_run:
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
    if "failed" in types_to_clean:
        freed = 0
        count = 0
        try:
            failed_dir = Path(TEMP_DIR) / ".failed"
            if failed_dir.exists():
                for f in failed_dir.iterdir():
                    if f.is_file():
                        freed += f.stat().st_size
                        if not dry_run:
                            f.unlink()
                        count += 1
        except:
            pass
        
        result["cleaned"]["failed"] = {
            "files": count,
            "bytes": freed
        }
        total_freed += freed
    
    # Clear model cache (only if not dry_run)
    if "models" in types_to_clean and not dry_run:
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
    elif "models" in types_to_clean and dry_run:
        # In dry_run mode, just report what would be freed
        try:
            from .whisper_transcribe import get_model_cache_info
            cache_info = get_model_cache_info()
            result["cleaned"]["models"] = {
                "would_clear": cache_info.get("total_mb", 0),
                "note": "dry_run: models not actually cleared"
            }
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


# ===== Queue Status Endpoint =====
@api_router.get("/queue")
async def get_queue_status(
    x_api_key: Optional[str] = Header(None)
):
    """
    Query current queue status.
    
    Returns:
        - current_processing: Number of requests currently being processed
        - max_concurrent: Maximum concurrent requests allowed
        - queue_length: Number of requests waiting in queue
        - queue: List of queued/processing requests with details
    """
    verify_api_key(x_api_key)
    
    manager = get_concurrency_manager()
    queue_status = manager.get_queue_status()
    
    return success_response(data=queue_status)


# ===== Full Configuration Endpoint =====
@api_router.get("/config")
async def get_full_config(
    x_api_key: Optional[str] = Header(None)
):
    """
    Query current full configuration.
    
    Returns configuration for:
        - api: API server settings
        - ocr: OCR configuration
        - whisper: Whisper transcription settings
        - cleanup: Cleanup configuration
        - admin: Admin endpoint settings
    """
    verify_api_key(x_api_key)
    
    config = get_config()
    
    # Build response according to spec
    data = {
        "api": {
            "version": "1.0.0",
            "port": config.api.port,
            "debug": config.api.debug,
            "max_upload_size_mb": config.upload.max_size // (1024 * 1024),
            "upload_timeout_minutes": config.upload.timeout // 60,
            "max_concurrent_requests": config.concurrency.max_requests
        },
        "ocr": {
            "enabled": config.ocr.enabled_by_default,
            "default_language": config.ocr.default_lang,
            "openai_enabled": bool(os.getenv("OPENAI_API_KEY", ""))
        },
        "whisper": {
            "model": config.whisper.model,
            "device": config.whisper.device,
            "compute_type": config.whisper.compute_type
        },
        "cleanup": {
            "temp_threshold_hours": int(os.getenv("CLEANUP_TEMP_THRESHOLD_HOURS", "1")),
            "auto_cleanup_enabled": os.getenv("AUTO_CLEANUP_ENABLED", "false").lower() == "true"
        },
        "admin": {
            "ip_restriction_enabled": os.getenv("IP_WHITELIST_ENABLED", "false").lower() == "true",
            "allowed_ips": os.getenv("IP_WHITELIST", "").split(",") if os.getenv("IP_WHITELIST") else []
        }
    }
    
    return success_response(data=data)
