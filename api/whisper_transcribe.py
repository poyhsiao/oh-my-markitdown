"""
Whisper Transcription Module
Use Faster-Whisper for local speech-to-text
"""

import os
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from faster_whisper import WhisperModel

from .constants import (
    WHISPER_MODEL_CACHE_SIZE,
    DEFAULT_YOUTUBE_INFO_TIMEOUT,
    DEFAULT_YOUTUBE_DOWNLOAD_TIMEOUT,
    DEFAULT_AUDIO_EXTRACT_TIMEOUT,
    SUBTITLE_LANG_PRIORITY,
    SUBTITLE_DOWNLOAD_TIMEOUT,
    MODEL_SELECTION_THRESHOLDS,
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    AUDIO_CODEC,
    AUDIO_FFMPEG_THREADS,
    DEFAULT_VAD_MIN_SILENCE_MS,
    DEFAULT_VAD_THRESHOLD,
    DEFAULT_VAD_SPEECH_PAD_MS,
    DEFAULT_CPU_THREADS,
    DEFAULT_CHUNK_DURATION,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_AUTO_CHUNK_THRESHOLD,
    MAX_TOTAL_DURATION,
    MIN_CHUNK_DURATION,
)
from .chunking import (
    ChunkConfig,
    AudioChunk,
    get_audio_duration,
    should_enable_chunking,
    calculate_chunk_segments,
    split_audio_into_chunks,
    transcribe_chunk,
    merge_transcription_results,
    cleanup_chunks,
    estimate_processing_time,
    get_chunking_recommendation,
)
from .subtitles import format_multiline_output, format_transcript_with_timestamps

# Import new SDK modules
from .youtube_client import YouTubeClient, YouTubeClientError
from .audio_extractor import extract_audio_from_video as _extract_audio_sdk

# Read configuration from environment variables
DEFAULT_MODEL = os.getenv("WHISPER_MODEL", "base")
DEFAULT_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
DEFAULT_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

# Timeout configuration from environment (with defaults from constants)
YOUTUBE_INFO_TIMEOUT = int(os.getenv("YOUTUBE_INFO_TIMEOUT", str(DEFAULT_YOUTUBE_INFO_TIMEOUT)))
YOUTUBE_DOWNLOAD_TIMEOUT = int(os.getenv("YOUTUBE_DOWNLOAD_TIMEOUT", str(DEFAULT_YOUTUBE_DOWNLOAD_TIMEOUT)))
AUDIO_EXTRACT_TIMEOUT = int(os.getenv("AUDIO_EXTRACT_TIMEOUT", str(DEFAULT_AUDIO_EXTRACT_TIMEOUT)))

