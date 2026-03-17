"""
Whisper Transcription Module
Use Faster-Whisper for local speech-to-text
"""

import os
import tempfile
import subprocess
from typing import Optional, Tuple, Dict, List
from faster_whisper import WhisperModel

from .constants import WHISPER_MODEL_CACHE_SIZE
from .subtitles import format_multiline_output, format_transcript_with_timestamps

# Read configuration from environment variables
DEFAULT_MODEL = os.getenv("WHISPER_MODEL", "base")
DEFAULT_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
DEFAULT_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

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

def get_model(
    model_size: str = None, 
    device: str = None, 
    compute_type: str = None
):
    """
    Get or load Whisper model
    
    Args:
        model_size: Model size (tiny, base, small, medium, large)
        device: Device to run on (cpu, cuda)
        compute_type: Compute type (int8, float16, float32)
    
    Returns:
        WhisperModel instance
    """
    # Use environment variables or defaults
    model_size = model_size or DEFAULT_MODEL
    device = device or DEFAULT_DEVICE
    compute_type = compute_type or DEFAULT_COMPUTE_TYPE
    
    cache_key = f"{model_size}_{device}_{compute_type}"
    
    model = _model_cache.get(cache_key)
    if model is None:
        print(f"[Whisper] Loading model: {model_size} (device={device}, compute_type={compute_type})")
        model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )
        _model_cache.set(cache_key, model)
    
    return model


def transcribe_audio(
    audio_path: str,
    language: str = "auto",
    model_size: str = "base",
    device: str = "cpu",
    compute_type: str = "int8",
    word_timestamps: bool = False
) -> Tuple[str, dict]:
    """
    Transcribe audio file
    
    Args:
        audio_path: Audio file path
        language: Language code (auto=auto-detect, zh, en, ja, ko, etc.)
        model_size: Model size
        device: Device to run on
        compute_type: Compute type
        word_timestamps: Whether to return word-level timestamps
    
    Returns:
        (transcript text, metadata)
    """
    # Handle "auto" for auto-detection (Whisper expects None for auto-detect)
    actual_language = None if language == "auto" else language
    
    # Load model
    model = get_model(model_size, device, compute_type)
    
    # Transcribe
    segments, info = model.transcribe(
        audio_path,
        language=actual_language,
        word_timestamps=word_timestamps,
        vad_filter=True,  # Use VAD to filter silence
        vad_parameters=dict(min_silence_duration_ms=500)
    )
    
    # Combine text
    transcript_lines = []
    for segment in segments:
        transcript_lines.append(segment.text)
    
    transcript = " ".join(transcript_lines)
    
    # Metadata
    metadata = {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "duration_after_vad": info.duration_after_vad,
        "segments_count": len(list(segments)) if segments else 0,
        "model": model_size,
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


def download_youtube_audio(url: str, output_dir: str = "/tmp") -> Tuple[str, str]:
    """
    Download audio from YouTube video
    
    Args:
        url: YouTube URL
        output_dir: Output directory
    
    Returns:
        (audio file path, video title)
    """
    # Get video info
    result = subprocess.run(
        ["yt-dlp", "--print", "%(title)s|||%(id)s", url],
        capture_output=True,
        text=True,
        timeout=60
    )
    
    if result.returncode != 0:
        raise Exception(f"Failed to get YouTube info: {result.stderr}")
    
    parts = result.stdout.strip().split("|||")
    title = parts[0] if len(parts) > 0 else "Unknown"
    video_id = parts[1] if len(parts) > 1 else "unknown"
    
    # Download audio
    output_path = os.path.join(output_dir, f"{video_id}.mp3")
    
    result = subprocess.run(
        ["yt-dlp", "-x", "--audio-format", "mp3", "-o", output_path, url],
        capture_output=True,
        text=True,
        timeout=300
    )
    
    if result.returncode != 0:
        raise Exception(f"Failed to download YouTube audio: {result.stderr}")
    
    return output_path, title


def transcribe_youtube_video(
    url: str,
    language: str = "zh",
    model_size: str = "base",
    output_dir: str = "/tmp"
) -> dict:
    """
    Download YouTube video and transcribe
    
    Args:
        url: YouTube URL
        language: Language code
        model_size: Model size
        output_dir: Temporary file directory
    
    Returns:
        Dictionary containing transcript results and metadata
    """
# Download audio
    audio_path, title = download_youtube_audio(url, output_dir)
    
    try:
        # Transcribe
        transcript, metadata = transcribe_audio(
            audio_path,
            language=language,
            model_size=model_size
        )
        
        return {
            "success": True,
            "title": title,
            "transcript": transcript,
            "metadata": metadata,
            "audio_path": audio_path
        }
        
    except Exception as e:
        # Clean up temporary files
        if os.path.exists(audio_path):
            os.unlink(audio_path)
        raise e


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
        md_lines.extend([
            "## Transcription Info",
            "",
            f"- **Language**: {metadata.get('language', 'unknown')}",
            f"- **Duration**: {metadata.get('duration', 0):.1f} seconds",
            f"- **Model**: {metadata.get('model', 'unknown')}",
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
    model_size: str = "base",
    output_formats: str = "markdown",
    include_timestamps: bool = False
) -> Tuple[Dict[str, str], dict]:
    """
    Transcribe audio and return multiple format outputs
    
    Args:
        audio_path: Audio file path
        language: Language code (auto=auto-detect)
        model_size: Model size
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
        model_size=model_size
    )
    
    # Use subtitles module to generate multiple formats
    formats_dict = format_multiline_output(
        segments_list,
        output_format=output_formats
    )
    
    # If timestamps needed, regenerate Markdown
    if include_timestamps and "markdown" in formats_dict:
        formats_dict["markdown"] = format_transcript_with_timestamps(
            segments_list,
            include_timestamps=True
        )
    
    # Metadata
    metadata = {
        "language": language,
        "model": model_size,
        "segments_count": len(segments_list),
        "formats": list(formats_dict.keys())
    }
    
    return formats_dict, metadata


def extract_audio_from_video(
    video_path: str,
    output_audio_path: Optional[str] = None
) -> str:
    """
    Extract audio from video file
    
    Args:
        video_path: Video file path
        output_audio_path: Output audio file path (optional)
    
    Returns:
        Extracted audio file path
    """
    if output_audio_path is None:
        # Auto-generate output path
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_audio_path = os.path.join(
            tempfile.gettempdir(),
            f"{base_name}.mp3"
        )
    
    # Use ffmpeg to extract audio
    result = subprocess.run(
        [
            "ffmpeg",
            "-i", video_path,
            "-vn",  # No video
            "-acodec", "libmp3lame",  # Use MP3 codec
            "-y",  # Overwrite output file
            output_audio_path
        ],
        capture_output=True,
        text=True,
        timeout=300  # 5 minutes timeout
    )
    
    if result.returncode != 0:
        raise Exception(f"Failed to extract audio from video: {result.stderr}")
    
    return output_audio_path


from .constants import SUPPORTED_LANGUAGES