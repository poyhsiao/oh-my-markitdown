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