# Global model cache (avoid repeated loading)
class ModelCache:
    """LRU model cache with size limit."""
    
    def __init__(self, max_size: int = WHISPER_MODEL_CACHE_SIZE):
        self._cache: Dict[str, WhisperModel] = {}
        self._order: List[str] = []
        self._max_size = max_size
    
    def get(self, key: str) -> Optional[WhisperModel]:
        if key in self._cache:
            self._order.remove(key)
            self._order.append(key)
            return self._cache[key]
        return None
    
    def set(self, key: str, model: WhisperModel):
        if key in self._cache:
            self._order.remove(key)
        elif len(self._cache) >= self._max_size:
            oldest_key = self._order.pop(0)
            del self._cache[oldest_key]
        self._cache[key] = model
        self._order.append(key)
    
    def clear(self) -> int:
        count = len(self._cache)
        self._cache.clear()
        self._order.clear()
        return count
    
    def remove(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            self._order.remove(key)
            return True
        return False
    
    def get_info(self) -> dict:
        return {
            "max_size": self._max_size,
            "current_size": len(self._cache),
            "cached_models": list(self._cache.keys()),
        }

_model_cache = ModelCache(max_size=WHISPER_MODEL_CACHE_SIZE)


def get_model_cache_info():
    return _model_cache.get_info()


def clear_model_cache() -> int:
    return _model_cache.clear()


def remove_model_from_cache(key: str) -> bool:
    return _model_cache.remove(key)


def update_cache_max_size(max_size: int):
    _model_cache._max_size = max_size
    while len(_model_cache._cache) > max_size:
        oldest_key = _model_cache._order.pop(0)
        del _model_cache._cache[oldest_key]


def get_recommended_model(duration_seconds: float) -> str:
    """
    Get recommended model size based on media duration.
    
    Args:
        duration_seconds: Media duration in seconds
        
    Returns:
        Recommended model size (tiny/base/small/medium)
    """
    if duration_seconds < MODEL_SELECTION_THRESHOLDS["tiny"]:
        return "tiny"
    elif duration_seconds < MODEL_SELECTION_THRESHOLDS["base"]:
        return "base"
    elif duration_seconds < MODEL_SELECTION_THRESHOLDS["small"]:
        return "small"
    return "medium"


def get_model(
    model_size: Optional[str] = None, 
    device: Optional[str] = None, 
    compute_type: Optional[str] = None,
    cpu_threads: int = 4
):
    """
    Get or load Whisper model
    
    Args:
        model_size: Model size (tiny, base, small, medium, large)
        device: Device to run on (cpu, cuda)
        compute_type: Compute type (int8, float16, float32)
        cpu_threads: Number of CPU threads (default: 4)
    
    Returns:
        WhisperModel instance
    """
    # Use environment variables or defaults
    model_size = model_size or DEFAULT_MODEL
    device = device or DEFAULT_DEVICE
    compute_type = compute_type or DEFAULT_COMPUTE_TYPE
    
    cache_key = f"{model_size}_{device}_{compute_type}_{cpu_threads}"
    
    model = _model_cache.get(cache_key)
    if model is None:
        print(f"[Whisper] Loading model: {model_size} (device={device}, compute_type={compute_type}, cpu_threads={cpu_threads})")
        model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            cpu_threads=cpu_threads
        )
        _model_cache.set(cache_key, model)
    
    return model


def transcribe_audio(
    audio_path: str,
    language: str = "auto",
    model_size: Optional[str] = None,
    device: Optional[str] = None,
    compute_type: Optional[str] = None,
    cpu_threads: Optional[int] = None,
    vad_enabled: bool = True,
    vad_params: Optional[dict] = None,
    word_timestamps: bool = False
) -> Tuple[str, dict]:
    """
    Transcribe audio file with Whisper.
    
    Args:
        audio_path: Path to audio file
        language: Language code or "auto" for detection
        model_size: Model size (None = use config default)
        device: Compute device (None = use config default)
        compute_type: Compute type (None = use config default)
        cpu_threads: CPU threads (None = auto detect)
        vad_enabled: Enable VAD filtering
        vad_params: Custom VAD parameters
        word_timestamps: Enable word-level timestamps
        
Returns:
    Tuple of (transcription_text, metadata)
    """
    overall_start = time.time()
    model_load_start = time.time()

    # Use environment variables or defaults
    effective_device = device or DEFAULT_DEVICE
    effective_compute_type = compute_type or DEFAULT_COMPUTE_TYPE
    effective_threads = cpu_threads or DEFAULT_CPU_THREADS

    # Handle auto model selection
    audio_duration_seconds = None
    if model_size == "auto" or model_size is None:
        try:
            audio_duration_seconds = get_audio_duration(audio_path)
            effective_model = get_recommended_model(audio_duration_seconds)
        except Exception:
            effective_model = DEFAULT_MODEL
    else:
        effective_model = model_size

    # Handle "auto" for auto-detection (Whisper expects None for auto-detect)
    actual_language = None if language == "auto" else language

    # VAD parameters
    if vad_enabled and vad_params is None:
        vad_params = {
            "min_silence_duration_ms": DEFAULT_VAD_MIN_SILENCE_MS,
            "threshold": DEFAULT_VAD_THRESHOLD,
            "speech_pad_ms": DEFAULT_VAD_SPEECH_PAD_MS
        }

    # Load model with CPU threading support
    model = get_model(effective_model, effective_device, effective_compute_type, cpu_threads=effective_threads)
    model_load_time_ms = int((time.time() - model_load_start) * 1000)

    # Transcribe
    transcription_start = time.time()
    segments, info = model.transcribe(
        audio_path,
        language=actual_language,
        word_timestamps=word_timestamps,
        vad_filter=vad_enabled,
        vad_parameters=vad_params if vad_enabled else None
    )
    transcription_time_ms = int((time.time() - transcription_start) * 1000)

    # Combine text
    transcript_lines = []
    for segment in segments:
        transcript_lines.append(segment.text)

    transcript = " ".join(transcript_lines)

    # Calculate realtime factor
    audio_duration = info.duration if info.duration else audio_duration_seconds
    realtime_factor = None
    if audio_duration and transcription_time_ms > 0:
        realtime_factor = round(transcription_time_ms / (audio_duration * 1000), 2)

    # Metadata
    metadata = {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "duration_after_vad": info.duration_after_vad,
        "segments_count": len(list(segments)) if segments else 0,
        "model": effective_model,
        "device": effective_device,
        "compute_type": effective_compute_type,
        "vad_enabled": vad_enabled,
        "backend": "faster-whisper",
        "cpu_threads": effective_threads,
        "model_load_time_ms": model_load_time_ms,
        "transcription_time_ms": transcription_time_ms,
        "realtime_factor": realtime_factor,
        "audio_duration_seconds": audio_duration,
    }
    
    return transcript, metadata


