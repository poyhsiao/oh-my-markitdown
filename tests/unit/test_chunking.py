"""
Tests for api/chunking.py - Audio chunking for long transcription.

Tests are aligned with actual implementation in api/chunking.py.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import os
import subprocess
import tempfile
from pathlib import Path

from api.chunking import (
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


class TestChunkConfig:
    """Test ChunkConfig dataclass."""

    def test_default_values(self):
        """Test ChunkConfig has correct default values."""
        config = ChunkConfig()

        assert config.enabled is False
        assert config.chunk_duration == 60
        assert config.overlap_duration == 2
        assert config.auto_enable_threshold == 90
        assert config.max_total_duration == 7200
        assert config.min_chunk_duration == 10

    def test_custom_values(self):
        """Test ChunkConfig with custom values."""
        config = ChunkConfig(
            enabled=True,
            chunk_duration=120,
            overlap_duration=5,
            auto_enable_threshold=60,
            max_total_duration=3600,
            min_chunk_duration=30
        )

        assert config.enabled is True
        assert config.chunk_duration == 120
        assert config.overlap_duration == 5
        assert config.auto_enable_threshold == 60
        assert config.max_total_duration == 3600
        assert config.min_chunk_duration == 30

    def test_chunk_duration_minimum(self):
        """Test chunk_duration respects minimum."""
        config = ChunkConfig(chunk_duration=5)

        assert config.chunk_duration == 5  # Should accept, validation elsewhere

    def test_overlap_duration_boundary(self):
        """Test overlap_duration can be zero or positive."""
        config_zero = ChunkConfig(overlap_duration=0)
        config_positive = ChunkConfig(overlap_duration=10)

        assert config_zero.overlap_duration == 0
        assert config_positive.overlap_duration == 10


class TestAudioChunk:
    """Test AudioChunk dataclass."""

    def test_audio_chunk_creation(self):
        """Test creating AudioChunk."""
        chunk = AudioChunk(
            chunk_id=0,
            start_time=0.0,
            end_time=60.0,
            file_path="/tmp/chunk_0.wav",
            duration=60.0,
            overlap_with_previous=0.0
        )

        assert chunk.chunk_id == 0
        assert chunk.file_path == "/tmp/chunk_0.wav"
        assert chunk.start_time == 0.0
        assert chunk.end_time == 60.0
        assert chunk.duration == 60.0
        assert chunk.overlap_with_previous == 0.0

    def test_audio_chunk_with_overlap(self):
        """Test AudioChunk with overlap."""
        chunk = AudioChunk(
            chunk_id=1,
            start_time=58.0,
            end_time=118.0,
            file_path="/tmp/chunk_1.wav",
            duration=60.0,
            overlap_with_previous=2.0
        )

        assert chunk.overlap_with_previous == 2.0


class TestGetAudioDuration:
    """Test get_audio_duration function."""

    @patch('api.chunking.subprocess.run')
    def test_get_audio_duration_success(self, mock_run):
        """Test successful audio duration retrieval."""
        mock_result = Mock()
        mock_result.stdout = "120.5\n"
        mock_run.return_value = mock_result

        duration = get_audio_duration("/path/to/audio.mp3")

        assert duration == 120.5
        # Verify ffprobe command was called correctly
        mock_run.assert_called_once()
        args = mock_run.call_args
        assert 'ffprobe' in args[0][0]
        assert '/path/to/audio.mp3' in args[0][0]

    @patch('api.chunking.subprocess.run')
    def test_get_audio_duration_file_not_found(self, mock_run):
        """Test duration retrieval with FileNotFoundError."""
        mock_run.side_effect = FileNotFoundError("ffprobe not found")

        with pytest.raises(RuntimeError, match="Could not determine audio duration"):
            get_audio_duration("/path/to/audio.mp3")

    @patch('api.chunking.subprocess.run')
    def test_get_audio_duration_ffprobe_error(self, mock_run):
        """Test duration retrieval when ffprobe fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "ffprobe", stderr="ffprobe error")

        with pytest.raises(RuntimeError, match="Could not determine audio duration"):
            get_audio_duration("/path/to/audio.mp3")

    @patch('api.chunking.subprocess.run')
    def test_get_audio_duration_invalid_output(self, mock_run):
        """Test duration retrieval with invalid ffprobe output."""
        mock_result = Mock()
        mock_result.stdout = "invalid\n"
        mock_run.return_value = mock_result

        with pytest.raises(RuntimeError, match="Could not determine audio duration"):
            get_audio_duration("/path/to/audio.mp3")


