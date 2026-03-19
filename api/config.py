"""
Configuration Module for MarkItDown API

Handles environment variable loading, validation, and defaults.

All configuration is centralized here for:
- Type safety
- Validation on startup
- Clear error messages for misconfiguration
"""

import os
from typing import Optional, List, Set
from dataclasses import dataclass, field
from .device_utils import detect_device, validate_device, get_compute_type_for_device, get_recommended_threads


# Valid OCR languages
VALID_OCR_LANGUAGES: Set[str] = {
    'chi_tra', 'chi_sim', 'eng', 'jpn', 'kor', 'tha', 'vie'
}

# Valid Whisper model sizes
VALID_WHISPER_MODELS: Set[str] = {
    'tiny', 'base', 'small', 'medium', 'large'
}


class ConfigurationError(ValueError):
    """Raised when configuration is invalid."""
    pass


@dataclass
class APIConfig:
    """API server configuration."""
    host: str = "0.0.0.0"
    port: int = 51083
    port_internal: int = 8000
    debug: bool = False
    workers: int = 1
    
    def __post_init__(self):
        if self.port <= 0 or self.port > 65535:
            raise ConfigurationError(f"API_PORT must be between 1 and 65535, got {self.port}")
        if self.port_internal <= 0 or self.port_internal > 65535:
            raise ConfigurationError(f"API_PORT_INTERNAL must be between 1 and 65535, got {self.port_internal}")
        if self.workers < 1:
            raise ConfigurationError(f"API_WORKERS must be at least 1, got {self.workers}")


@dataclass
class UploadConfig:
    """Upload limits configuration."""
    max_size: int = 52428800  # 50MB
    timeout: int = 1800  # 30 minutes
    chunk_size: int = 1048576  # 1MB
    buffer_size: int = 10485760  # 10MB
    
    def __post_init__(self):
        if self.max_size <= 0:
            raise ConfigurationError(f"MAX_UPLOAD_SIZE must be positive, got {self.max_size}")
        if self.timeout <= 0:
            raise ConfigurationError(f"UPLOAD_TIMEOUT must be positive, got {self.timeout}")
        if self.chunk_size <= 0:
            raise ConfigurationError(f"UPLOAD_CHUNK_SIZE must be positive, got {self.chunk_size}")
        if self.buffer_size <= 0:
            raise ConfigurationError(f"UPLOAD_BUFFER_SIZE must be positive, got {self.buffer_size}")


@dataclass
class OCRConfig:
    """OCR configuration."""
    default_lang: str = "chi_tra+eng"
    enabled_by_default: bool = False
    
    def __post_init__(self):
        self._validate_ocr_lang(self.default_lang)
    
    def _validate_ocr_lang(self, lang: str) -> None:
        """Validate OCR language combination."""
        if not lang:
            return
        langs = lang.split('+')
        for l in langs:
            if l not in VALID_OCR_LANGUAGES:
                raise ConfigurationError(
                    f"Invalid OCR language '{l}'. Valid languages: {', '.join(sorted(VALID_OCR_LANGUAGES))}"
                )


@dataclass
class PerformanceConfig:
    """Performance-related configuration for Whisper transcription."""
    
    # GPU Configuration
    device: str = "auto"              # cpu | cuda | mps | auto
    compute_type: str = "auto"        # int8 | float16 | float32 | auto
    
    # CPU Performance
    cpu_threads: int = 0              # 0 = auto detect
    
    # VAD Configuration
    vad_enabled: bool = True
    vad_min_silence_ms: int = 300
    vad_threshold: float = 0.6
    vad_speech_pad_ms: int = 200
    
    # Model Selection
    auto_model_selection: bool = True
    
    def get_effective_device(self) -> str:
        """Get effective device (resolve 'auto')."""
        return validate_device(self.device)
    
    def get_effective_compute_type(self) -> str:
        """Get effective compute type."""
        if self.compute_type == "auto":
            return get_compute_type_for_device(self.get_effective_device())
        return self.compute_type
    
    def get_effective_threads(self) -> int:
        """Get effective CPU thread count."""
        return get_recommended_threads(self.cpu_threads)


@dataclass
class WhisperConfig:
    """Whisper transcription configuration."""
    model: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    default_language: str = "auto"
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    def __post_init__(self):
        if self.model not in VALID_WHISPER_MODELS:
            raise ConfigurationError(
                f"Invalid WHISPER_MODEL '{self.model}'. Valid models: {', '.join(sorted(VALID_WHISPER_MODELS))}"
            )
        if self.device not in ('cpu', 'cuda', 'auto'):
            raise ConfigurationError(f"WHISPER_DEVICE must be cpu, cuda, or auto, got {self.device}")


@dataclass
class ConcurrencyConfig:
    """Concurrency control configuration."""
    max_requests: int = 3
    queue_timeout: int = 600
    
    def __post_init__(self):
        if self.max_requests < 1:
            raise ConfigurationError(f"CONCURRENT_MAX_REQUESTS must be at least 1, got {self.max_requests}")
        if self.queue_timeout <= 0:
            raise ConfigurationError(f"CONCURRENT_QUEUE_TIMEOUT must be positive, got {self.queue_timeout}")


@dataclass
class AdminConfig:
    """Admin endpoint configuration."""
    ip_restriction_enabled: bool = False
    allowed_ips: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.ip_restriction_enabled and not self.allowed_ips:
            pass