def transcribe_with_timestamps(
    audio_path: str,
    language: Optional[str] = None,
    model_size: str = "base"
) -> Tuple[str, list]:
    """
    Transcribe audio and return timestamps
    
    Args:
        audio_path: Audio file path
        language: Language code (None=auto-detect)
        model_size: Model size
    
    Returns:
        (transcript text, segments list)
    """
    model = get_model(model_size)
    
    segments, info = model.transcribe(
        audio_path,
        language=language,
        vad_filter=True
    )
    
    segments_list = []
    transcript_lines = []
    
    for segment in segments:
        segments_list.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text
        })
        transcript_lines.append(segment.text)
    
    return " ".join(transcript_lines), segments_list


# Global YouTube client instance
_youtube_client: Optional[YouTubeClient] = None


def _get_youtube_client() -> YouTubeClient:
    """Get or create YouTube client instance."""
    global _youtube_client
    if _youtube_client is None:
        _youtube_client = YouTubeClient(
            timeout=YOUTUBE_INFO_TIMEOUT,
            download_timeout=YOUTUBE_DOWNLOAD_TIMEOUT,
            subtitle_timeout=SUBTITLE_DOWNLOAD_TIMEOUT,
        )
    return _youtube_client


def download_youtube_audio(
    url: str, 
    output_dir: str = "/tmp",
    audio_quality: str = "128K"
) -> Tuple[str, str]:
    """
    Download audio from YouTube video using yt-dlp SDK.
    
    Args:
        url: YouTube URL
        output_dir: Output directory
        audio_quality: Audio quality (128K default, 64K for faster download)
    
    Returns:
        (audio file path, video title)
    
    Raises:
        YouTubeClientError: Download failed
    """
    client = _get_youtube_client()
    return client.download_audio(url, output_dir, audio_quality)


def transcribe_youtube_video(
    url: str,
    language: str = "zh",
    model_size: Optional[str] = None,
    device: Optional[str] = None,
    compute_type: Optional[str] = None,
    cpu_threads: Optional[int] = None,
    vad_enabled: bool = True,
    vad_params: Optional[dict] = None,
    output_dir: str = "/tmp",
    prefer_subtitles: bool = True,
    fast_mode: bool = False
) -> dict:
    """
    Download YouTube video and transcribe.
    
    Uses hybrid strategy:
    - Fast path: Use YouTube subtitles if available (2-5 seconds)
    - Slow path: Use Whisper transcription (30-60 minutes for 1hr video)
    
    Args:
        url: YouTube URL
        language: Language code
        model_size: Model size (None = use config default)
        device: Compute device (None = use config default)
        compute_type: Compute type (None = use config default)
        cpu_threads: CPU threads (None = auto detect)
        vad_enabled: Enable VAD filtering
        vad_params: Custom VAD parameters
        output_dir: Temporary file directory
        prefer_subtitles: Prefer YouTube subtitles if available
        fast_mode: Enable optimizations for Whisper (lower quality, multi-threading)
    
    Returns:
        Dictionary containing transcript results and metadata
    """
    start_time = time.time()
    
    # Fast path: Check for subtitles first
    if prefer_subtitles:
        try:
            subtitle_info = check_available_subtitles(url)
            
            if subtitle_info["available_langs"]:
                # Subtitles available - use fast path
                transcript, subtitle_metadata = download_and_convert_subtitles(
                    url, output_dir, [subtitle_info["recommended_lang"]]
                )
                
                processing_time_ms = int((time.time() - start_time) * 1000)
                
                # Get video title
                title = _get_video_title(url)
                
                return {
                    "success": True,
                    "title": title,
                    "transcript": transcript,
                    "metadata": {
                        **subtitle_metadata,
                        "processing_time_ms": processing_time_ms
                    }
                }
        except Exception as e:
            # Subtitle extraction failed, fall back to Whisper
            print(f"[YouTube] Subtitle extraction failed, falling back to Whisper: {e}")
    