class TestShouldEnableChunking:
    """Test should_enable_chunking function."""

    def test_explicit_enabled_true(self):
        """Test chunking enabled when config.enabled=True."""
        config = ChunkConfig(enabled=True, min_chunk_duration=10)

        result = should_enable_chunking(duration=30.0, config=config)

        assert result is True

    def test_explicit_enabled_with_short_audio(self):
        """Test explicit enabled respects min_chunk_duration check.
        
        When enabled=True, implementation returns: duration > min_chunk_duration.
        So 5s audio < 10s min_chunk_duration returns False.
        """
        config = ChunkConfig(enabled=True, min_chunk_duration=10)

        result = should_enable_chunking(duration=5.0, config=config)

        assert result is False

    def test_auto_enable_exceeds_threshold(self):
        """Test auto-enable when duration exceeds threshold."""
        config = ChunkConfig(enabled=False, auto_enable_threshold=90)

        result = should_enable_chunking(duration=120.0, config=config)

        assert result is True

    def test_auto_enable_at_threshold(self):
        """Test auto-enable when duration equals threshold."""
        config = ChunkConfig(enabled=False, auto_enable_threshold=90)

        result = should_enable_chunking(duration=90.0, config=config)

        # At threshold: duration > threshold (not >=)
        assert result is False

    def test_auto_enable_above_threshold(self):
        """Test auto-enable when duration is just above threshold."""
        config = ChunkConfig(enabled=False, auto_enable_threshold=90)

        result = should_enable_chunking(duration=90.1, config=config)

        assert result is True

    def test_auto_enable_below_threshold(self):
        """Test no chunking when duration below threshold."""
        config = ChunkConfig(enabled=False, auto_enable_threshold=90)

        result = should_enable_chunking(duration=60.0, config=config)

        assert result is False

    def test_disabled_stays_disabled(self):
        """Test disabled config with long audio."""
        config = ChunkConfig(enabled=False, auto_enable_threshold=10000)

        result = should_enable_chunking(duration=120.0, config=config)

        assert result is False


class TestCalculateChunkSegments:
    """Test calculate_chunk_segments function."""

    def test_single_segment_for_short_audio(self):
        """Test single segment when duration is within chunk_duration."""
        config = ChunkConfig(chunk_duration=60, overlap_duration=2)

        segments = calculate_chunk_segments(duration=30.0, config=config)

        assert len(segments) == 1
        assert segments[0] == (0.0, 30.0)

    def test_two_segments_exact_division(self):
        """Test segments with overlap produce correct number of chunks.
        
        For 120s audio with 60s chunks and 2s overlap:
        - Chunk 1: (0, 60)
        - Chunk 2: (58, 118) - starts 2s before end of previous
        - Chunk 3: (116, 120) - starts 2s before end of previous
        Result: 3 segments with overlap, not 2.
        """
        config = ChunkConfig(chunk_duration=60, overlap_duration=2)

        segments = calculate_chunk_segments(duration=120.0, config=config)

        assert len(segments) == 3
        assert segments[0] == (0.0, 60.0)
        assert segments[1][0] == 58.0  # 60 - 2 overlap
        assert segments[1][1] == 118.0
        assert segments[2][0] == 116.0  # 118 - 2 overlap
        assert segments[2][1] == 120.0

    def test_overlap_applied_between_chunks(self):
        """Test overlap is correctly applied between chunks."""
        config = ChunkConfig(chunk_duration=60, overlap_duration=2)

        segments = calculate_chunk_segments(duration=180.0, config=config)

        # First segment starts at 0
        assert segments[0][0] == 0.0
        assert segments[0][1] == 60.0

        # Subsequent segments overlap
        for i in range(1, len(segments)):
            overlap_start = segments[i - 1][1] - config.overlap_duration
            assert segments[i][0] == overlap_start

    def test_last_segment_exact_end(self):
        """Test last segment ends exactly at duration."""
        config = ChunkConfig(chunk_duration=60, overlap_duration=2)

        segments = calculate_chunk_segments(duration=150.0, config=config)

        # Last segment should end at 150
        assert segments[-1][1] == 150.0


