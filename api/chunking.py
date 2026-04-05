"""
Audio/Video chunking module for long file transcription.

Solves Cloudflare 524 timeout by processing files in segments.

Strategy:
- Split long audio/video into overlapping chunks
- Process each chunk separately
- Merge transcription results with offset correction
- Auto-detect if chunking is needed based on duration
"""

import os
import subprocess
import tempfile
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ChunkConfig:
    """Configuration for chunking strategy."""
    enabled: bool = False
    chunk_duration: int = 60  # seconds per chunk
    overlap_duration: int = 2  # seconds overlap for smooth transitions
    auto_enable_threshold: int = 90  # auto-enable if duration exceeds this (100s - 10s buffer)
    max_total_duration: int = 7200  # 2 hours max
    min_chunk_duration: int = 10  # minimum chunk size in seconds


@dataclass
class AudioChunk:
    """Represents a single audio chunk."""
    chunk_id: int
    start_time: float  # seconds
    end_time: float  # seconds
    file_path: str
    duration: float
    overlap_with_previous: float = 0  # overlap duration with previous chunk


def get_audio_duration(file_path: str) -> float:
    """
    Get audio/video duration using ffprobe.
    
    Args:
        file_path: Path to audio or video file
        
    Returns:
        Duration in seconds
        
    Raises:
        RuntimeError: If ffprobe fails or duration cannot be extracted
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        duration = float(result.stdout.strip())
        return duration
        
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError) as e:
        logger.error(f"Failed to get audio duration: {e}")
        raise RuntimeError(f"Could not determine audio duration: {e}")


def should_enable_chunking(
    duration: float,
    config: ChunkConfig
) -> bool:
    """
    Determine if chunking should be enabled.
    
    Args:
        duration: Audio/video duration in seconds
        config: Chunking configuration
        
    Returns:
        True if chunking should be used
    """
    if config.enabled:
        return duration > config.min_chunk_duration
    
    # Auto-enable if duration exceeds threshold
    return duration > config.auto_enable_threshold


def calculate_chunk_segments(
    duration: float,
    config: ChunkConfig
) -> List[Tuple[float, float]]:
    """
    Calculate chunk start and end times.
    
    Uses overlapping chunks to handle mid-word splits.
    
    Args:
        duration: Total duration in seconds
        config: Chunking configuration
        
    Returns:
        List of (start_time, end_time) tuples
    """
    if duration <= config.chunk_duration:
        return [(0.0, duration)]
    
    segments = []
    start = 0.0
    
    while start < duration:
        end = min(start + config.chunk_duration, duration)
        segments.append((start, end))
        
        # Next chunk starts with overlap (but not for last chunk)
        if end < duration:
            start = end - config.overlap_duration
        else:
            break
    
    return segments


def split_audio_into_chunks(
    file_path: str,
    config: ChunkConfig,
    output_dir: Optional[str] = None
) -> List[AudioChunk]:
    """
    Split audio file into overlapping chunks.
    
    Args:
        file_path: Path to audio or video file
        config: Chunking configuration
        output_dir: Optional directory for chunk files (uses temp dir if None)
        
    Returns:
        List of AudioChunk objects
        
    Raises:
        RuntimeError: If splitting fails
    """
    # Get duration
    duration = get_audio_duration(file_path)
    
    # Check if chunking is needed
    if not should_enable_chunking(duration, config):
        return [AudioChunk(
            chunk_id=0,
            start_time=0.0,
            end_time=duration,
            file_path=file_path,
            duration=duration
        )]
    
    # Calculate segments
    segments = calculate_chunk_segments(duration, config)
    
    # Create output directory
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="audio_chunks_")
    else:
        os.makedirs(output_dir, exist_ok=True)
    
    # Extract file extension
    file_ext = Path(file_path).suffix
    base_name = Path(file_path).stem
    
    chunks = []
    
    for i, (start, end) in enumerate(segments):
        chunk_file = os.path.join(output_dir, f"{base_name}_chunk_{i:03d}{file_ext}")
        
        # Use ffmpeg to extract chunk
        try:
            cmd = [
                'ffmpeg',
                '-y',  # overwrite
                '-i', file_path,
                '-ss', str(start),  # start time
                '-t', str(end - start),  # duration
                '-c', 'copy',  # stream copy for speed
                '-avoid_negative_ts', 'make_zero',
                chunk_file
            ]
            
            subprocess.run(
                cmd,
                capture_output=True,
                check=True
            )
            
            # Calculate overlap with previous chunk
            overlap = 0.0
            if i > 0 and config.overlap_duration > 0:
                prev_start, prev_end = segments[i - 1]
                overlap = max(0, prev_end - start)
            
            chunks.append(AudioChunk(
                chunk_id=i,
                start_time=start,
                end_time=end,
                file_path=chunk_file,
                duration=end - start,
                overlap_with_previous=overlap
            ))
            
            logger.info(f"Created chunk {i}: {start:.2f}s - {end:.2f}s")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create chunk {i}: {e}")
            # Clean up created chunks
            for chunk in chunks:
                try:
                    os.remove(chunk.file_path)
                except:
                    pass
            raise RuntimeError(f"Failed to split audio: {e}")
    
    return chunks


def transcribe_chunk(
    chunk: AudioChunk,
    model,  # WhisperModel instance
    language: Optional[str] = None,
    beam_size: int = 5,
    vad_filter: bool = True,
    temperature: float = 0.0
) -> dict:
    """
    Transcribe a single audio chunk.
    
    Args:
        chunk: AudioChunk to transcribe
        model: FasterWhisper model instance
        language: Language code (e.g., 'zh', 'en')
        beam_size: Beam search size
        vad_filter: Whether to use VAD filter
        temperature: Sampling temperature
        
    Returns:
        Dictionary with segments and text
    """
    from faster_whisper import WhisperModel
    from faster_whisper.transcribe import TranscriptionOptions
    
    try:
        # Transcribe the chunk
        segments, info = model.transcribe(
            chunk.file_path,
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            temperature=temperature
        )
        
        # Convert segments to list
        segment_list = []
        for segment in segments:
            segment_list.append({
                'start': segment.start + chunk.start_time,  # Offset correction
                'end': segment.end + chunk.start_time,
                'text': segment.text.strip()
            })
        
        # Combine text
        full_text = ' '.join(s['text'] for s in segment_list)
        
        return {
            'segments': segment_list,
            'text': full_text,
            'language': info.language,
            'language_probability': info.language_probability,
            'chunk_id': chunk.chunk_id,
            'chunk_start': chunk.start_time,
            'chunk_end': chunk.end_time
        }
        
    except Exception as e:
        logger.error(f"Failed to transcribe chunk {chunk.chunk_id}: {e}")
        raise


def merge_transcription_results(
    results: List[dict],
    overlap_duration: int = 2,
    min_segment_gap: float = 0.5
) -> dict:
    """
    Merge transcription results from chunks.
    
    Handles overlapping regions by preferring text from the first chunk
    and deduplicating segments.
    
    Args:
        results: List of transcription results from chunks
        overlap_duration: Overlap duration in seconds
        min_segment_gap: Minimum gap between segments to merge
        
    Returns:
        Merged transcription result
    """
    if not results:
        return {'segments': [], 'text': ''}
    
    if len(results) == 1:
        return results[0]
    
    # Collect all segments with corrected timestamps
    all_segments = []
    
    for result in results:
        for segment in result['segments']:
            # Already offset-corrected in transcribe_chunk
            all_segments.append(segment)
    
    # Sort by start time
    all_segments.sort(key=lambda s: s['start'])
    
    # Merge overlapping segments
    merged_segments = []
    prev_segment = None
    
    for segment in all_segments:
        if prev_segment is None:
            merged_segments.append(segment)
            prev_segment = segment
            continue
        
        # Check for overlap or gap
        gap = segment['start'] - prev_segment['end']
        
        if gap < -min_segment_gap:
            # Overlapping - skip duplicate text
            # Keep the segment with longer text or later start
            if len(segment['text']) > len(prev_segment['text']):
                merged_segments[-1] = segment
            # else keep previous
        elif gap < min_segment_gap:
            # Small gap - merge into single segment
            merged_segments[-1]['end'] = segment['end']
            merged_segments[-1]['text'] = prev_segment['text'] + ' ' + segment['text']
        else:
            # Significant gap - keep as separate segment
            merged_segments.append(segment)
        
        prev_segment = merged_segments[-1]
    
    # Clean up text
    merged_text = ' '.join(s['text'] for s in merged_segments)
    # Remove duplicate spaces
    merged_text = ' '.join(merged_text.split())
    
    # Get language info from first result
    language = results[0].get('language', 'unknown')
    language_prob = results[0].get('language_probability', 0.0)
    
    return {
        'segments': merged_segments,
        'text': merged_text,
        'language': language,
        'language_probability': language_prob
    }


def cleanup_chunks(chunks: List[AudioChunk]) -> None:
    """
    Clean up temporary chunk files.
    
    Args:
        chunks: List of AudioChunk objects to clean up
    """
    for chunk in chunks:
        try:
            if os.path.exists(chunk.file_path):
                os.remove(chunk.file_path)
                logger.debug(f"Cleaned up chunk file: {chunk.file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up chunk {chunk.file_path}: {e}")


def estimate_processing_time(duration: float, model_size: str = "base") -> float:
    """
    Estimate processing time for given audio duration.
    
    Args:
        duration: Audio duration in seconds
        model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
        
    Returns:
        Estimated processing time in seconds
    """
    # Rough estimates based on model size (realtime factor)
    # CPU: tiny=0.3x, base=0.5x, small=0.8x, medium=1.5x, large=2.5x
    # GPU: tiny=0.05x, base=0.1x, small=0.15x, medium=0.2x, large=0.3x
    
    realtime_factors = {
        'tiny': 0.3,
        'base': 0.5,
        'small': 0.8,
        'medium': 1.5,
        'large': 2.5
    }
    
    factor = realtime_factors.get(model_size, 0.5)
    return duration * factor


def get_chunking_recommendation(duration: float) -> dict:
    """
    Get recommendation for chunking settings based on duration.

    Args:
        duration: Audio/video duration in seconds

    Returns:
        Dictionary with recommended settings
    """
    if duration < 60:
        return {
            'need_chunking': False,
            'reason': 'Duration under 1 minute, chunking not needed',
            'suggested_chunk_duration': duration
        }
    elif duration < 180:
        return {
            'need_chunking': False,
            'reason': 'Duration under 3 minutes, can process in single request (but close to timeout)',
            'suggested_chunk_duration': duration
        }
    elif duration < 600:
        return {
            'need_chunking': True,
            'reason': 'Duration 3-10 minutes, recommend chunking to avoid timeout',
            'suggested_chunk_duration': 60,
            'suggested_overlap': 2,
            'estimated_chunks': int(duration / 60) + 1
        }
    else:
        return {
            'need_chunking': True,
            'reason': 'Duration over 10 minutes, chunking required to avoid timeout',
            'suggested_chunk_duration': 60,
            'suggested_overlap': 2,
            'estimated_chunks': int(duration / 60) + 1
        }


from concurrent.futures import ThreadPoolExecutor, as_completed


def transcribe_audio_parallel(
    audio_path: str,
    language: str,
    model,
    beam_size: int = 1,
    vad_filter: bool = True,
    temperature: float = 0.0,
    max_workers: int = 4,
    chunk_config: ChunkConfig | None = None,
) -> dict:
    """Transcribe audio with parallel chunk processing.

    Splits audio into chunks, processes each chunk in parallel, and merges
    results ordered by timestamp.

    Args:
        audio_path: Path to audio file
        language: Language code for transcription
        model: FasterWhisper model instance
        beam_size: Beam search size
        vad_filter: Whether to use VAD filter
        temperature: Sampling temperature
        max_workers: Maximum number of parallel workers
        chunk_config: Chunking configuration (uses defaults if None)

    Returns:
        Merged transcription result dictionary
    """
    if chunk_config is None:
        chunk_config = ChunkConfig()

    chunks = split_audio_into_chunks(audio_path, chunk_config)

    if not chunks:
        from api.chunking import get_audio_duration

        duration = get_audio_duration(audio_path)
        whole_chunk = AudioChunk(
            chunk_id=0,
            start_time=0,
            end_time=duration,
            file_path=audio_path,
            duration=duration,
            overlap_with_previous=0,
        )
        return transcribe_chunk(
            chunk=whole_chunk,
            model=model,
            language=language,
            beam_size=beam_size,
            vad_filter=vad_filter,
            temperature=temperature,
        )

    max_w = min(max_workers, len(chunks))
    chunk_results = []

    with ThreadPoolExecutor(max_workers=max_w) as executor:
        futures = {
            executor.submit(
                transcribe_chunk,
                chunk=chunk,
                model=model,
                language=language,
                beam_size=beam_size,
                vad_filter=vad_filter,
                temperature=temperature,
            ): chunk
            for chunk in chunks
        }

        for future in as_completed(futures):
            chunk_results.append(future.result())

    merged = merge_transcription_results(
        chunk_results, overlap_duration=chunk_config.overlap_duration
    )
    cleanup_chunks(chunks)

    return merged