# Slow path: Download audio and use Whisper
    audio_quality = "64K" if fast_mode else "128K"
    audio_path, title = download_youtube_audio(url, output_dir, audio_quality=audio_quality)

    try:
        effective_model = model_size
        if model_size == "auto" or model_size is None:
            try:
                audio_duration = get_audio_duration(audio_path)
                effective_model = get_recommended_model(audio_duration)
            except Exception:
                effective_model = DEFAULT_MODEL

        # Transcribe with optional optimizations
        # Use more CPU threads in fast_mode for faster processing
        effective_threads = cpu_threads or (8 if fast_mode else None)
        transcript, metadata = transcribe_audio(
            audio_path,
            language=language,
            model_size=effective_model,
            device=device,
            compute_type=compute_type,
            cpu_threads=effective_threads,
            vad_enabled=vad_enabled,
            vad_params=vad_params
        )
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Add source info to metadata
        metadata["source"] = "whisper"
        metadata["processing_time_ms"] = processing_time_ms
        
        return {
            "success": True,
            "title": title,
            "transcript": transcript,
            "metadata": metadata
        }
        
    finally:
        # Clean up temporary files
        if os.path.exists(audio_path):
            os.unlink(audio_path)


def _get_video_title(url: str) -> str:
    """Get YouTube video title using yt-dlp SDK."""
    try:
        client = _get_youtube_client()
        info = client.get_video_info(url)
        return info.title
    except YouTubeClientError:
        return "Unknown"
    except Exception:
        return "Unknown"


def format_transcript_as_markdown(
    title: str,
    transcript: str,
    metadata: dict,
    include_metadata: bool = True
) -> str:
    """
    Format transcript results as Markdown
    
    Args:
        title: Video title
        transcript: Transcript text
        metadata: Metadata
        include_metadata: Whether to include metadata
    
    Returns:
        Markdown formatted string
    """
    md_lines = [f"# {title}", ""]
    
    if include_metadata:
        # Build metadata section with source info
        source = metadata.get('source', 'whisper')
        source_display = "YouTube Subtitles" if source == "youtube_subtitles" else "Whisper AI"
        
        md_lines.extend([
            "## Transcription Info",
            "",
            f"- **Source**: {source_display}",
            f"- **Language**: {metadata.get('language', 'unknown')}",
        ])
        
        # Add duration if available
        if metadata.get('duration'):
            md_lines.append(f"- **Duration**: {metadata.get('duration', 0):.1f} seconds")
        
        # Add model info for Whisper
        if source == 'whisper' and metadata.get('model'):
            md_lines.append(f"- **Model**: {metadata.get('model')}")
        
        # Add auto-generated flag for subtitles
        if source == 'youtube_subtitles':
            is_auto = metadata.get('is_auto_generated', False)
            auto_text = "Auto-generated" if is_auto else "Manual"
            md_lines.append(f"- **Subtitle Type**: {auto_text}")
        
        # Add processing time
        if metadata.get('processing_time_ms'):
            time_ms = metadata.get('processing_time_ms', 0)
            if time_ms < 1000:
                time_str = f"{time_ms}ms"
            else:
                time_str = f"{time_ms / 1000:.1f}s"
            md_lines.append(f"- **Processing Time**: {time_str}")
        
        md_lines.extend([
            "",
            "---",
            ""
        ])
    
    md_lines.extend([
        "## Transcript",
        "",
        transcript
    ])
    
    return "\n".join(md_lines)