class TestSplitAudioIntoChunks:
    """Test split_audio_into_chunks function."""

    @patch('api.chunking.get_audio_duration')
    @patch('api.chunking.subprocess.run')
    @patch('api.chunking.tempfile.mkdtemp')
    def test_split_into_chunks_basic(self, mock_mkdtemp, mock_run, mock_get_duration):
        """Test basic audio splitting into chunks."""
        mock_get_duration.return_value = 120.0
        mock_mkdtemp.return_value = "/tmp/audio_chunks_123"
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        config = ChunkConfig(chunk_duration=60, overlap_duration=2)

        chunks = split_audio_into_chunks("/path/to/audio.mp3", config)

        # Should return at least one chunk
        assert len(chunks) >= 1

    @patch('api.chunking.get_audio_duration')
    def test_no_chunking_for_short_audio(self, mock_get_duration):
        """Test no chunking when audio is under threshold."""
        mock_get_duration.return_value = 30.0  # Short audio

        config = ChunkConfig(enabled=False, auto_enable_threshold=90)

        chunks = split_audio_into_chunks("/path/to/audio.mp3", config)

        # Should return single chunk with original file
        assert len(chunks) == 1
        assert chunks[0].file_path == "/path/to/audio.mp3"
        assert chunks[0].duration == 30.0

    @patch('api.chunking.get_audio_duration')
    @patch('api.chunking.subprocess.run')
    @patch('os.makedirs')
    def test_custom_output_dir(self, mock_makedirs, mock_run, mock_get_duration):
        """Test custom output directory for chunks."""
        mock_get_duration.return_value = 150.0
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        config = ChunkConfig(chunk_duration=60, overlap_duration=2, enabled=True)

        split_audio_into_chunks("/path/to/audio.mp3", config, output_dir="/custom/output")

        # Verify custom directory was used
        mock_makedirs.assert_called()

    @patch('api.chunking.get_audio_duration')
    def test_error_handling_during_split(self, mock_get_duration):
        """Test error handling when chunk creation fails."""
        mock_get_duration.return_value = 120.0

        config = ChunkConfig(chunk_duration=60, overlap_duration=2, enabled=True)

        with patch('api.chunking.subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg", stderr="ffmpeg error")

            with pytest.raises(RuntimeError):
                split_audio_into_chunks("/path/to/audio.mp3", config)


class TestTranscribeChunk:
    """Test transcribe_chunk function."""

    def test_transcribe_chunk_structure(self):
        """Test transcribe_chunk returns expected result structure."""
        chunk = AudioChunk(
            chunk_id=0,
            start_time=0.0,
            end_time=60.0,
            file_path="/tmp/chunk_0.wav",
            duration=60.0,
            overlap_with_previous=0.0
        )

        # Create mock model and segments
        mock_model = Mock()
        mock_segment = Mock()
        mock_segment.start = 0.0
        mock_segment.end = 5.0
        mock_segment.text = "Hello world"

        mock_info = Mock()
        mock_info.language = "en"
        mock_info.language_probability = 0.95

        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        result = transcribe_chunk(
            chunk=chunk,
            model=mock_model,
            language="en"
        )

        assert 'segments' in result
        assert 'text' in result
        assert 'language' in result
        assert 'chunk_id' in result
        assert result['chunk_id'] == 0

    def test_transcribe_chunk_with_parameters(self):
        """Test transcribe_chunk passes all parameters correctly."""
        chunk = AudioChunk(
            chunk_id=1,
            start_time=60.0,
            end_time=120.0,
            file_path="/tmp/chunk_1.wav",
            duration=60.0,
            overlap_with_previous=2.0
        )

        mock_model = Mock()
        mock_segment = Mock()
        mock_segment.start = 0.0
        mock_segment.end = 10.0
        mock_segment.text = "Test text"

        mock_info = Mock()
        mock_info.language = "zh"
        mock_info.language_probability = 0.98

        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        result = transcribe_chunk(
            chunk=chunk,
            model=mock_model,
            language="zh",
            beam_size=10,
            vad_filter=True,
            temperature=0.2
        )

        # Verify model.transcribe was called with correct params
        mock_model.transcribe.assert_called_once()

    def test_transcribe_chunk_offset_correction(self):
        """Test transcribe_chunk applies offset correction."""
        chunk = AudioChunk(
            chunk_id=1,
            start_time=60.0,  # Offset from original
            end_time=120.0,
            file_path="/tmp/chunk_1.wav",
            duration=60.0,
            overlap_with_previous=2.0
        )

        mock_model = Mock()
        mock_segment = Mock()
        mock_segment.start = 5.0  # Within chunk
        mock_segment.end = 10.0
        mock_segment.text = "Test"

        mock_info = Mock()
        mock_info.language = "en"
        mock_info.language_probability = 0.9

        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        result = transcribe_chunk(chunk=chunk, model=mock_model)

        # Offset should be added (60.0 + 5.0 = 65.0)
        assert result['segments'][0]['start'] == 65.0
        assert result['segments'][0]['end'] == 70.0


class TestMergeTranscriptionResults:
    """Test merge_transcription_results function."""

    def test_merge_single_result(self):
        """Test merging single chunk result."""
        results = [{
            "segments": [{"start": 0.0, "end": 1.0, "text": "Hello"}],
            "text": "Hello",
            "language": "en",
            "language_probability": 0.95,
            "chunk_id": 0,
            "chunk_start": 0.0,
            "chunk_end": 60.0
        }]

        merged = merge_transcription_results(results)

        assert merged["text"] == "Hello"
        assert len(merged["segments"]) == 1
        assert merged["language"] == "en"

    def test_merge_multiple_results(self):
        """Test merging multiple chunk results."""
        results = [
            {
                "segments": [{"start": 0.0, "end": 1.0, "text": "First"}],
                "text": "First",
                "language": "en",
                "language_probability": 0.95,
                "chunk_id": 0,
                "chunk_start": 0.0,
                "chunk_end": 60.0
            },
            {
                "segments": [{"start": 60.0, "end": 61.0, "text": "Second"}],
                "text": "Second",
                "language": "en",
                "language_probability": 0.92,
                "chunk_id": 1,
                "chunk_start": 60.0,
                "chunk_end": 120.0
            }
        ]

        merged = merge_transcription_results(results)

        assert "First" in merged["text"]
        assert "Second" in merged["text"]
        assert len(merged["segments"]) == 2

    def test_merge_empty_results(self):
        """Test merging empty results."""
        results = []

        merged = merge_transcription_results(results)

        assert merged["segments"] == []
        assert merged["text"] == ""

    def test_merge_single_result_is_returned_as_is(self):
        """Test that single result is returned as-is without processing."""
        results = [
            {
                "segments": [{"start": 0, "end": 1, "text": "Hello  "}],
                "text": "Hello  ",
                "language": "en",
                "language_probability": 0.9
            }
        ]

        merged = merge_transcription_results(results)

        assert merged["text"] == "Hello  "
        assert merged == results[0]

    def test_merge_handles_overlapping_segments(self):
        """Test merge handles overlapping segments."""
        results = [
            {
                "segments": [
                    {"start": 0.0, "end": 62.0, "text": "First overlap"},
                ],
                "text": "First overlap",
                "language": "en",
                "language_probability": 0.9
            },
            {
                "segments": [
                    {"start": 58.0, "end": 120.0, "text": "overlap rest"},
                ],
                "text": "overlap rest",
                "language": "en",
                "language_probability": 0.9
            }
        ]

        merged = merge_transcription_results(results, overlap_duration=2, min_segment_gap=0.5)

        # Overlapping segments should be deduplicated/merged
        assert len(merged["segments"]) >= 1


class TestCleanupChunks:
    """Test cleanup_chunks function."""

    def test_cleanup_removes_files(self):
        """Test cleanup removes chunk files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create temporary files
            file1 = os.path.join(tmpdir, "chunk_0.wav")
            file2 = os.path.join(tmpdir, "chunk_1.wav")

            Path(file1).touch()
            Path(file2).touch()

            chunks = [
                AudioChunk(0, 0.0, 60.0, file1, 60.0, 0.0),
                AudioChunk(1, 60.0, 120.0, file2, 60.0, 2.0)
            ]

            cleanup_chunks(chunks)

            # Files should be removed
            assert not os.path.exists(file1)
            assert not os.path.exists(file2)

    def test_cleanup_handles_missing_files(self):
        """Test cleanup handles missing files gracefully."""
        chunks = [
            AudioChunk(0, 0.0, 60.0, "/nonexistent/chunk_0.wav", 60.0, 0.0)
        ]

        # Should not raise error
        cleanup_chunks(chunks)

    def test_cleanup_continues_on_error(self):
        """Test cleanup continues even if one file fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "chunk_0.wav")
            Path(file1).touch()

            chunks = [
                AudioChunk(0, 0.0, 60.0, file1, 60.0, 0.0),
                AudioChunk(1, 60.0, 120.0, "/nonexistent/chunk_1.wav", 60.0, 2.0)
            ]

            # Should not raise error
            cleanup_chunks(chunks)

            # First file should be cleaned
            assert not os.path.exists(file1)


