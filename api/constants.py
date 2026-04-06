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

# Default OCR language
DEFAULT_OCR_LANG = "chi_tra+eng"

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

# Whisper model cache settings
WHISPER_MODEL_CACHE_SIZE = 3  # Max models to keep in cache

# Timeout settings (in seconds)
DEFAULT_YOUTUBE_INFO_TIMEOUT = 300  # 5 minutes for getting video info
DEFAULT_YOUTUBE_DOWNLOAD_TIMEOUT = 600  # 10 minutes for downloading audio
DEFAULT_AUDIO_EXTRACT_TIMEOUT = 300  # 5 minutes for extracting audio from video

# YouTube subtitle language priority
# Used when checking available subtitles and selecting the best one
SUBTITLE_LANG_PRIORITY = [
    'zh-Hant',    # Traditional Chinese (Taiwan)
    'zh-Hans',    # Simplified Chinese
    'zh-TW',      # Traditional Chinese (Taiwan, alternative code)
    'zh-CN',      # Simplified Chinese (alternative code)
    'zh',         # Generic Chinese
    'en',         # English
]

# Subtitle download timeout
SUBTITLE_DOWNLOAD_TIMEOUT = 120  # 2 minutes for downloading subtitles

# ===== VAD Parameters =====
DEFAULT_VAD_MIN_SILENCE_MS = 500
DEFAULT_VAD_THRESHOLD = 0.5
DEFAULT_VAD_SPEECH_PAD_MS = 300

# ===== Audio Extraction Parameters =====
AUDIO_SAMPLE_RATE = 16000           # 16kHz (Whisper native)
AUDIO_CHANNELS = 1                  # Mono
AUDIO_CODEC = "pcm_s16le"           # WAV/PCM
AUDIO_FFMPEG_THREADS = 4            # FFmpeg thread count

# ===== CPU Threading =====
MAX_CPU_THREADS = 8
MIN_CPU_THREADS = 1
DEFAULT_CPU_THREADS = 8

# ===== Model Selection Thresholds (seconds) =====
MODEL_SELECTION_THRESHOLDS = {
    "tiny": 120,         # < 2 minutes
    "base": 600,         # 2-10 minutes
    "small": 1800,       # 10-30 minutes
    "medium": float("inf")  # > 30 minutes
}

# ===== Compute Type by Device =====
COMPUTE_TYPE_BY_DEVICE = {
    "cpu": "int8",
    "cuda": "float16",
    "mps": "float16"
}

# ===== Chunking Configuration =====
# For handling long audio/video files that may cause Cloudflare 524 timeout
# Cloudflare has a 100-second timeout limit for proxied requests
DEFAULT_CHUNK_DURATION = 60 # Max duration per chunk (seconds)
DEFAULT_CHUNK_OVERLAP = 2 # Overlap between chunks (seconds)
DEFAULT_AUTO_CHUNK_THRESHOLD = 90 # Auto-enable chunking above this duration (100s - 10s buffer)
MAX_TOTAL_DURATION = 7200 # Max total processing time (2 hours)
MIN_CHUNK_DURATION = 10 # Minimum chunk duration (seconds)

# ===== Whisper Quality Presets =====
# Maps user-friendly quality_mode to beam_size/temperature
QUALITY_PRESETS = {
    "fast": {"beam_size": 1, "temperature": 0.0},
    "standard": {"beam_size": 3, "temperature": 0.0},
    "best": {"beam_size": 5, "temperature": 0.0},
}

# ===== Chunk Transcription Settings =====
DEFAULT_CHUNK_BEAM_SIZE = 1
DEFAULT_CHUNK_TEMPERATURE = 0.0
DEFAULT_BATCH_SIZE = 8
DEFAULT_CHUNK_LENGTH_S = 30

# ===== Worker Configuration =====
DEFAULT_MAX_WORKERS = 4
MIN_MAX_WORKERS = 1
MAX_MAX_WORKERS = 8

# ===== Parallel Chunking Threshold =====
# Minimum number of chunks before parallel processing is worthwhile
PARALLEL_MIN_CHUNKS = 4

# Dynamic max_workers based on chunk count: (min_chunks, max_workers)
PARALLEL_MAX_WORKERS_TABLE = [
    (1, 1),   # 1 chunk: no parallel
    (2, 1),   # 2-3 chunks: sequential (overhead > benefit)
    (4, 2),   # 4-6 chunks: 2 workers
    (7, 4),   # 7+ chunks: 4 workers
]

# ===== Model Pre-warm Configuration =====
# Models to pre-load at startup to eliminate cold-start latency
# Format: (model_size, device, compute_type, cpu_threads)
PRE_WARM_MODELS = [
    ("tiny", "cpu", "int8", 8),
    ("base", "cpu", "int8", 8),
]