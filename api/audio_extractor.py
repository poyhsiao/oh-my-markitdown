"""Audio extraction module using ffmpeg-python SDK.

Provides audio extraction from video files, optimized for Whisper transcription.
"""

import os
import tempfile
from typing import Optional

import ffmpeg

from api.constants import (
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    AUDIO_CODEC,
    AUDIO_FFMPEG_THREADS,
)


class AudioExtractionError(Exception):
    """Audio extraction failed."""
    pass


class AudioExtractionTimeout(AudioExtractionError):
    """Audio extraction timed out."""
    pass


def extract_audio_from_video(
    video_path: str,
    output_audio_path: Optional[str] = None,
    *,
    sample_rate: int = AUDIO_SAMPLE_RATE,
    channels: int = AUDIO_CHANNELS,
    codec: str = AUDIO_CODEC,
    threads: int = AUDIO_FFMPEG_THREADS,
) -> str:
    """Extract audio from video file.

    Uses ffmpeg-python SDK to extract audio optimized for Whisper:
    - 16kHz sample rate (Whisper native)
    - Mono channel
    - WAV/PCM format (no compression overhead)

    Args:
        video_path: Input video file path
        output_audio_path: Output audio file path (auto-generated if None)
        sample_rate: Audio sample rate (default: 16000 Hz)
        channels: Number of audio channels (default: 1, mono)
        codec: Audio codec (default: pcm_s16le)
        threads: Number of decoding threads (default: 4)

    Returns:
        Path to extracted audio file

    Raises:
        AudioExtractionError: Audio extraction failed
        FileNotFoundError: Video file not found
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if output_audio_path is None:
        output_audio_path = tempfile.mktemp(suffix=".wav")

    try:
        stream = (
            ffmpeg
            .input(video_path, threads=threads)
            .output(
                output_audio_path,
                vn=None,
                ac=channels,
                ar=sample_rate,
                acodec=codec,
            )
            .overwrite_output()
        )

        stream.run(capture_stdout=True, capture_stderr=True, quiet=True)

        if not os.path.exists(output_audio_path):
            raise AudioExtractionError(
                "Audio extraction failed: output file not created"
            )

        return output_audio_path

    except ffmpeg.Error as e:
        error_msg = e.stderr.decode("utf-8") if e.stderr else str(e)
        raise AudioExtractionError(f"Audio extraction failed: {error_msg}") from e
    except AudioExtractionError:
        raise
    except Exception as e:
        raise AudioExtractionError(f"Audio extraction failed: {e}") from e


def get_audio_info(audio_path: str) -> dict:
    """Get audio file information.

    Args:
        audio_path: Audio file path

    Returns:
        Dictionary with audio information (sample_rate, channels, duration, codec, bit_rate)

    Raises:
        AudioExtractionError: Failed to get audio info
    """
    try:
        probe = ffmpeg.probe(audio_path)

        audio_stream = next(
            (s for s in probe["streams"] if s["codec_type"] == "audio"),
            None
        )

        if audio_stream is None:
            raise AudioExtractionError("No audio stream found")

        return {
            "sample_rate": int(audio_stream.get("sample_rate", 0)),
            "channels": int(audio_stream.get("channels", 0)),
            "duration": float(probe["format"].get("duration", 0)),
            "codec": audio_stream.get("codec_name", "unknown"),
            "bit_rate": int(probe["format"].get("bit_rate", 0)),
        }

    except ffmpeg.Error as e:
        error_msg = e.stderr.decode("utf-8") if e.stderr else str(e)
        raise AudioExtractionError(f"Failed to get audio info: {error_msg}") from e
    except Exception as e:
        raise AudioExtractionError(f"Failed to get audio info: {e}") from e


def validate_video_file(video_path: str) -> bool:
    """Check if video file contains extractable audio.

    Args:
        video_path: Video file path

    Returns:
        True if video has audio stream, False otherwise
    """
    try:
        probe = ffmpeg.probe(video_path)

        audio_streams = [
            s for s in probe["streams"]
            if s["codec_type"] == "audio"
        ]

        return len(audio_streams) > 0

    except Exception:
        return False