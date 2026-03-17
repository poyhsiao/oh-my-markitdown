"""
Whisper Transcription Module
Use Faster-Whisper for local speech-to-text
"""

import os
import tempfile
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from faster_whisper import WhisperModel

from .constants import WHISPER_MODEL_CACHE_SIZE, DEFAULT_YOUTUBE_INFO_TIMEOUT, DEFAULT_YOUTUBE_DOWNLOAD_TIMEOUT, DEFAULT_AUDIO_EXTRACT_TIMEOUT, SUBTITLE_LANG_PRIORITY, SUBTITLE_DOWNLOAD_TIMEOUT
from .subtitles import format_multiline_output, format_transcript_with_timestamps

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

def get_model(
    model_size: str = None, 
    device: str = None, 
    compute_type: str = None,
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
    model_size: str = "base",
    device: str = "cpu",
    compute_type: str = "int8",
    word_timestamps: bool = False,
    cpu_threads: int = 4
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
        cpu_threads: Number of CPU threads for parallel processing (CPU only, default: 4)
    
    Returns:
        (transcript text, metadata)
    """
    # Handle "auto" for auto-detection (Whisper expects None for auto-detect)
    actual_language = None if language == "auto" else language
    
    # Load model with CPU threading support
    model = get_model(model_size, device, compute_type, cpu_threads=cpu_threads)
    
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


def download_youtube_audio(
    url: str, 
    output_dir: str = "/tmp",
    audio_quality: str = "128K"
) -> Tuple[str, str]:
    """
    Download audio from YouTube video
    
    Args:
        url: YouTube URL
        output_dir: Output directory
        audio_quality: Audio quality (128K default, 64K for faster download)
    
    Returns:
        (audio file path, video title)
    """
    result = subprocess.run(
        ["yt-dlp", "--no-check-certificate", "--print", "%(title)s|||%(id)s", url],
        capture_output=True,
        text=True,
        timeout=YOUTUBE_INFO_TIMEOUT
    )
    
    if result.returncode != 0:
        raise Exception(f"Failed to get YouTube info: {result.stderr}")
    
    parts = result.stdout.strip().split("|||")
    title = parts[0] if len(parts) > 0 else "Unknown"
    video_id = parts[1] if len(parts) > 1 else "unknown"
    
    output_path = os.path.join(output_dir, f"{video_id}.mp3")
    
    result = subprocess.run(
        [
            "yt-dlp", 
            "--no-check-certificate", 
            "-x", 
            "--audio-format", "mp3",
            "--audio-quality", audio_quality,
            "-o", output_path, 
            url
        ],
        capture_output=True,
        text=True,
        timeout=YOUTUBE_DOWNLOAD_TIMEOUT
    )
    
    if result.returncode != 0:
        raise Exception(f"Failed to download YouTube audio: {result.stderr}")
    
    return output_path, title


def transcribe_youtube_video(
    url: str,
    language: str = "zh",
    model_size: str = "base",
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
        model_size: Model size (for Whisper)
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
        # Transcribe with optional optimizations
        # Use more CPU threads in fast_mode for faster processing
        cpu_threads = 8 if fast_mode else 4
        transcript, metadata = transcribe_audio(
            audio_path,
            language=language,
            model_size=model_size,
            cpu_threads=cpu_threads
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
    """Get YouTube video title without downloading."""
    try:
        proc = subprocess.run(
            ["yt-dlp", "--no-check-certificate", "--print", "%(title)s", url],
            capture_output=True,
            text=True,
            timeout=YOUTUBE_INFO_TIMEOUT
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except:
        pass
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
    
    result = subprocess.run(
        [
            "ffmpeg",
            "-i", video_path,
            "-vn",
            "-acodec", "libmp3lame",
            "-y",
            output_audio_path
        ],
        capture_output=True,
        text=True,
        timeout=AUDIO_EXTRACT_TIMEOUT
    )
    
    if result.returncode != 0:
        raise Exception(f"Failed to extract audio from video: {result.stderr}")
    
    return output_audio_path


# ==================== YouTube Subtitle Functions ====================

def check_available_subtitles(url: str) -> dict:
    """
    Check available YouTube subtitles for a video.
    
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
        proc = subprocess.run(
            ["yt-dlp", "--list-subs", "--no-download", "--no-check-certificate", url],
            capture_output=True,
            text=True,
            timeout=YOUTUBE_INFO_TIMEOUT
        )
        
        if proc.returncode != 0:
            return result
        
        output = proc.stdout
        lines = output.split('\n')
        
        manual_langs = []
        auto_langs = []
        
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if 'Available subtitles' in line:
                current_section = 'manual'
                result["has_manual"] = True
            elif 'Available automatic captions' in line or 'Automatic captions' in line:
                current_section = 'auto'
                result["has_auto"] = True
            elif current_section and line[0:2].isalpha():
                lang_code = line.split()[0] if line.split() else None
                if lang_code and len(lang_code) <= 10:
                    if current_section == 'manual':
                        manual_langs.append(lang_code)
                    else:
                        auto_langs.append(lang_code)
        
        # Prioritize manual subtitles over auto
        result["available_langs"] = manual_langs + auto_langs
        
        # Find recommended language based on priority
        for lang in SUBTITLE_LANG_PRIORITY:
            if lang in result["available_langs"]:
                result["recommended_lang"] = lang
                break
        
        if not result["recommended_lang"] and result["available_langs"]:
            result["recommended_lang"] = result["available_langs"][0]
        
        return result
        
    except subprocess.TimeoutExpired:
        return result
    except Exception:
        return result


def download_and_convert_subtitles(
    url: str,
    output_dir: str = "/tmp",
    preferred_langs: list = None
) -> Tuple[str, dict]:
    """
    Download YouTube subtitles and convert to plain text.
    
    Args:
        url: YouTube URL
        output_dir: Temporary directory for downloads
        preferred_langs: Language priority list (defaults to SUBTITLE_LANG_PRIORITY)
    
    Returns:
        (transcript text, metadata dict)
    """
    import shutil
    
    if preferred_langs is None:
        preferred_langs = SUBTITLE_LANG_PRIORITY
    
    temp_dir = os.path.join(output_dir, f"subs_{os.getpid()}")
    os.makedirs(temp_dir, exist_ok=True)
    
    metadata = {
        "source": "youtube_subtitles",
        "language": None,
        "is_auto_generated": None,
        "duration": None
    }
    
    try:
        # Get video info first
        info_proc = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download", "--no-check-certificate", url],
            capture_output=True,
            text=True,
            timeout=YOUTUBE_INFO_TIMEOUT
        )
        
        video_duration = None
        if info_proc.returncode == 0:
            try:
                import json
                info = json.loads(info_proc.stdout)
                video_duration = info.get("duration")
            except:
                pass
        
        # Check available subtitles
        sub_info = check_available_subtitles(url)
        
        if not sub_info["available_langs"]:
            raise Exception("No subtitles available for this video")
        
        # Determine which language to download
        target_lang = None
        for lang in preferred_langs:
            if lang in sub_info["available_langs"]:
                target_lang = lang
                break
        
        if not target_lang:
            target_lang = sub_info["recommended_lang"]
        
        if not target_lang:
            raise Exception("Could not determine subtitle language")
        
        # Download subtitles
        output_template = os.path.join(temp_dir, "%(id)s.%(ext)s")
        
        proc = subprocess.run(
            [
                "yt-dlp",
                "--write-subs",
                "--write-auto-subs",
                "--sub-lang", target_lang,
                "--skip-download",
                "--sub-format", "vtt",
                "--convert-subs", "vtt",
                "-o", output_template,
                "--no-check-certificate",
                url
            ],
            capture_output=True,
            text=True,
            timeout=SUBTITLE_DOWNLOAD_TIMEOUT
        )
        
        if proc.returncode != 0:
            raise Exception(f"Failed to download subtitles: {proc.stderr}")
        
        # Find downloaded VTT file
        vtt_files = list(Path(temp_dir).glob("*.vtt"))
        
        if not vtt_files:
            raise Exception("No subtitle files found after download")
        
        # Use the first matching VTT file
        vtt_file = vtt_files[0]
        
        # Parse VTT and convert to plain text
        transcript = _parse_vtt_to_text(str(vtt_file))
        
        # Set metadata
        metadata["language"] = target_lang
        metadata["is_auto_generated"] = target_lang not in (sub_info["available_langs"][:len([l for l in sub_info["available_langs"] if sub_info["has_manual"]])]) if sub_info["has_manual"] else True
        metadata["duration"] = video_duration
        
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