def transcribe_with_formats(
    audio_path: str,
    language: str = "auto",
    model_size: Optional[str] = None,
    device: Optional[str] = None,
    compute_type: Optional[str] = None,
    cpu_threads: Optional[int] = None,
    vad_enabled: bool = True,
    vad_params: Optional[dict] = None,
    output_formats: str = "markdown",
    include_timestamps: bool = False
) -> Tuple[Dict[str, str], dict]:
    """
    Transcribe audio and return multiple format outputs
    
    Args:
        audio_path: Audio file path
        language: Language code (auto=auto-detect)
        model_size: Model size (None = use config default)
        device: Compute device (None = use config default)
        compute_type: Compute type (None = use config default)
        cpu_threads: CPU threads (None = auto detect)
        vad_enabled: Enable VAD filtering
        vad_params: Custom VAD parameters
        output_formats: Output formats (comma-separated, e.g., markdown,srt,vtt)
        include_timestamps: Whether to include timestamps in Markdown
    
    Returns:
        (format dict, metadata)
    """
    # Handle "auto" for auto-detection (Whisper expects None for auto-detect)
    actual_language = None if language == "auto" else language
    
    # Get segments with timestamps
    _, segments_list = transcribe_with_timestamps(
        audio_path,
        language=actual_language,
        model_size=model_size or DEFAULT_MODEL
    )
    
    # Use subtitles module to generate multiple formats
    formats_dict = format_multiline_output(
        segments_list,
        output_format=output_formats,
        include_timestamps=include_timestamps
    )
    
    # Metadata
    metadata = {
        "language": language,
        "model": model_size or DEFAULT_MODEL,
        "device": device or DEFAULT_DEVICE,
        "compute_type": compute_type or DEFAULT_COMPUTE_TYPE,
        "vad_enabled": vad_enabled,
        "segments_count": len(segments_list),
        "formats": list(formats_dict.keys())
    }
    
    return formats_dict, metadata


def extract_audio_from_video(
    video_path: str,
    output_audio_path: Optional[str] = None,
    threads: int = AUDIO_FFMPEG_THREADS
) -> str:
    """
    Extract audio from video file using ffmpeg-python SDK.
    
    Optimizations:
    - WAV/PCM format (no compression overhead)
    - 16kHz sample rate (Whisper native)
    - Mono channel
    - Multi-threaded decoding
    
    Args:
        video_path: Path to video file
        output_audio_path: Output path (optional, temp file if None)
        threads: FFmpeg thread count
    
    Returns:
        Path to extracted audio file
    """
    return _extract_audio_sdk(
        video_path,
        output_audio_path,
        sample_rate=AUDIO_SAMPLE_RATE,
        channels=AUDIO_CHANNELS,
        codec=AUDIO_CODEC,
        threads=threads,
    )


# ==================== YouTube Subtitle Functions ====================

def check_available_subtitles(url: str) -> dict:
    """
    Check available YouTube subtitles for a video using yt-dlp SDK.
    
    Returns:
        {
            "has_manual": bool,      # Has manually uploaded subtitles
            "has_auto": bool,        # Has auto-generated subtitles
            "available_langs": list, # Available language codes
            "recommended_lang": str   # Recommended language based on priority
        }
    """
    result = {
        "has_manual": False,
        "has_auto": False,
        "available_langs": [],
        "recommended_lang": None
    }
    
    try:
        client = _get_youtube_client()
        subtitle_info = client.list_subtitles(url)
        
        result["has_manual"] = len(subtitle_info.manual) > 0
        result["has_auto"] = len(subtitle_info.auto) > 0
        
        # Get all available languages
        all_langs = list(subtitle_info.available_langs)
        result["available_langs"] = all_langs
        
        # Find recommended language based on priority
        for lang in SUBTITLE_LANG_PRIORITY:
            if lang in all_langs:
                result["recommended_lang"] = lang
                break
        
        if not result["recommended_lang"] and all_langs:
            result["recommended_lang"] = all_langs[0]
        
        return result
        
    except Exception:
        return result