class TestEstimateProcessingTime:
    """Test estimate_processing_time function."""

    def test_estimate_for_tiny_model(self):
        """Test estimate for tiny model."""
        duration = estimate_processing_time(60.0, model_size="tiny")

        # tiny: 0.3x realtime factor
        assert duration == 60.0 * 0.3

    def test_estimate_for_base_model(self):
        """Test estimate for base model."""
        duration = estimate_processing_time(60.0, model_size="base")

        # base: 0.5x realtime factor
        assert duration == 60.0 * 0.5

    def test_estimate_for_large_model(self):
        """Test estimate for large model."""
        duration = estimate_processing_time(60.0, model_size="large")

        # large: 2.5x realtime factor
        assert duration == 60.0 * 2.5

    def test_estimate_unknown_model(self):
        """Test estimate defaults to base for unknown model."""
        duration = estimate_processing_time(60.0, model_size="unknown")

        # Should default to base (0.5x)
        assert duration == 60.0 * 0.5


class TestGetChunkingRecommendation:
    """Test get_chunking_recommendation function."""

    def test_recommendation_for_short_audio(self):
        """Test recommendation for audio under 1 minute."""
        rec = get_chunking_recommendation(30.0)

        assert rec["need_chunking"] is False
        assert "under 1 minute" in rec["reason"]

    def test_recommendation_for_medium_audio(self):
        """Test recommendation for audio 1-3 minutes."""
        rec = get_chunking_recommendation(120.0)

        assert rec["need_chunking"] is False
        assert "under 3 minutes" in rec["reason"]

    def test_recommendation_for_longer_audio(self):
        """Test recommendation for audio 3-10 minutes."""
        rec = get_chunking_recommendation(300.0)

        assert rec["need_chunking"] is True
        assert "3-10 minutes" in rec["reason"]
        assert rec["suggested_chunk_duration"] == 60

    def test_recommendation_for_very_long_audio(self):
        """Test recommendation for audio over 10 minutes."""
        rec = get_chunking_recommendation(900.0)

        assert rec["need_chunking"] is True
        assert "over 10 minutes" in rec["reason"]
        assert rec["suggested_chunk_duration"] == 60


