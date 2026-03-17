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