def download_and_convert_subtitles(
    url: str,
    output_dir: str = "/tmp",
    preferred_langs: Optional[list] = None
) -> Tuple[str, dict]:
    """
    Download YouTube subtitles and convert to plain text using yt-dlp SDK.
    
    Args:
        url: YouTube URL
        output_dir: Temporary directory for downloads
        preferred_langs: Language priority list (defaults to SUBTITLE_LANG_PRIORITY)
    
    Returns:
        (transcript text, metadata dict)
    """
    import shutil
    
    if preferred_langs is None:
        preferred_langs = list(SUBTITLE_LANG_PRIORITY)
    
    temp_dir = os.path.join(output_dir, f"subs_{os.getpid()}")
    os.makedirs(temp_dir, exist_ok=True)
    
    metadata = {
        "source": "youtube_subtitles",
        "language": None,
        "is_auto_generated": None,
        "duration": None
    }
    
    try:
        client = _get_youtube_client()
        
        # Get video info for duration
        try:
            info = client.get_video_info(url)
            metadata["duration"] = info.duration
        except Exception:
            pass
        
        # Check available subtitles
        sub_info = check_available_subtitles(url)
        
        if not sub_info["available_langs"]:
            raise Exception("No subtitles available for this video")
        
        # Download best available subtitles
        vtt_path = client.get_best_subtitles(
            url=url,
            preferred_langs=preferred_langs,
            output_dir=temp_dir,
        )
        
        if not vtt_path:
            raise Exception("Failed to download subtitles")
        
        # Parse VTT and convert to plain text
        transcript = _parse_vtt_to_text(vtt_path)
        
        # Determine if auto-generated
        # Check if the downloaded language was in manual or auto list
        subtitle_info = client.list_subtitles(url)
        manual_langs = {t.lang for t in subtitle_info.manual}
        
        # Get the language from the VTT filename (format: {video_id}.{lang}.vtt)
        vtt_filename = os.path.basename(vtt_path)
        parts = vtt_filename.replace('.vtt', '').split('.')
        downloaded_lang = parts[-1] if len(parts) > 1 else None
        
        metadata["language"] = downloaded_lang
        metadata["is_auto_generated"] = downloaded_lang not in manual_langs if downloaded_lang else True
        
        return transcript, metadata
        
    finally:
        # Cleanup temp directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def _parse_vtt_to_text(vtt_path: str) -> str:
    """
    Parse VTT subtitle file and extract plain text.
    
    Removes:
    - WEBVTT header
    - Timestamp lines (containing -->)
    - Numeric cue identifiers
    - Empty lines
    """
    with open(vtt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    text_lines = []
    
    for line in lines:
        line = line.strip()
        
        # Skip VTT header
        if line.startswith('WEBVTT'):
            continue
        
        # Skip timestamp lines
        if '-->' in line:
            continue
        
        # Skip numeric cue identifiers
        if line.isdigit():
            continue
        
        # Skip NOTE blocks
        if line.startswith('NOTE'):
            continue
        
        # Skip empty lines
        if not line:
            continue
        
        # Skip positioning/styling tags
        if line.startswith('position:') or line.startswith('align:'):
            continue
        
        # This is actual text
        text_lines.append(line)
    
    return ' '.join(text_lines)


from .constants import SUPPORTED_LANGUAGES


def transcribe_audio_chunked(
    audio_path: str,
    language: str = "auto",
    model_size: Optional[str] = None,
    device: Optional[str] = None,
    compute_type: Optional[str] = None,
    cpu_threads: Optional[int] = None,
    vad_enabled: bool = True,
    vad_params: Optional[dict] = None,
    word_timestamps: bool = False,
    enable_chunking: bool = False,
    chunk_duration: int = DEFAULT_CHUNK_DURATION,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    auto_enable_threshold: int = DEFAULT_AUTO_CHUNK_THRESHOLD,
) -> Tuple[str, dict]:
    """
    Transcribe audio with optional chunking for long files.
    
    This function addresses Cloudflare 524 timeout issues by splitting
    long audio files into smaller chunks that can be processed within
    the timeout limit.
    
    Args:
        audio_path: Path to audio file
        language: Language code or "auto" for detection
        model_size: Model size (None = use config default)
        device: Compute device (None = use config default)
        compute_type: Compute type (None = use config default)
        cpu_threads: CPU threads (None = auto detect)
        vad_enabled: Enable VAD filtering
        vad_params: Custom VAD parameters
        word_timestamps: Enable word-level timestamps
        enable_chunking: Enable automatic chunking
        chunk_duration: Max duration per chunk (seconds)
        chunk_overlap: Overlap between chunks (seconds)
        auto_enable_threshold: Auto-enable chunking above this duration
    
Returns:
    Tuple of (transcription_text, metadata)
    """
    start_time = time.time()
    model_load_start = time.time()

    effective_device = device or DEFAULT_DEVICE
    effective_compute_type = compute_type or DEFAULT_COMPUTE_TYPE
    effective_threads = cpu_threads or DEFAULT_CPU_THREADS

    try:
        duration = get_audio_duration(audio_path)
    except Exception:
        duration = None

    # Handle auto model selection
    if model_size == "auto" or model_size is None:
        if duration:
            effective_model = get_recommended_model(duration)
        else:
            effective_model = DEFAULT_MODEL
    else:
        effective_model = model_size
    
    chunk_config = ChunkConfig(
        enabled=enable_chunking,
        chunk_duration=chunk_duration,
        overlap_duration=chunk_overlap,
        auto_enable_threshold=auto_enable_threshold,
        max_total_duration=MAX_TOTAL_DURATION,
        min_chunk_duration=MIN_CHUNK_DURATION,
    )
    
    # Determine if chunking should be used
    use_chunking = should_enable_chunking(
        duration=duration,
        config=chunk_config,
    ) if duration else enable_chunking
    
    if not use_chunking:
        return transcribe_audio(
            audio_path=audio_path,
            language=language,
            model_size=effective_model,
            device=effective_device,
            compute_type=effective_compute_type,
            cpu_threads=effective_threads,
            vad_enabled=vad_enabled,
            vad_params=vad_params,
            word_timestamps=word_timestamps,
        )
    
# Load model for chunk transcription
    model = get_model(
        model_size=effective_model,
        device=effective_device,
        compute_type=effective_compute_type,
        cpu_threads=effective_threads,
    )
    model_load_time_ms = int((time.time() - model_load_start) * 1000)

    # Split audio into chunks
    chunks = split_audio_into_chunks(
        file_path=audio_path,
        config=chunk_config,
    )
    
    if not chunks:
        raise RuntimeError("Failed to create audio chunks")
    
    # Process each chunk
    chunk_results = []
    for chunk in chunks:
        try:
            result = transcribe_chunk(
                chunk=chunk,
                model=model,
                language=None if language == "auto" else language,
                beam_size=5,
                vad_filter=vad_enabled,
                temperature=0.0,
            )
            
            chunk_results.append(result)
        except Exception as e:
            chunk_results.append({
                'segments': [],  # Required for merge_transcription_results
                'text': '',
                'language': 'unknown',
                'language_probability': 0.0,
                'chunk_id': chunk.chunk_id,
                'chunk_start': chunk.start_time,
                'chunk_end': chunk.end_time,
                'error': str(e),
            })
    
    # Merge results
    merged = merge_transcription_results(
        results=chunk_results,
        overlap_duration=chunk_overlap,
        min_segment_gap=0.5,
    )
    
# Cleanup temporary chunks
    cleanup_chunks(chunks)

    processing_time_ms = int((time.time() - start_time) * 1000)
    transcription_time_ms = processing_time_ms - model_load_time_ms

    realtime_factor = None
    if duration and transcription_time_ms > 0:
        realtime_factor = round(transcription_time_ms / (duration * 1000), 2)

    metadata = {
        "processing_time_ms": processing_time_ms,
        "transcription_time_ms": transcription_time_ms,
        "chunking_enabled": True,
        "total_chunks": len(chunks),
        "language": merged.get("language", "unknown"),
        "language_probability": merged.get("language_probability", 0.0),
        "model": effective_model,
        "device": effective_device,
        "compute_type": effective_compute_type,
        "backend": "faster-whisper",
        "cpu_threads": effective_threads,
        "model_load_time_ms": model_load_time_ms,
        "realtime_factor": realtime_factor,
        "audio_duration_seconds": duration,
    }
    if duration:
        metadata["original_duration"] = duration

    return merged.get("text", ""), metadata