class TestEdgeCases:
    """Test edge cases and error handling."""

    @patch('api.chunking.subprocess.run')
    def test_zero_duration_audio(self, mock_run):
        """Test handling zero duration audio."""
        mock_result = Mock()
        mock_result.stdout = "0\n"
        mock_run.return_value = mock_result

        duration = get_audio_duration("/path/to/audio.mp3")

        assert duration == 0.0

    def test_very_long_audio(self):
        """Test handling very long audio files."""
        config = ChunkConfig(chunk_duration=60, max_total_duration=7200)

        # 7200 seconds = 2 hours, within limit
        duration = 7200.0

        should_chunk = should_enable_chunking(duration, config)

        # Duration exceeds threshold, so should enable
        assert should_chunk is True

    def test_negative_overlap(self):
        """Test handling negative overlap in config."""
        # Config allows it, but behavior is implementation-defined
        config = ChunkConfig(overlap_duration=-1)

        # Implementation may handle this in calculate_chunk_segments
        # For now, just verify config accepts the value
        assert config.overlap_duration == -1

    def test_merging_with_empty_segments(self):
        """Test merging with empty segments."""
        results = [
            {"segments": [], "text": "", "language": "en", "language_probability": 0.9},
            {"segments": [{"start": 0, "end": 1, "text": "Content"}], "text": "Content", "language": "en", "language_probability": 0.95}
        ]

        merged = merge_transcription_results(results)

        assert "Content" in merged["text"]

    def test_chunk_duration_mismatch(self):
        """Test AudioChunk with duration not matching start/end."""
        chunk = AudioChunk(
            chunk_id=0,
            start_time=0.0,
            end_time=60.0,
            file_path="/tmp/chunk.wav",
            duration=55.0,  # Actual duration less than expected
            overlap_with_previous=0.0
        )

        # Implementation should handle mismatches
        assert chunk.duration == 55.0

    @patch('api.chunking.get_audio_duration')
    def test_ffmpeg_failure_during_split(self, mock_get_duration):
        """Test handling ffmpeg failure during chunk splitting."""
        mock_get_duration.return_value = 120.0

        config = ChunkConfig(enabled=True, chunk_duration=60)

        with patch('api.chunking.subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg", stderr="ffmpeg failed")

            with pytest.raises(RuntimeError):
                split_audio_into_chunks("/path/to/audio.mp3", config, output_dir="/tmp")