"""
Subtitle formatting module for Whisper transcription.

Supports multiple output formats:
- SRT (SubRip subtitle format)
- VTT (WebVTT format)
"""

from typing import List, Dict
from dataclasses import dataclass


@dataclass
class SubtitleSegment:
    """Represents a single subtitle segment with timing."""
    index: int
    start: float  # seconds
    end: float    # seconds
    text: str


def seconds_to_srt_time(seconds: float) -> str:
    """
    Convert seconds to SRT time format (HH:MM:SS,mmm).
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Time string in SRT format
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def seconds_to_vtt_time(seconds: float) -> str:
    """
    Convert seconds to VTT time format (HH:MM:SS.mmm).
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Time string in VTT format
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def format_segments_as_srt(segments: List[Dict]) -> str:
    """
    Format transcription segments as SRT subtitle format.
    
    Args:
        segments: List of segments with 'start', 'end', 'text' keys
        
    Returns:
        SRT formatted string
    """
    lines = []
    
    for i, segment in enumerate(segments, 1):
        start = seconds_to_srt_time(segment['start'])
        end = seconds_to_srt_time(segment['end'])
        text = segment['text'].strip()
        
        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")  # Empty line between entries
    
    return "\n".join(lines)


def format_segments_as_vtt(segments: List[Dict]) -> str:
    """
    Format transcription segments as VTT subtitle format.
    
    Args:
        segments: List of segments with 'start', 'end', 'text' keys
        
    Returns:
        VTT formatted string
    """
    lines = ["WEBVTT", ""]  # VTT header
    
    for i, segment in enumerate(segments, 1):
        start = seconds_to_vtt_time(segment['start'])
        end = seconds_to_vtt_time(segment['end'])
        text = segment['text'].strip()
        
        # Optional: Add cue identifier
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")  # Empty line between cues
    
    return "\n".join(lines)


def format_transcript_with_timestamps(
    segments: List[Dict],
    include_timestamps: bool = True
) -> str:
    """
    Format transcript with optional timestamps in markdown.
    
    Args:
        segments: List of segments with 'start', 'end', 'text' keys
        include_timestamps: Whether to include timestamps
        
    Returns:
        Formatted transcript text
    """
    if not include_timestamps:
        return " ".join(s['text'].strip() for s in segments)
    
    lines = []
    for segment in segments:
        start_time = format_timestamp_readable(segment['start'])
        text = segment['text'].strip()
        lines.append(f"[{start_time}] {text}")
    
    return "\n\n".join(lines)


def format_timestamp_readable(seconds: float) -> str:
    """
    Format seconds as readable timestamp (MM:SS or HH:MM:SS).
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Readable timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:d}:{secs:02d}"


def format_multiline_output(
    segments: List[Dict],
    output_format: str = "markdown",
    include_timestamps: bool = False
) -> Dict[str, str]:
    """
    Generate multiple output formats from segments.
    
    Args:
        segments: List of segments with 'start', 'end', 'text' keys
        output_format: Comma-separated list of formats (markdown,srt,vtt)
        include_timestamps: Whether to include timestamps in Markdown output
        
    Returns:
        Dictionary mapping format names to formatted strings
    """
    formats = [f.strip().lower() for f in output_format.split(",")]
    result = {}
    
    if "markdown" in formats or "md" in formats:
        result["markdown"] = format_transcript_with_timestamps(segments, include_timestamps)
    
    if "srt" in formats:
        result["srt"] = format_segments_as_srt(segments)
    
    if "vtt" in formats:
        result["vtt"] = format_segments_as_vtt(segments)
    
    if "text" in formats or "txt" in formats:
        result["text"] = " ".join(s['text'].strip() for s in segments)
    
    return result