@dataclass
class CleanupConfig:
    """Cleanup configuration."""
    temp_threshold_hours: int = 1
    auto_enabled: bool = False
    
    def __post_init__(self):
        if self.temp_threshold_hours < 0:
            raise ConfigurationError(f"CLEANUP_TEMP_THRESHOLD_HOURS must be non-negative, got {self.temp_threshold_hours}")


@dataclass
class LogConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "json"
    
    def __post_init__(self):
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.level.upper() not in valid_levels:
            raise ConfigurationError(f"LOG_LEVEL must be one of {valid_levels}, got {self.level}")
        if self.format not in ("text", "json"):
            raise ConfigurationError(f"LOG_FORMAT must be text or json, got {self.format}")


@dataclass
class VisionOCRConfig:
    """OpenAI Vision OCR configuration (optional)."""
    enabled: bool = False
    api_key: str = ""
    model: str = "gpt-4o"


@dataclass
class AutoConvertConfig:
    """Auto-convert service configuration."""
    input_dir: str = "/app/input"
    output_dir: str = "/app/output"
    enable_ocr: bool = True
    ocr_lang: str = "chi_tra+eng"
    poll_interval: int = 5


@dataclass
class Config:
    """Main configuration container."""
    api: APIConfig = field(default_factory=APIConfig)
    upload: UploadConfig = field(default_factory=UploadConfig)
    ocr: OCRConfig = field(default_factory=OCRConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    concurrency: ConcurrencyConfig = field(default_factory=ConcurrencyConfig)
    admin: AdminConfig = field(default_factory=AdminConfig)
    cleanup: CleanupConfig = field(default_factory=CleanupConfig)
    log: LogConfig = field(default_factory=LogConfig)
    vision_ocr: VisionOCRConfig = field(default_factory=VisionOCRConfig)
    auto_convert: AutoConvertConfig = field(default_factory=AutoConvertConfig)


def load_config_from_env() -> Config:
    """Load configuration from environment variables."""
    return Config(
        api=APIConfig(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "51083")),
            port_internal=int(os.getenv("API_PORT_INTERNAL", "8000")),
            debug=os.getenv("API_DEBUG", "false").lower() == "true",
            workers=int(os.getenv("API_WORKERS", "1")),
        ),
        upload=UploadConfig(
            max_size=int(os.getenv("UPLOAD_MAX_SIZE", os.getenv("MAX_UPLOAD_SIZE", "52428800"))),
            timeout=int(os.getenv("UPLOAD_TIMEOUT", "1800")),
            chunk_size=int(os.getenv("UPLOAD_CHUNK_SIZE", "1048576")),
            buffer_size=int(os.getenv("UPLOAD_BUFFER_SIZE", "10485760")),
        ),
        ocr=OCRConfig(
            default_lang=os.getenv("OCR_DEFAULT_LANG", os.getenv("DEFAULT_OCR_LANG", "chi_tra+eng")),
            enabled_by_default=os.getenv("OCR_ENABLED_DEFAULT", os.getenv("ENABLE_PLUGINS_BY_DEFAULT", "false")).lower() == "true",
        ),
        whisper=WhisperConfig(
            model=os.getenv("WHISPER_MODEL", "base"),
            device=os.getenv("WHISPER_DEVICE", "cpu"),
            compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
            default_language=os.getenv("WHISPER_DEFAULT_LANGUAGE", "auto"),
        ),
        concurrency=ConcurrencyConfig(
            max_requests=int(os.getenv("CONCURRENT_MAX_REQUESTS", "3")),
            queue_timeout=int(os.getenv("CONCURRENT_QUEUE_TIMEOUT", "600")),
        ),
        admin=AdminConfig(
            ip_restriction_enabled=os.getenv("ADMIN_IP_RESTRICTION_ENABLED", "false").lower() == "true",
            allowed_ips=[ip.strip() for ip in os.getenv("ADMIN_ALLOWED_IPS", "").split(",") if ip.strip()],
        ),
        cleanup=CleanupConfig(
            temp_threshold_hours=int(os.getenv("CLEANUP_TEMP_THRESHOLD_HOURS", "1")),
            auto_enabled=os.getenv("CLEANUP_AUTO_ENABLED", "false").lower() == "true",
        ),
        log=LogConfig(
            level=os.getenv("LOG_LEVEL", "INFO"),
            format=os.getenv("LOG_FORMAT", "json"),
        ),
        vision_ocr=VisionOCRConfig(
            enabled=os.getenv("VISION_OCR_ENABLED", "false").lower() == "true",
            api_key=os.getenv("VISION_OCR_API_KEY", os.getenv("OPENAI_API_KEY", "")),
            model=os.getenv("VISION_OCR_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o")),
        ),
        auto_convert=AutoConvertConfig(
            input_dir=os.getenv("AUTO_INPUT_DIR", "/app/input"),
            output_dir=os.getenv("AUTO_OUTPUT_DIR", "/app/output"),
            enable_ocr=os.getenv("AUTO_ENABLE_OCR", "true").lower() == "true",
            ocr_lang=os.getenv("AUTO_OCR_LANG", "chi_tra+eng"),
            poll_interval=int(os.getenv("AUTO_POLL_INTERVAL", "5")),
        ),
    )


def validate_environment() -> Config:
    """
    Validate all environment variables on startup.
    
    Raises:
        ConfigurationError: If any configuration is invalid
        
    Returns:
        Config: Validated configuration object
    """
    try:
        config = load_config_from_env()
        return config
    except ValueError as e:
        raise ConfigurationError(str(e))


# Global config instance (loaded on import if needed)
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = validate_environment()
    return _config